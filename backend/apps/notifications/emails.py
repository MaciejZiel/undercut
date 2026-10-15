"""Content of the post-race e-mail: plain text and a hand-written, self-contained HTML version.

Rendering takes plain data only (dataclasses from the other modules' public functions) and has no
I/O, so it is easy to test. No external assets, no scripts; styles are inline because mail clients
drop <style> blocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

from apps.catalog.summaries import ConstructorRaceResult, DriverRaceResult, RaceSummary
from apps.predictions.selectors_public import UserRoundResult

KIND_RACE_RESULT = "race_result"

_TEXT = "color:#1a1a1a;"
_MUTED = "color:#4a4a4a;"
_TH = "text-align:left;padding:4px 12px 4px 0;border-bottom:1px solid #c8c8c8;"
_TD = "padding:4px 12px 4px 0;border-bottom:1px solid #e4e4e4;"


@dataclass(frozen=True)
class RaceEmail:
    summary: RaceSummary
    recipient_name: str
    drivers: list[DriverRaceResult] = field(default_factory=list)
    constructors: list[ConstructorRaceResult] = field(default_factory=list)
    pick: UserRoundResult | None = None
    unsubscribe_url: str = ""


def round_url(summary: RaceSummary) -> str:
    h = summary.header
    return f"{settings.SITE_URL}/seasons/{h.year}/{h.round}"


def unsubscribe_url(token: str) -> str:
    return f"{settings.API_PUBLIC_URL}/api/v1/notifications/unsubscribe/{token}/"


def subject(summary: RaceSummary) -> str:
    return f"{summary.header.name}: results and your picks"


def _lap(ms: int | None) -> str:
    if not ms:
        return ""
    minutes, rest = divmod(ms, 60_000)
    return f"{minutes}:{rest / 1000:06.3f}"


def _grid(change: int | None) -> str:
    if change is None:
        return "grid change unknown"
    if change == 0:
        return "no grid change"
    return (
        f"{abs(change)} place{'s' if abs(change) != 1 else ''} {'gained' if change > 0 else 'lost'}"
    )


def _pts(points: float) -> str:
    return f"{points:g} pt" + ("" if points == 1 else "s")


def _driver_line(r: DriverRaceResult) -> str:
    place = f"P{r.position}" if r.position is not None else (r.position_text or "not classified")
    start = f"started P{r.grid}" if r.grid else "no grid position"
    return f"{place}, {_pts(r.points)}, {start} ({_grid(r.grid_change)})"


def _constructor_line(r: ConstructorRaceResult) -> str:
    best = f"best finish P{r.best_position}" if r.best_position is not None else "no classified car"
    return f"{best}, {_pts(r.points)}"


def _pick_slots(e: RaceEmail):
    """Pick vs podium rows: (label, picked, actual)."""
    if e.pick is None:
        return []
    podium = {p.position: p.driver_name for p in e.summary.podium}
    return [
        ("P1", e.pick.picks["p1"], podium.get(1, "unknown")),
        ("P2", e.pick.picks["p2"], podium.get(2, "unknown")),
        ("P3", e.pick.picks["p3"], podium.get(3, "unknown")),
    ]


def render_text(e: RaceEmail) -> str:
    s = e.summary
    out = [f"Hi {e.recipient_name},", "", f"{s.header.name}: results", "", "Podium"]
    out += [f"{p.position}. {p.driver_name} ({p.constructor_name})" for p in s.podium]
    if s.fastest_lap:
        f = s.fastest_lap
        lap = f" in {_lap(f.time_ms)}" if f.time_ms else ""
        out += ["", f"Fastest lap: {f.driver_name} ({f.constructor_name}){lap}"]
    if e.drivers or e.constructors:
        out += ["", "Your favourites"]
        out += [f"{r.driver_name} ({r.constructor_name}): {_driver_line(r)}" for r in e.drivers]
        out += [f"{r.constructor_name}: {_constructor_line(r)}" for r in e.constructors]
    if e.pick:
        out += ["", "Your picks"]
        out += [
            f"{label}: you picked {mine}, actual {real}" for label, mine, real in _pick_slots(e)
        ]
        out += [
            f"Pole: you picked {e.pick.picks['pole']}",
            f"Fastest lap: you picked {e.pick.picks['fastest_lap']}",
        ]
        if e.pick.points is not None:
            out += ["", "Points"]
            out += [f"{label}: {pts}" for label, pts in e.pick.breakdown_rows]
            out += [f"Total: {e.pick.points}"]
    out += [
        "",
        f"Full results: {round_url(s)}",
        "",
        "You get this e-mail because you turned on race result e-mails.",
        f"Unsubscribe with one click: {e.unsubscribe_url}",
    ]
    return "\n".join(out) + "\n"


def _table(caption: str, headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f'<th scope="col" style="{_TH}">{escape(h)}</th>' for h in headers)
    body = "".join(
        "<tr>" + "".join(f'<td style="{_TD}">{escape(c)}</td>' for c in row) + "</tr>"
        for row in rows
    )
    return (
        f'<table style="border-collapse:collapse;width:100%;{_TEXT}">'
        f'<caption style="text-align:left;font-weight:bold;padding-bottom:4px;">'
        f"{escape(caption)}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def render_html(e: RaceEmail) -> str:
    s = e.summary
    parts = [
        f'<h1 style="font-size:22px;margin:0 0 12px;{_TEXT}">{escape(s.header.name)}: results</h1>',
        _table(
            "Podium",
            ["Position", "Driver", "Team"],
            [[str(p.position), p.driver_name, p.constructor_name] for p in s.podium],
        ),
    ]
    if s.fastest_lap:
        f = s.fastest_lap
        lap = f", {_lap(f.time_ms)}" if f.time_ms else ""
        parts.append(
            f'<p style="{_TEXT}"><strong>Fastest lap:</strong> {escape(f.driver_name)} '
            f"({escape(f.constructor_name)}){escape(lap)}</p>"
        )
    if e.drivers or e.constructors:
        rows = [[r.driver_name, f"{r.constructor_name}: {_driver_line(r)}"] for r in e.drivers]
        rows += [[r.constructor_name, f"Team: {_constructor_line(r)}"] for r in e.constructors]
        parts.append(_table("Your favourites", ["Favourite", "Result"], rows))
    if e.pick:
        parts.append(
            _table(
                "Your picks against the podium",
                ["Place", "You picked", "Actual"],
                [list(row) for row in _pick_slots(e)],
            )
        )
        parts.append(
            f'<p style="{_TEXT}">Pole: you picked {escape(e.pick.picks["pole"])}. '
            f"Fastest lap: you picked {escape(e.pick.picks['fastest_lap'])}.</p>"
        )
        if e.pick.points is not None:
            rows = [[label, str(pts)] for label, pts in e.pick.breakdown_rows]
            rows.append(["Total", str(e.pick.points)])
            parts.append(_table("Points", ["Part", "Points"], rows))
    link_style = "color:#0b4fa8;text-decoration:underline;"
    parts.append(
        f'<p style="{_TEXT}"><a href="{escape(round_url(s))}" style="{link_style}">'
        "See the full results</a></p>"
    )
    parts.append(
        f'<p style="font-size:13px;{_MUTED}">You get this e-mail because you turned on race result '
        f'e-mails. <a href="{escape(e.unsubscribe_url)}" style="{link_style}">'
        "Unsubscribe with one click</a>.</p>"
    )
    inner = "".join(f'<div style="margin:0 0 20px;">{p}</div>' for p in parts)
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(subject(s))}</title></head>"
        '<body style="margin:0;padding:16px;background:#ffffff;'
        'font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.5;">'
        f'<div style="max-width:600px;margin:0 auto;">'
        f'<p style="{_TEXT}">Hi {escape(e.recipient_name)},</p>'
        f"{inner}</div></body></html>"
    )


def build_message(e: RaceEmail, to: str) -> EmailMultiAlternatives:
    message = EmailMultiAlternatives(
        subject=subject(e.summary),
        body=render_text(e),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
        headers={
            "List-Unsubscribe": f"<{e.unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )
    message.attach_alternative(render_html(e), "text/html")
    return message
