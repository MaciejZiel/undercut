"""Track outlines from a bundled GeoJSON file, for circuits OpenF1 has no data for (before 2023).

The file is `f1-circuits` by Tomislav Bacinger (MIT licence, shipped next to it as
`f1-circuits-LICENSE.md`): one closed centre line per circuit in longitude and latitude. It shows
the current layout of a circuit, which is not always the layout of an old Grand Prix, and it does
not say where the start line is, so these outlines carry `marker: false` and no start mark is
drawn.
Circuits that already have an outline are skipped unless `force` is set.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

from django.db import transaction

from apps.catalog import models as catalog_models
from apps.catalog import services as catalog

from .openf1.outline import DECIMETRES, build_outline

log = logging.getLogger(__name__)

DATA = Path(__file__).resolve().parent.parent / "catalog" / "data" / "f1-circuits.geojson"
ORIGIN = "geojson"

# GeoJSON id -> catalog slug, for circuits raced before 2023 whose layout the file still shows.
# Indianapolis is left out on purpose: the file has the oval, Formula 1 used the road course.
SLUGS: dict[str, str] = {
    "pt-1972": "estoril",
    "ar-1952": "galvez",
    "de-1932": "hockenheimring",
    "tr-2005": "istanbul",
    "br-1977": "jacarepagua",
    "za-1961": "kyalami",
    "fr-1960": "magny-cours",
    "it-1914": "mugello",
    "de-1927": "nurburgring",
    "pt-2008": "portimao",
    "fr-1969": "ricard",
    "ru-2014": "sochi",
    "us-1956": "watkins-glen",
}


def project(coordinates: list[list[float]]) -> list[tuple[float, float]]:
    """Longitude and latitude to a local flat plane in decimetres, y growing north."""
    lat0 = sum(c[1] for c in coordinates) / len(coordinates)
    lon0 = sum(c[0] for c in coordinates) / len(coordinates)
    per_degree_lat = 111_320 * DECIMETRES
    per_degree_lon = per_degree_lat * math.cos(math.radians(lat0))
    return [
        ((lon - lon0) * per_degree_lon, (lat - lat0) * per_degree_lat)
        for lon, lat, *_ in coordinates
    ]


def outline_from_feature(feature: dict) -> dict | None:
    coordinates = feature["geometry"]["coordinates"]
    outline = build_outline(project(coordinates), min_samples=20)
    if outline is None:
        return None
    declared = feature.get("properties", {}).get("length")
    if isinstance(declared, int | float) and declared > 0:
        outline["length_m"] = round(declared)
    return {**outline, "marker": False, "origin": ORIGIN}


@dataclass
class Summary:
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def import_geojson(path: Path = DATA, *, force: bool = False) -> Summary:
    summary = Summary()
    features = {f["properties"]["id"]: f for f in json.loads(path.read_text())["features"]}
    for geo_id, slug in SLUGS.items():
        circuit = catalog_models.Circuit.objects.filter(slug=slug).first()
        feature = features.get(geo_id)
        if circuit is None or feature is None:
            summary.failed.append(f"{slug}: not in the catalog or in the file")
            continue
        if circuit.outline and not force:
            summary.skipped.append(slug)
            continue
        outline = outline_from_feature(feature)
        if outline is None:
            summary.failed.append(f"{slug}: unusable line")
            continue
        with transaction.atomic():
            catalog.set_circuit_outline(circuit.pk, outline)
        summary.written.append(slug)
    return summary
