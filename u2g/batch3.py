"""Batch 3: prefab/scene Unity -> .tscn Godot.

pakai: python3 -m u2g.batch3 SRC_ROOT MANIFEST.json OUT_ROOT
Harus jalan SETELAH batch2 (butuh models/, materials/, texture/ di OUT_ROOT).
Keluaran: OUT_ROOT/scenes/<struktur>.tscn + scene-conversion.json
"""
import json
import os
import sys

from .guidmap import parse_meta_guid
from .meshconv import safe_stem
from .sceneconv import build_tscn, parse_prefab


def _guid_of(src_root, rel_path):
    meta = os.path.join(src_root, rel_path + ".meta")
    if os.path.isfile(meta):
        g = parse_meta_guid(meta)
        return g.lower() if g else None
    return None


def _build_maps(manifest, src_root, out_root):
    mesh_map, mat_map, tex_map = {}, {}, {}

    def _res(p):
        return "res://" + p.replace(os.sep, "/")
    for f in manifest.get("files", []):
        p = f["path"]
        if p.endswith(".asset") and f["category"] == "data":
            obj = os.path.join(out_root, "models", safe_stem(p[:-6]) + ".obj")
            if os.path.isfile(obj):
                g = _guid_of(src_root, p)
                if g:
                    mesh_map[g] = _res(os.path.join("models", safe_stem(p[:-6]) + ".obj"))
        elif f["category"] == "material":
            base = p[:-4] if p.endswith(".mat") else p
            tres = os.path.join(out_root, "materials", safe_stem(base) + ".tres")
            if os.path.isfile(tres):
                g = _guid_of(src_root, p)
                if g:
                    mat_map[g] = _res(os.path.join("materials", safe_stem(base) + ".tres"))
        elif f["category"] == "texture":
            dst = os.path.join(out_root, "texture", p)
            if os.path.isfile(dst):
                g = _guid_of(src_root, p)
                if g:
                    tex_map[g] = _res(os.path.join("texture", p))
    return mesh_map, mat_map, tex_map


def run_batch3(src_root, manifest_path, out_root):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    mesh_map, mat_map, tex_map = _build_maps(manifest, src_root, out_root)
    scenes_dir = os.path.join(out_root, "scenes")
    os.makedirs(scenes_dir, exist_ok=True)
    summary = {"scenes": 0, "prefabs": 0, "nodes": 0, "meshes": 0,
               "warnings": 0, "unsupported": {}, "failed": {}}
    targets = [f for f in manifest.get("files", [])
               if f["category"] in ("scene", "prefab")]
    for n, f in enumerate(targets):
        if n % 25 == 0:
            print("scene %d/%d ..." % (n, len(targets)), flush=True)
        src = os.path.join(src_root, f["path"])
        try:
            with open(src, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            gos, comps = parse_prefab(text)
            if not gos:
                summary["failed"][f["path"]] = "tanpa GameObject"
                continue
            tscn, warnings, stats = build_tscn(gos, comps, mesh_map, mat_map, tex_map)
            rel = f["path"]
            rel = rel[:-7] + ".tscn" if rel.endswith(".prefab") else rel[:-6] + ".tscn"
            dst = os.path.join(scenes_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(tscn)
            summary["scenes" if f["category"] == "scene" else "prefabs"] += 1
            summary["nodes"] += stats["nodes"]
            summary["meshes"] += stats["mesh"]
            summary["warnings"] += len(warnings)
            for k, v in stats["unsupported"].items():
                summary["unsupported"][str(k)] = summary["unsupported"].get(str(k), 0) + v
        except OSError as e:
            summary["failed"][f["path"]] = str(e)[:120]
    with open(os.path.join(out_root, "scene-conversion.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    return summary


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("pakai: batch3.py SRC_ROOT MANIFEST.json OUT_ROOT")
    s = run_batch3(sys.argv[1], sys.argv[2], sys.argv[3])
    print("scene=%d prefab=%d nodes=%d mesh=%d warn=%d gagal=%d" % (
        s["scenes"], s["prefabs"], s["nodes"], s["meshes"],
        s["warnings"], len(s["failed"])))
    print("unsupported:", s["unsupported"])
