"""Batch 2: mesh + material + copy texture/audio/font.

pakai: python3 -m u2g.batch2 SRC_ROOT MANIFEST.json OUT_ROOT
Keluaran: OUT_ROOT/{models,materials,texture,audio,font,conversion.json}
Tidak mengubah SRC_ROOT.
"""
import json
import os
import sys

from .assetcopy import copy_assets
from .guidmap import parse_meta_guid
from .matconv import convert_mat_file
from .meshconv import convert_mesh_file, safe_stem
from .scanner import scan_to_json


def _tex_guid_map(manifest, src_root, dst_root):
    """{guid: path_rel_tujuan} untuk file tekstur (dari .meta sebelahnya)."""
    m = {}
    for f in manifest.get("files", []):
        if f["category"] != "texture":
            continue
        meta = os.path.join(src_root, f["path"] + ".meta")
        g = parse_meta_guid(meta) if os.path.isfile(meta) else None
        if g:
            m[g.lower()] = os.path.join("texture", f["path"])
    return m


def run_batch2(src_root, manifest_path, out_root):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    models = os.path.join(out_root, "models")
    materials = os.path.join(out_root, "materials")
    os.makedirs(models, exist_ok=True)
    os.makedirs(materials, exist_ok=True)

    summary = {"mesh": {"ok": 0, "skipped": {}, "failed": {}, "faces_skipped": 0},
               "material": {"ok": 0, "failed": {}, "warnings": 0},
               "copy": {}}
    for f in manifest.get("files", []):
        if not f["path"].endswith(".asset"):
            continue
        st = convert_mesh_file(os.path.join(src_root, f["path"]),
                               os.path.join(models, safe_stem(f["path"][:-6]) + ".obj"))
        s = summary["mesh"]
        if st["ok"]:
            s["ok"] += 1
            s["faces_skipped"] += st.get("skipped_faces", 0)
        elif st.get("skipped"):
            s["skipped"][st["reason"]] = s["skipped"].get(st["reason"], 0) + 1
        else:
            s["failed"][f["path"]] = st["reason"]

    guid_tex = _tex_guid_map(manifest, src_root, out_root)
    for f in manifest.get("files", []):
        if f["category"] != "material":
            continue
        st = convert_mat_file(os.path.join(src_root, f["path"]),
                              os.path.join(materials, safe_stem(f["path"]) + ".tres"),
                              guid_tex)
        s = summary["material"]
        if st["ok"]:
            s["ok"] += 1
            s["warnings"] += len(st["warnings"])
        else:
            s["failed"][f["path"]] = st["reason"]

    summary["copy"] = copy_assets(manifest, src_root, out_root)
    with open(os.path.join(out_root, "conversion.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    return summary


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--rescan":
        print("pakai: batch2.py SRC_ROOT MANIFEST.json OUT_ROOT [--rescan]")
        sys.exit(0)
    if len(sys.argv) < 4:
        sys.exit("pakai: batch2.py SRC_ROOT MANIFEST.json OUT_ROOT")
    src, man, out = sys.argv[1], sys.argv[2], sys.argv[3]
    if not os.path.isfile(man):
        scan_to_json(src, man)
        print("manifest dibuat ulang")
    s = run_batch2(src, man, out)
    print("mesh ok=%d faces_skipped=%d" % (s["mesh"]["ok"], s["mesh"]["faces_skipped"]))
    print("mesh skip:", s["mesh"]["skipped"])
    print("mesh gagal=%d material ok=%d warn=%d" % (
        len(s["mesh"]["failed"]), s["material"]["ok"], s["material"]["warnings"]))
    print("copy:", s["copy"]["copied"], "hilang:", len(s["copy"]["missing"]))
