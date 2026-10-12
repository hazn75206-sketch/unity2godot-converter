"""Project scanner: baca project Unity rekursif -> manifest JSON.

Mendeteksi struktur Assets/Packages/ProjectSettings, mengkategorikan
berkas per ekstensi, memetakan GUID, menandai status migrasi awal.
Tidak mengubah project sumber (read-only).
"""
import json
import os

from .guidmap import build_guid_map

CATEGORY_BY_EXT = {
    ".unity": "scene", ".prefab": "prefab", ".asset": "data",
    ".mat": "material", ".anim": "animation", ".controller": "animation",
    ".overrideController": "animation", ".cs": "script",
    ".fbx": "model", ".obj": "model", ".gltf": "model", ".glb": "model",
    ".dae": "model", ".blend": "model",
    ".png": "texture", ".jpg": "texture", ".jpeg": "texture",
    ".tga": "texture", ".psd": "texture", ".bmp": "texture",
    ".wav": "audio", ".mp3": "audio", ".ogg": "audio",
    ".ttf": "font", ".otf": "font",
    ".shader": "shader", ".compute": "shader", ".cginc": "shader",
    ".asmdef": "config", ".json": "config",
    ".mp4": "video", ".mov": "video",
}

SKIP_DIRS = {".git", ".godot", "Library", "Temp", "Obj", "Logs"}


def categorize(filename):
    _, ext = os.path.splitext(filename.lower())
    if filename.endswith(".meta"):
        return "meta"
    return CATEGORY_BY_EXT.get(ext, "other")


def scan_project(root):
    """Kembalikan dict manifest. Tidak menulis apa pun ke root."""
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise ValueError("bukan direktori: %s" % root)
    assets_dir = os.path.join(root, "Assets")
    has_assets = os.path.isdir(assets_dir)

    files = []
    unreadable = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".meta"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                size = os.path.getsize(full)
            except OSError:
                unreadable.append(rel)
                continue
            files.append({"path": rel, "ext": os.path.splitext(fn.lower())[1],
                          "size": size, "category": categorize(fn)})

    guid_map, duplikat, tanpa_guid = build_guid_map(root)

    by_cat = {}
    for f in files:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1

    kind = "unknown"
    if by_cat.get("model", 0) + by_cat.get("prefab", 0) > 0 and by_cat.get("scene", 0):
        kind = "3d" if by_cat.get("texture", 0) else "mixed"
    if kind == "unknown" and files:
        kind = "mixed"

    return {
        "root": root,
        "has_assets_layout": has_assets,
        "kind": kind,
        "total_files": len(files),
        "by_category": by_cat,
        "files": sorted(files, key=lambda x: x["path"]),
        "guid_count": len(guid_map),
        "guid_duplicates": duplikat,
        "meta_without_guid": tanpa_guid,
        "unreadable": unreadable,
    }


def scan_to_json(root, out_path):
    manifest = scan_project(root)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    return manifest


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        sys.exit("pakai: scanner.py ROOT_PROJECT OUT.json")
    m = scan_to_json(sys.argv[1], sys.argv[2])
    print("files=%d guid=%d kind=%s" % (m["total_files"], m["guid_count"], m["kind"]))
    print("kategori:", m["by_category"])
