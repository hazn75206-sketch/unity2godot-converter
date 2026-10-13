"""Batch 4: script templates + builder + report.

pakai: python3 -m u2g.batch4 SRC_ROOT MANIFEST.json OUT_ROOT PROJECT_NAME
Butuh conversion.json + scene-conversion.json dari batch 2/3 (boleh kosong).
"""
import json
import os
import sys

from .builder import build_project, copy_manifest
from .report import build_report
from .scriptscan import scan_scripts


def run_batch4(src_root, manifest_path, out_root, project_name):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    scripts = scan_scripts(manifest, src_root, os.path.join(out_root, "scripts"))
    conv = {}
    for fn, key in (("conversion.json", "conversion"),
                    ("scene-conversion.json", "scene")):
        p = os.path.join(out_root, fn)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                conv[key] = json.load(f)
    parts = {"conversion": conv.get("conversion", {}),
             "scene": conv.get("scene", {}), "scripts": scripts}
    build_project(out_root, project_name)
    copy_manifest(manifest_path, out_root)
    report = build_report(parts, os.path.join(out_root, "migration", "report.json"))
    return {"scripts": scripts, "report": report}


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit("pakai: batch4.py SRC_ROOT MANIFEST.json OUT_ROOT PROJECT_NAME")
    r = run_batch4(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print("template=%d gagal=%d status=%s" % (
        r["scripts"]["template"], len(r["scripts"]["failed"]), r["report"]["status"]))
