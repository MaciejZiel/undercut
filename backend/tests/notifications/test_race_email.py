import datetime as dt
import smtplib
from decimal import Decimal

import pytest
from django.core.mail.backends import locmem
from django.utils import timezone

from apps.accounts.models import Favorite
from apps.events import registry
from apps.events.models import OutboxEvent
from apps.events.publisher import publish
from apps.events.worker import process_batch
from apps.notifications import handlers, services
from apps.notifications.models import SentEmail
from tests.accounts.factories import UnverifiedUserFactory, UserFactory
from tests.catalog.factories import (
    ConstructorFactory,
    DriverFactory,
    ResultFactory,
    RoundFactory,
    SeasonFactory,
    SessionFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _handlers():
    registry.clear()
    handlers.register_handlers()
    yield
    registry.clear()


@pytest.fixture
def race(db):
    """Round 2025/5 with a finished race: VER (Red Bull) won, NOR (McLaren) 2nd from P4."""
    season = SeasonFactory(year=2025)
    round_ = RoundFactory(season=season, round=5, name="Monaco Grand Prix")
    session = SessionFactory(round=round_, type="RACE", status="results_final")
    red_bull = ConstructorFactory(name="Red Bull", slug="red-bull")
    mclaren = ConstructorFactory(name="McLaren", slug="mclaren")
    ferrari = ConstructorFactory(name="Ferrari", slug="ferrari")
    ver = DriverFactory(given_name="Max", family_name="Verstappen", slug="max-verstappen")
    nor = DriverFactory(given_name="Lando", family_name="Norris", slug="lando-norris")
    lec = DriverFactory(given_name="Charles", family_name="Leclerc", slug="charles-leclerc")
    ham = DriverFactory(given_name="Lewis", family_name="Hamilton", slug="lewis-hamilton")
    rows = [
        (ver, red_bull, 1, "1", 1, 25, 1),
        (nor, mclaren, 2, "2", 4, 18, None),
        (lec, ferrari, 3, "3", 2, 15, None),
        (ham, ferrari, None, "R", 3, 0, None),
    ]
    for driver, team, pos, text, grid, points, rank in rows:
        ResultFactory(
            session=session,
            driver=driver,
            constructor=team,
            position=pos,
            position_text=text,
            grid=grid,
            points=Decimal(points),
            fastest_lap_rank=rank,
            best_lap_ms=75_321 if rank else None,
        )
    return {
        "round": round_,
        "ver": ver,
        "nor": nor,
        "lec": lec,
        "ham": ham,
        "mclaren": mclaren,
        "ferrari": ferrari,
    }


def opted_in(**kwargs):
    user = UserFactory(**kwargs)
    services.set_race_result_email(user, True)
    return user


def scored_event(race):
    round_id = race["round"].pk
    return publish("PredictionsScored", key=f"round:{round_id}", payload={"round_id": round_id})


def emails_to(mailoutbox):
    return sorted(address for m in mailoutbox for address in m.to)


# --- Recipients -------------------------------------------------------------------------------


def test_only_eligible_users_are_mailed(race, mailoutbox):
    good = opted_in(email="good@example.com")
    UserFactory(email="no-pref@example.com")
    off = UserFactory(email="off@example.com")
    services.set_race_result_email(off, False)
    unverified = UnverifiedUserFactory(email="unverified@example.com")
    services.set_race_result_email(unverified, True)
    demo = UserFactory(email="demo@example.com", is_demo=True)
    services.set_race_result_email(demo, True)
    inactive = opted_in(email="inactive@example.com")
    inactive.is_active = False
    inactive.save()
    no_address = opted_in(email="")

    handlers.handle_race_result(scored_event(race))

    assert emails_to(mailoutbox) == [good.email]
    assert list(SentEmail.objects.values_list("user_id", flat=True)) == [good.pk]
    assert no_address.pk not in SentEmail.objects.values_list("user_id", flat=True)


def test_round_without_a_result_sends_nothing(mailoutbox):
    opted_in()
    round_ = RoundFactory(round=9)
    event = publish("PredictionsScored", key="round:x", payload={"round_id": round_.pk})
    handlers.handle_race_result(event)
    assert mailoutbox == [] and SentEmail.objects.count() == 0


def test_session_results_finalized_alone_sends_nothing(race, mailoutbox):
    opted_in()
    publish("SessionResultsFinalized", key="session:1", payload={"session_id": 1, "version": 1})
    assert process_batch() == 1
    assert mailoutbox == []


# --- Content ----------------------------------------------------------------------------------


def test_content_podium_favourites_pick_links_and_headers(race, mailoutbox, settings):
    settings.SITE_URL = "https://example.test"
    settings.API_PUBLIC_URL = "https://example.test"
    user = opted_in(email="fan@example.com", display_name="Fan One")
    Favorite.objects.create(user=user, driver=race["nor"])
    Favorite.objects.create(user=user, constructor=race["ferrari"])
    user.predictions.create(
        round=race["round"],
        p1=race["ver"],
        p2=race["lec"],
        p3=race["nor"],
        pole=race["ver"],
        fastest_lap=race["ver"],
        points=15,
        breakdown={
            "p1": 5,
            "p2": 2,
            "p3": 2,
            "pole": 3,
            "fastest_lap": 2,
            "exact_podium_bonus": 0,
            "total": 14,
        },
    )
    token = services.get_pref(user).unsubscribe_token

    handlers.handle_race_result(scored_event(race))

    (mail,) = mailoutbox
    assert mail.subject == "Monaco Grand Prix: results and your picks"
    assert mail.to == ["fan@example.com"]
    text = mail.body
    assert "1. Max Verstappen (Red Bull)" in text
    assert "2. Lando Norris (McLaren)" in text
    assert "3. Charles Leclerc (Ferrari)" in text
    assert "Fastest lap: Max Verstappen (Red Bull) in 1:15.321" in text
    assert "Lando Norris (McLaren): P2, 18 pts, started P4 (2 places gained)" in text
    assert "Ferrari: best finish P3, 15 pts" in text
    assert "P1: you picked Max Verstappen, actual Max Verstappen" in text
    assert "P2: you picked Charles Leclerc, actual Lando Norris" in text
    assert "Pole: you picked Max Verstappen" in text
    assert "Pole position: 3" in text and "Total: 15" in text
    assert "https://example.test/seasons/2025/5" in text
    unsubscribe = f"https://example.test/api/v1/notifications/unsubscribe/{token}/"
    assert unsubscribe in text
    assert mail.extra_headers["List-Unsubscribe"] == f"<{unsubscribe}>"
    assert mail.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"

    ((html, mimetype),) = mail.alternatives
    assert mimetype == "text/html"
    assert '<html lang="en">' in html
    assert "<caption" in html and 'scope="col"' in html
    assert "Max Verstappen" in html and "Monaco Grand Prix" in html
    assert 'href="https://example.test/seasons/2025/5"' in html
    assert f'href="{unsubscribe}"' in html
    assert "http://" not in html.replace("https://", "")  # no external assets
    assert "<img" not in html and "<script" not in html


def test_mail_without_favourites_or_pick_still_has_podium(race, mailoutbox):
    opted_in()
    handlers.handle_race_result(scored_event(race))
    (mail,) = mailoutbox
    assert "Podium" in mail.body
    assert "Your favourites" not in mail.body and "Your picks" not in mail.body


def test_html_escapes_user_supplied_names(race, mailoutbox):
    opted_in(display_name="<b>Eve</b>")
    handlers.handle_race_result(scored_event(race))
    html = mailoutbox[0].alternatives[0][0]
    assert "<b>Eve</b>" not in html and "&lt;b&gt;Eve&lt;/b&gt;" in html


def test_retired_favourite_is_reported_without_a_position(race, mailoutbox):
    user = opted_in()
    Favorite.objects.create(user=user, driver=race["ham"])
    handlers.handle_race_result(scored_event(race))
    assert "Lewis Hamilton (Ferrari): R, 0 pts" in mailoutbox[0].body


# --- Exactly once -----------------------------------------------------------------------------


def test_redelivery_does_not_mail_twice(race, mailoutbox):
    opted_in()
    event = scored_event(race)
    handlers.handle_race_result(event)
    handlers.handle_race_result(event)
    assert len(mailoutbox) == 1 and SentEmail.objects.count() == 1


def test_a_second_scoring_event_does_not_mail_again(race, mailoutbox):
    opted_in()
    scored_event(race)
    assert process_batch() == 1
    scored_event(race)  # e.g. a result correction re-scored the round
    assert process_batch() == 1
    assert len(mailoutbox) == 1


def test_new_subscriber_gets_the_mail_on_redelivery_and_old_ones_do_not(race, mailoutbox):
    first = opted_in(email="first@example.com")
    event = scored_event(race)
    handlers.handle_race_result(event)
    second = opted_in(email="second@example.com")
    handlers.handle_race_result(event)
    assert emails_to(mailoutbox) == [first.email, second.email]


# --- Partial failure and retry ----------------------------------------------------------------


def fail_for(monkeypatch, bad_address):
    original = locmem.EmailBackend.send_messages
    state = {"fail": True}

    def flaky(self, messages):
        if state["fail"] and any(bad_address in m.to for m in messages):
            raise smtplib.SMTPException("boom")
        return original(self, messages)

    monkeypatch.setattr(locmem.EmailBackend, "send_messages", flaky)
    return state


def test_one_failure_does_not_block_the_others_and_retry_sends_only_the_missing(
    race, mailoutbox, monkeypatch
):
    a = opted_in(email="a@example.com")
    b = opted_in(email="b@example.com")
    c = opted_in(email="c@example.com")
    state = fail_for(monkeypatch, "b@example.com")

    scored_event(race)
    assert process_batch() == 1

    assert emails_to(mailoutbox) == [a.email, c.email]
    assert sorted(SentEmail.objects.values_list("user_id", flat=True)) == sorted([a.pk, c.pk])
    first = OutboxEvent.objects.get(type="PredictionsScored")
    assert first.status == OutboxEvent.Status.DONE  # nothing raised: markers are kept
    retry = OutboxEvent.objects.get(type=handlers.RETRY_EVENT)
    assert retry.payload == {"round_id": race["round"].pk, "attempt": 1}
    assert retry.available_at > timezone.now() + dt.timedelta(minutes=4)
    assert retry.available_at < timezone.now() + dt.timedelta(hours=1)

    # Not due yet: the worker leaves it alone.
    assert process_batch() == 0

    state["fail"] = False
    OutboxEvent.objects.filter(pk=retry.pk).update(available_at=timezone.now())
    assert process_batch() == 1

    assert emails_to(mailoutbox) == [a.email, b.email, c.email]
    assert SentEmail.objects.filter(user=b).count() == 1
    assert OutboxEvent.objects.filter(type=handlers.RETRY_EVENT).count() == 1  # no more retries


def test_retries_are_bounded(race, mailoutbox, monkeypatch):
    opted_in(email="b@example.com")
    fail_for(monkeypatch, "b@example.com")
    event = publish(
        handlers.RETRY_EVENT,
        key="x",
        payload={"round_id": race["round"].pk, "attempt": handlers.MAX_RETRIES},
    )
    handlers.handle_race_result(event)
    assert OutboxEvent.objects.filter(type=handlers.RETRY_EVENT).count() == 1  # only the input
    assert mailoutbox == []


def test_retry_delays_stay_inside_the_six_hour_window():
    total = sum((handlers.RETRY_BASE * 2**n for n in range(handlers.MAX_RETRIES)), dt.timedelta())
    assert total < dt.timedelta(hours=6)


# --- Unsubscribe between scoring and sending --------------------------------------------------


def test_unsubscribed_before_sending_gets_nothing(race, mailoutbox):
    gone = opted_in(email="gone@example.com")
    stays = opted_in(email="stays@example.com")
    scored_event(race)
    services.unsubscribe(services.get_pref(gone).unsubscribe_token)

    assert process_batch() == 1

    assert emails_to(mailoutbox) == [stays.email]
    assert not SentEmail.objects.filter(user=gone).exists()


def test_deleting_the_account_removes_the_marker(race, mailoutbox):
    user = opted_in()
    handlers.handle_race_result(scored_event(race))
    assert SentEmail.objects.filter(user=user).exists()
    user.delete()
    assert SentEmail.objects.count() == 0
