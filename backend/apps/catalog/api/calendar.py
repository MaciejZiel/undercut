"""Season calendar (FR-102) and its iCalendar export."""

import datetime as dt

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .. import selectors
from ..models import Season, Session
from . import filters
from .serializers import DriverRefSerializer, TeamRefSerializer
from .views import PublicDetailView, _validated

# --- Serializers -----------------------------------------------------------------------------


class CalendarQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(
        required=False,
        min_value=filters.MIN_YEAR,
        max_value=filters.MAX_YEAR,
        help_text="Season year (default: the latest season with rounds).",
    )


class IcsQuerySerializer(CalendarQuerySerializer):
    round = serializers.IntegerField(
        required=False, min_value=1, max_value=100, help_text="Only this round (default: all)."
    )


class CalendarCircuitSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    country = serializers.CharField(allow_null=True)
    locality = serializers.CharField(allow_null=True)
    timezone = serializers.CharField(allow_null=True, help_text="IANA name of the circuit.")


class CalendarSessionSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="FP1, FP2, FP3, SQ, SPRINT, Q or RACE.")
    start_utc = serializers.DateTimeField(allow_null=True)
    end_utc = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()


class CalendarWinnerSerializer(serializers.Serializer):
    driver = DriverRefSerializer()
    team = TeamRefSerializer()


class CalendarEntrySerializer(serializers.Serializer):
    round = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    date = serializers.DateField()
    status = serializers.CharField(help_text="completed, next, upcoming or cancelled.")
    is_next = serializers.BooleanField()
    has_sprint = serializers.BooleanField()
    race_start_utc = serializers.DateTimeField(
        allow_null=True, help_text="Countdown target; null when the race time is unknown."
    )
    circuit = CalendarCircuitSerializer()
    sessions = CalendarSessionSerializer(many=True, help_text="Only sessions that exist.")
    winner = CalendarWinnerSerializer(allow_null=True, help_text="Null until results exist.")


class NextRoundSerializer(serializers.Serializer):
    round = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    race_start_utc = serializers.DateTimeField(allow_null=True)


class CalendarSerializer(serializers.Serializer):
    year = serializers.IntegerField(allow_null=True)
    next_round = NextRoundSerializer(allow_null=True)
    rounds = CalendarEntrySerializer(many=True)


# --- iCalendar (RFC 5545) --------------------------------------------------------------------

SESSION_LABELS = dict(Session.Type.choices)
# Used when the end of a session is unknown (minutes).
DEFAULT_DURATION = {"FP1": 60, "FP2": 60, "FP3": 60, "SQ": 45, "SPRINT": 40, "Q": 60, "RACE": 120}
PRODID = "-//Undercut//Calendar//EN"
UID_DOMAIN = "undercut"


def escape_text(value: str) -> str:
    """Escape a TEXT value: backslash, semicolon, comma and line breaks (RFC 5545 3.3.11)."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fold_line(line: str, limit: int = 75) -> str:
    """Fold a content line to at most `limit` octets per physical line (RFC 5545 3.1).

    Continuation lines start with one space, which counts towards their limit. UTF-8
    characters are never split.
    """
    if len(line.encode()) <= limit:
        return line
    parts: list[str] = []
    current: list[str] = []
    size = 0
    for char in line:
        width = len(char.encode())
        if size + width > limit:
            parts.append("".join(current))
            current, size = [], 1  # the leading space of the next physical line
        current.append(char)
        size += width
    parts.append("".join(current))
    return "\r\n ".join(parts)


def format_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def build_ics(calendar: dict, round_number: int | None, stamp: dt.datetime) -> str:
    """iCalendar text for the sessions of one round, or of the whole year when None.

    Times are UTC, UIDs are stable (`<year>-r<round>-<type>@undercut`), sessions without a start
    time and cancelled rounds are left out. `stamp` is the DTSTAMP of every event.
    """
    year = calendar["year"]
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(f'Undercut {year}')}",
    ]
    for entry in calendar["rounds"]:
        if entry["status"] == "cancelled":
            continue
        if round_number is not None and entry["round"] != round_number:
            continue
        circuit = entry["circuit"]
        location = ", ".join(
            part for part in (circuit["name"], circuit["locality"], circuit["country"]) if part
        )
        for session in entry["sessions"]:
            start = session["start_utc"]
            if start is None:
                continue
            end = session["end_utc"] or start + dt.timedelta(
                minutes=DEFAULT_DURATION.get(session["type"], 60)
            )
            label = SESSION_LABELS.get(session["type"], session["type"])
            lines += [
                "BEGIN:VEVENT",
                f"UID:{year}-r{entry['round']}-{session['type']}@{UID_DOMAIN}",
                f"DTSTAMP:{format_utc(stamp)}",
                f"DTSTART:{format_utc(start)}",
                f"DTEND:{format_utc(end)}",
                f"SUMMARY:{escape_text(f'{entry["name"]} - {label}')}",
                f"LOCATION:{escape_text(location)}",
                f"DESCRIPTION:{escape_text(f'Round {entry["round"]} of {year}, {label}.')}",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    return "".join(fold_line(line) + "\r\n" for line in lines)


# --- Views -----------------------------------------------------------------------------------


def _resolve_year(requested: int | None) -> int | None:
    if requested is None:
        return selectors.calendar_year()
    get_object_or_404(Season, year=requested)
    return requested


class CalendarView(PublicDetailView):
    @extend_schema(
        tags=["calendar"],
        summary="Season calendar with sessions and status",
        parameters=[CalendarQuerySerializer],
        responses=CalendarSerializer,
    )
    def get(self, request):
        data = _validated(CalendarQuerySerializer, request)
        year = _resolve_year(data.get("year"))
        if year is None:
            body = {"year": None, "next_round": None, "rounds": []}
        else:
            body = selectors.calendar(year)
        return Response(CalendarSerializer(body).data)


class CalendarIcsView(PublicDetailView):
    @extend_schema(
        tags=["calendar"],
        summary="iCalendar export of a round or a season",
        parameters=[IcsQuerySerializer],
        responses={(200, "text/calendar"): OpenApiTypes.STR},
    )
    def get(self, request):
        data = _validated(IcsQuerySerializer, request)
        year = _resolve_year(data.get("year"))
        if year is None:
            raise NotFound("There is no season yet.")
        calendar = selectors.calendar(year)
        number = data.get("round")
        if number is not None and all(e["round"] != number for e in calendar["rounds"]):
            raise NotFound(f"Season {year} has no round {number}.")
        body = build_ics(calendar, number, timezone.now())
        response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
        name = f"undercut-{year}" + (f"-r{number}" if number is not None else "")
        response["Content-Disposition"] = f'inline; filename="{name}.ics"'
        return response
