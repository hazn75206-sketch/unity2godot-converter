"""Copy aset kompatibel (tekstur/audio/font) dgn struktur folder dipertahankan.

Sumber: manifest scanner. Tidak konversi isi, hanya salin + laporkan.
"""
import os
import shutil

COPY_CATEGORIES = ("texture", "audio", "font")


def copy_assets(manifest, src_root, dst_root):
    """Salin file berkategori COPY_CATEGORIES. Kembalikan ringkasan."""
    summary = {"copied": 0, "missing": [], "failed": {}}
    for f in manifest.get("files", []):
        if f["category"] not in COPY_CATEGORIES:
            continue
        src = os.path.join(src_root, f["path"])
        dst = os.path.join(dst_root, f["category"], f["path"])
        if not os.path.isfile(src):
            summary["missing"].append(f["path"])
            continue
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            summary["copied"] += 1
        except OSError as e:
            summary["failed"][f["path"]] = str(e)[:120]
    return summary
