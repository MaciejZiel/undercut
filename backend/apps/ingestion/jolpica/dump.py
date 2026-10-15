"""Reading the Jolpica-F1 CSV database dump.

The dump is untrusted input: archive members are validated before extraction and every CSV is
read by column name (the column order is not stable).
"""

from __future__ import annotations

import csv
import shutil
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

DUMP_URL = "https://api.jolpi.ca/data/dumps/download/delayed/?dump_type=csv"
USER_AGENT = "Undercut/0.1"
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
MAX_UNPACKED_BYTES = 1024 * 1024 * 1024
TABLE_PREFIX = "formula_one_"

csv.field_size_limit(1 << 20)


class DumpError(Exception):
    pass


# --------------------------------------------------------------------------- download / unzip


def download_dump(dest: Path, url: str = DUMP_URL, timeout: int = 60) -> Path:
    """Download the zip to `dest` (the endpoint redirects to a short-lived signed URL)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    written = 0
    with urllib.request.urlopen(request, timeout=timeout) as response, dest.open("wb") as out:  # noqa: S310
        while chunk := response.read(1 << 20):
            written += len(chunk)
            if written > MAX_DOWNLOAD_BYTES:
                raise DumpError("Dump download is larger than expected; aborting.")
            out.write(chunk)
    return dest


def safe_extract(zip_path: Path, dest: Path) -> None:
    """Extract CSV members into `dest`, rejecting anything that could escape it."""
    dest = dest.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if sum(i.file_size for i in infos) > MAX_UNPACKED_BYTES:
            raise DumpError("Archive unpacks to more than the allowed size.")
        for info in infos:
            name = info.filename
            pure = PurePosixPath(name)
            if (
                pure.is_absolute()
                or ".." in pure.parts
                or "\\" in name
                or (len(name) > 1 and name[1] == ":")
            ):
                raise DumpError(f"Unsafe path in archive: {name!r}")
            target = (dest / name).resolve()
            if target != dest and dest not in target.parents:
                raise DumpError(f"Unsafe path in archive: {name!r}")
            if info.is_dir():
                continue
            if not name.endswith(".csv"):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)


@contextmanager
def open_dump(path: Path) -> Iterator[Path]:
    """Yield a directory holding the CSV files; unpack a zip into a temporary directory."""
    path = Path(path)
    if path.is_dir():
        yield path
        return
    if not zipfile.is_zipfile(path):
        raise DumpError(f"{path} is neither a directory nor a zip archive.")
    with tempfile.TemporaryDirectory(prefix="jolpica-") as tmp:
        safe_extract(path, Path(tmp))
        yield _find_root(Path(tmp))


def _find_root(base: Path) -> Path:
    if (base / f"{TABLE_PREFIX}season.csv").exists():
        return base
    for child in base.iterdir():
        if child.is_dir() and (child / f"{TABLE_PREFIX}season.csv").exists():
            return child
    raise DumpError("No formula_one_season.csv in the dump.")


# --------------------------------------------------------------------------- rows


@dataclass(frozen=True)
class SeasonRow:
    id: int
    year: int


@dataclass(frozen=True)
class CircuitRow:
    id: int
    reference: str
    name: str
    locality: str
    country: str
    latitude: Decimal | None
    longitude: Decimal | None


@dataclass(frozen=True)
class DriverRow:
    id: int
    reference: str
    forename: str
    surname: str
    abbreviation: str
    permanent_car_number: int | None
    date_of_birth: str
    nationality: str


@dataclass(frozen=True)
class TeamRow:
    id: int
    reference: str
    name: str
    nationality: str
    primary_color: str


@dataclass(frozen=True)
class RoundRow:
    id: int
    season_id: int
    circuit_id: int
    name: str
    date: str
    number: int | None
    is_cancelled: bool


@dataclass(frozen=True)
class SessionRow:
    id: int
    round_id: int
    type: str
    number: int | None
    timestamp: str
    timezone: str
    scheduled_laps: int | None
    is_cancelled: bool


@dataclass(frozen=True)
class TeamDriverRow:
    id: int
    season_id: int
    driver_id: int
    team_id: int


@dataclass(frozen=True)
class RoundEntryRow:
    id: int
    round_id: int
    team_driver_id: int


@dataclass(frozen=True)
class SessionEntryRow:
    id: int
    session_id: int
    round_entry_id: int
    position: int | None
    grid: int | None
    laps_completed: int | None
    points: str
    status: str  # integer code as text
    detail: str
    time: str
    is_classified: bool
    fastest_lap_rank: int | None


@dataclass
class Dump:
    seasons: list[SeasonRow] = field(default_factory=list)
    circuits: dict[int, CircuitRow] = field(default_factory=dict)
    drivers: dict[int, DriverRow] = field(default_factory=dict)
    teams: dict[int, TeamRow] = field(default_factory=dict)
    rounds: list[RoundRow] = field(default_factory=list)
    sessions_by_round: dict[int, list[SessionRow]] = field(
        default_factory=lambda: defaultdict(list)
    )
    team_drivers: dict[int, TeamDriverRow] = field(default_factory=dict)
    round_entries: dict[int, RoundEntryRow] = field(default_factory=dict)
    entries_by_session: dict[int, list[SessionEntryRow]] = field(
        default_factory=lambda: defaultdict(list)
    )
    # session_entry_id -> fastest lap time text (qualifying times live only in `lap` rows)
    fastest_laps: dict[int, str] = field(default_factory=dict)


def _int(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(Decimal(value))
    except (InvalidOperation, ValueError):
        return None


def _dec(value: str) -> Decimal | None:
    value = (value or "").strip()
    try:
        return Decimal(value) if value else None
    except InvalidOperation:
        return None


def _bool(value: str) -> bool:
    return (value or "").strip().lower() in {"t", "true", "1"}


def _rows(directory: Path, table: str) -> Iterator[dict[str, str]]:
    path = directory / f"{TABLE_PREFIX}{table}.csv"
    if not path.exists():
        raise DumpError(f"Missing table file: {path.name}")
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def read_dump(directory: Path) -> Dump:
    """Parse the tables the importer needs into frozen row dataclasses."""
    directory = Path(directory)
    dump = Dump()
    try:
        for r in _rows(directory, "season"):
            dump.seasons.append(SeasonRow(int(r["id"]), int(r["year"])))
        for r in _rows(directory, "circuit"):
            dump.circuits[int(r["id"])] = CircuitRow(
                int(r["id"]),
                r["reference"],
                r["name"],
                r["locality"],
                r["country"],
                _dec(r["latitude"]),
                _dec(r["longitude"]),
            )
        for r in _rows(directory, "driver"):
            dump.drivers[int(r["id"])] = DriverRow(
                int(r["id"]),
                r["reference"],
                r["forename"],
                r["surname"],
                r["abbreviation"],
                _int(r["permanent_car_number"]),
                r["date_of_birth"],
                r["nationality"],
            )
        for r in _rows(directory, "team"):
            dump.teams[int(r["id"])] = TeamRow(
                int(r["id"]), r["reference"], r["name"], r["nationality"], r["primary_color"]
            )
        for r in _rows(directory, "round"):
            dump.rounds.append(
                RoundRow(
                    int(r["id"]),
                    int(r["season_id"]),
                    int(r["circuit_id"]),
                    r["name"],
                    r["date"],
                    _int(r["number"]),
                    _bool(r["is_cancelled"]),
                )
            )
        for r in _rows(directory, "session"):
            dump.sessions_by_round[int(r["round_id"])].append(
                SessionRow(
                    int(r["id"]),
                    int(r["round_id"]),
                    r["type"],
                    _int(r["number"]),
                    r["timestamp"],
                    r["timezone"],
                    _int(r["scheduled_laps"]),
                    _bool(r["is_cancelled"]),
                )
            )
        for r in _rows(directory, "teamdriver"):
            dump.team_drivers[int(r["id"])] = TeamDriverRow(
                int(r["id"]), int(r["season_id"]), int(r["driver_id"]), int(r["team_id"])
            )
        for r in _rows(directory, "roundentry"):
            dump.round_entries[int(r["id"])] = RoundEntryRow(
                int(r["id"]), int(r["round_id"]), int(r["team_driver_id"])
            )
        for r in _rows(directory, "sessionentry"):
            dump.entries_by_session[int(r["session_id"])].append(
                SessionEntryRow(
                    int(r["id"]),
                    int(r["session_id"]),
                    int(r["round_entry_id"]),
                    _int(r["position"]),
                    _int(r["grid"]),
                    _int(r["laps_completed"]),
                    r["points"],
                    r["status"],
                    r["detail"],
                    r["time"],
                    _bool(r["is_classified"]),
                    _int(r["fastest_lap_rank"]),
                )
            )
        for r in _rows(directory, "lap"):
            if _bool(r["is_entry_fastest_lap"]) and not _bool(r["is_deleted"]) and r["time"]:
                dump.fastest_laps[int(r["session_entry_id"])] = r["time"]
    except KeyError as exc:
        raise DumpError(f"Unexpected dump layout, missing column {exc}") from exc
    return dump
