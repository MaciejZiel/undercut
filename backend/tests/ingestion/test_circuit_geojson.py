import json
import math

from apps.catalog.models import Circuit
from apps.ingestion import circuit_geojson as geo
from tests.catalog import factories as f


def loop(n=60, lon=-9.39, lat=38.75, radius=0.01):
    """A closed lap as GeoJSON gives it: longitude and latitude, first point repeated."""
    points = [
        [
            lon + radius * math.cos(2 * math.pi * i / n),
            lat + radius * 0.6 * math.sin(2 * math.pi * i / n),
        ]
        for i in range(n)
    ]
    return [*points, points[0]]


def feature(geo_id="pt-1972", length=4350, coordinates=None):
    return {
        "type": "Feature",
        "properties": {"id": geo_id, "Name": "Somewhere", "length": length},
        "geometry": {"type": "LineString", "coordinates": coordinates or loop()},
    }


def test_projection_keeps_a_circle_roughly_round_in_metres():
    flat = geo.project(loop(lat=60.0))
    xs = [p[0] for p in flat]
    # at 60 degrees north a degree of longitude is half as long as a degree of latitude
    assert math.isclose((max(xs) - min(xs)) / 10, 2 * 0.01 * 111_320 * 0.5, rel_tol=0.01)


def test_outline_from_feature_has_no_start_mark_and_uses_the_declared_length():
    result = geo.outline_from_feature(feature())
    assert result["marker"] is False and result["origin"] == "geojson"
    assert result["length_m"] == 4350
    assert result["width"] == 1000 and result["points"][0] == result["points"][-1]


def test_import_draws_only_circuits_without_an_outline(db, tmp_path):
    path = tmp_path / "circuits.geojson"
    path.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": [feature("pt-1972"), feature("tr-2005")]}
        )
    )
    f.CircuitFactory(slug="estoril")
    f.CircuitFactory(slug="istanbul", outline={"width": 1, "height": 1, "points": [[0, 0]]})
    summary = geo.import_geojson(path)
    assert summary.written == ["estoril"] and summary.skipped == ["istanbul"]
    assert Circuit.objects.get(slug="estoril").outline["origin"] == "geojson"
    again = geo.import_geojson(path)
    assert again.written == [] and set(again.skipped) == {"estoril", "istanbul"}
    forced = geo.import_geojson(path, force=True)
    assert set(forced.written) == {"estoril", "istanbul"}


def test_import_reports_circuits_missing_from_the_catalog_or_the_file(db, tmp_path):
    path = tmp_path / "circuits.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [feature("pt-1972")]}))
    summary = geo.import_geojson(path)
    assert summary.written == [] and len(summary.failed) == len(geo.SLUGS)


def test_the_bundled_file_covers_every_mapped_circuit():
    ids = {x["properties"]["id"] for x in json.loads(geo.DATA.read_text())["features"]}
    assert set(geo.SLUGS) <= ids
    assert "us-1909" not in geo.SLUGS  # the Indianapolis oval is not the road course Formula 1 used
