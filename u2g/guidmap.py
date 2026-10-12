"""GUID map: baca file .meta Unity -> {guid: path_relatif}.

Sumber GUID satu-satunya adalah isi file .meta (baris 'guid: ...').
Tidak menebak, tidak mengarang: file tanpa guid tercatat tanpa guid.
"""
import os

META_DIRS_SKIP = set()


def parse_meta_guid(meta_path):
    """Kembalikan guid dari file .meta, atau None."""
    try:
        with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                s = line.strip()
                if s.startswith("guid:"):
                    g = s.split(":", 1)[1].strip()
                    return g or None
    except OSError:
        return None
    return None


def build_guid_map(root):
    """Susuri root, petakan guid -> path relatif file aset (tanpa .meta).

    Kembalikan (guid_map, duplikat, tanpa_guid):
    - guid_map: {guid: relpath}
    - duplikat: {guid: [relpath...]} bila satu guid dipakai >1 file
    - tanpa_guid: [relpath...] file .meta tanpa guid terbaca
    """
    guid_map = {}
    duplikat = {}
    tanpa_guid = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".godot", "Library", "Temp", "Obj")]
        for fn in filenames:
            if not fn.endswith(".meta"):
                continue
            meta = os.path.join(dirpath, fn)
            rel = os.path.relpath(meta[:-5], root)
            g = parse_meta_guid(meta)
            if not g:
                tanpa_guid.append(rel)
                continue
            if g in guid_map:
                duplikat.setdefault(g, [guid_map[g]]).append(rel)
            else:
                guid_map[g] = rel
    return guid_map, duplikat, tanpa_guid
