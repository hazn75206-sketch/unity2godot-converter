import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from u2g.scanner import scan_project


def _proj(tmp_path):
    a = tmp_path / "Assets"
    (a / "Tex").mkdir(parents=True)
    (a / "hero.png").write_bytes(b"\x89PNG")
    (a / "Tex" / "hero.png.meta").write_text("fileFormatVersion: 2\nguid: abc123\n")
    (a / "go.prefab").write_text("%YAML 1.1\n")
    (a / "go.prefab.meta").write_text("fileFormatVersion: 2\nguid: abc123\n")
    return str(tmp_path)


def test_scan_counts(tmp_path):
    m = scan_project(_proj(tmp_path))
    assert m["total_files"] == 2
    assert m["by_category"]["texture"] == 1
    assert m["by_category"]["prefab"] == 1
    assert m["guid_count"] == 1
    assert len(m["guid_duplicates"]["abc123"]) == 2
    assert m["kind"] in ("mixed", "3d")


def test_scan_bukan_dir(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        scan_project(str(tmp_path / "hilang"))
