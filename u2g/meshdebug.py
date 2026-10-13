"""Debug: bedah file .asset yang gagal parse (alasan + angka layout).

pakai: python3 -m u2g.meshdebug FILE.asset
      python3 -m u2g.meshdebug --find DIR ALASAN_SUBSTRING
"""
import os
import re
import sys

from .meshconv import FMT_SIZE, parse_mesh


def diagnose(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            t = f.read()
    except OSError as e:
        return {"file": path, "error": str(e)[:100]}
    _, err = parse_mesh(path)
    info = {"file": path, "parse": err or "OK"}
    nv = re.search(r"m_VertexCount:\s*(\d+)", t)
    info["verts"] = int(nv.group(1)) if nv else None
    chans = re.findall(
        r"-\s*stream:\s*(\d+)\s*offset:\s*(\d+)\s*format:\s*(\d+)\s*dimension:\s*(\d+)", t)
    info["channels"] = [(int(s), int(o), int(f), int(d)) for s, o, f, d in chans]
    dm = re.search(r"_typelessdata:\s*([0-9a-fA-F]+)", t)
    info["blob_bytes"] = len(dm.group(1)) // 2 if dm else 0
    need = 0
    streams = {}
    for s, o, f, d in info["channels"]:
        streams.setdefault(s, 0)
        if d:
            streams[s] = max(streams[s], o + FMT_SIZE.get(f, 0) * d)
    info["stream_stride"] = streams
    if info["verts"]:
        info["need_bytes"] = sum(v * info["verts"] for v in streams.values())
    sm = re.search(r"size:\s*(\d+)", t)
    info["stream_size"] = int(sm.group(1)) if sm else None
    ib = re.search(r"m_IndexBuffer:\s*([0-9a-fA-F]*)", t)
    info["index_bytes"] = len(ib.group(1)) // 2 if ib else 0
    docs = len(re.findall(r"--- !u!\d+", t))
    info["docs"] = docs
    return info


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--find":
        root, want = sys.argv[2], sys.argv[3]
        n = 0
        for dp, _, fs in os.walk(root):
            for f in sorted(fs):
                if not f.endswith(".asset"):
                    continue
                _, err = parse_mesh(os.path.join(dp, f))
                if err and want in err:
                    print(os.path.join(dp, f), "=>", err)
                    n += 1
                    if n >= 3:
                        sys.exit(0)
    elif len(sys.argv) == 2:
        info = diagnose(sys.argv[1])
        for k, v in info.items():
            print("%s: %s" % (k, v))
    else:
        sys.exit("pakai: meshdebug.py FILE | --find DIR ALASAN")
