import io
import urllib.request
import zipfile
from pathlib import Path

import pytest

from apps.ingestion.jolpica import dump as dump_mod
from apps.ingestion.jolpica.dump import DumpError, open_dump, safe_extract

FIXTURES = Path(__file__).parent / "fixtures" / "dump"


def make_zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return path


@pytest.mark.parametrize("name", ["../evil.csv", "/abs/evil.csv", "a/../../evil.csv", "C:evil.csv"])
def test_zip_slip_is_rejected(tmp_path, name):
    archive = make_zip(tmp_path / "bad.zip", {name: b"x"})
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(DumpError):
        safe_extract(archive, dest)
    assert not (tmp_path / "evil.csv").exists()
    assert list(dest.iterdir()) == []


def test_zip_with_dump_extracts_and_cleans_up(tmp_path):
    archive = make_zip(
        tmp_path / "ok.zip",
        {p.name: p.read_bytes() for p in FIXTURES.glob("*.csv")} | {"notes.txt": b"ignored"},
    )
    with open_dump(archive) as directory:
        assert (directory / "formula_one_season.csv").exists()
        assert not (directory / "notes.txt").exists()
        kept = directory
    assert not kept.exists()


def test_not_an_archive(tmp_path):
    bogus = tmp_path / "x.zip"
    bogus.write_bytes(b"nope")
    with pytest.raises(DumpError), open_dump(bogus):
        pass


def test_download_sends_user_agent(tmp_path, monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["ua"] = request.get_header("User-agent")
        seen["url"] = request.full_url
        return io.BytesIO(b"zipbytes")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    target = dump_mod.download_dump(tmp_path / "d.zip")
    assert seen["ua"] == "Undercut/0.1"
    assert "dump_type=csv" in seen["url"]
    assert target.read_bytes() == b"zipbytes"
