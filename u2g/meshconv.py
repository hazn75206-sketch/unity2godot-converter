"""Mesh Unity (.asset YAML, typelessdata) -> Wavefront OBJ (Godot-ready).

Unity kidal -> Godot kanan: X dinegasi + winding dibalik.
Hanya stream 0, topologi segitiga. Normal/UV bila ada, tangent/color dibuang.
Fungsi murni (parse_mesh/to_obj) + convert_* untuk batch. Status selalu eksplisit.
"""
import os
import re
import struct

FMT_SIZE = {0: 4, 1: 2, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 1, 8: 1, 9: 2, 10: 2, 11: 4, 12: 4}
FLOAT_FMTS = {0: "f", 1: "e"}


def _norm_val(fmt, raw):
    if fmt in FLOAT_FMTS:
        return float(raw)
    bits = FMT_SIZE[fmt] * 8
    if fmt in (4, 6, 8, 10, 12):
        return max(-1.0, min(1.0, raw / (1 << (bits - 1))))
    if fmt == 2:
        return raw / 255.0
    hi = (1 << bits) - 1
    return (raw / hi) * 2.0 - 1.0 if fmt in (3, 5) else raw


def _unpack_chan(blob, off, fmt, dim):
    size = FMT_SIZE[fmt]
    out = []
    for i in range(dim):
        chunk = blob[off + i * size: off + (i + 1) * size]
        if fmt in FLOAT_FMTS:
            (v,) = struct.unpack("<" + FLOAT_FMTS[fmt], chunk)
            out.append(float(v))
        elif fmt in (7, 9, 11):
            out.append(int.from_bytes(chunk, "little", signed=False))
        elif fmt in (8, 10, 12):
            out.append(int.from_bytes(chunk, "little", signed=True))
        else:
            ival = int.from_bytes(chunk, "little", signed=(fmt in (4, 6)))
            out.append(_norm_val(fmt, ival))
    return out


def parse_mesh(path):
    """Kembalikan (mesh_dict, None) atau (None, alasan_skip)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        t = f.read()
    m = re.search(r"m_VertexCount:\s*(\d+)", t)
    if not m:
        return None, "bukan mesh vertexdata"
    nv = int(m.group(1))
    chans = re.findall(
        r"-\s*stream:\s*(\d+)\s*offset:\s*(\d+)\s*format:\s*(\d+)\s*dimension:\s*(\d+)", t)
    if not chans:
        return None, "tanpa channel vertex"
    if any(int(f) not in FMT_SIZE for _, _, f, _ in chans):
        return None, "format channel tak dikenal"
    # kelompokkan per stream (blob = stream0 lalu stream1, ...)
    streams = {}
    for sem, (s, o, f, d) in enumerate([(int(s), int(o), int(f), int(d)) for s, o, f, d in chans]):
        streams.setdefault(s, {"stride": 0, "chans": []})
        streams[s]["chans"].append((sem, o, f, d))
        if d:
            streams[s]["stride"] = max(streams[s]["stride"], o + FMT_SIZE[f] * d)
    nstreams = max(streams) + 1
    if any(s not in streams for s in range(nstreams)):
        return None, "stream tak berurutan"
    dm = re.search(r"_typelessdata:\s*([0-9a-fA-F]+)", t)
    blob = bytes.fromhex(dm.group(1)) if dm else b""
    if not blob:
        sm = re.search(r"m_StreamData:\s*\n\s*serializedVersion:\s*\d+\s*\n\s*offset:\s*(\d+)\s*\n\s*size:\s*(\d+)", t)
        if sm and int(sm.group(2)) == 0:
            return None, "stream data kosong (vertex tak ter-rip)"
        return None, "typelessdata kosong"
    bases = {}
    off = 0
    for s in range(nstreams):
        bases[s] = off
        off += streams[s]["stride"] * nv
    if len(blob) < off:
        return None, "ukuran data tak cocok"
    ib = re.search(r"m_IndexBuffer:\s*([0-9a-fA-F]+)", t)
    idxfmt = re.search(r"m_IndexFormat:\s*(\d+)", t)
    is32 = bool(idxfmt and int(idxfmt.group(1)) == 1)
    isz = 4 if is32 else 2
    iblob = bytes.fromhex(ib.group(1)) if ib else b""
    idx = [int.from_bytes(iblob[i * isz:(i + 1) * isz], "little")
           for i in range(len(iblob) // isz)]
    subs = re.findall(
        r"firstByte:\s*(\d+)\s*indexCount:\s*(\d+)\s*topology:\s*(\d+)\s*baseVertex:\s*(\d+)\s*firstVertex:\s*(\d+)", t)
    def chan(sem):
        for s in range(nstreams):
            for se, o, f, d in streams[s]["chans"]:
                if se == sem and d:
                    return (s, o, f, d)
        return None

    cpos, cnrm = chan(0), chan(1)
    cuv = None
    for sem in range(4, len(chans)):
        c = chan(sem)
        if c and c[3] >= 2:
            cuv = c
            break
    pos, nrm, uv = [], [], []
    for v in range(nv):
        if cpos:
            s, o, f, d = cpos
            p = _unpack_chan(blob, bases[s] + v * streams[s]["stride"] + o, f, d)
            pos.append((-p[0], p[1], p[2]) if len(p) >= 3 else (0, 0, 0))
        else:
            pos.append((0, 0, 0))
        if cnrm and cnrm[3] >= 3:
            s, o, f, d = cnrm
            n = _unpack_chan(blob, bases[s] + v * streams[s]["stride"] + o, f, d)
            nrm.append((-n[0], n[1], n[2]))
        else:
            nrm.append(None)
        if cuv:
            s, o, f, d = cuv
            u = _unpack_chan(blob, bases[s] + v * streams[s]["stride"] + o, f, d)
            uv.append((u[0], u[1]))
        else:
            uv.append(None)
    return {
        "nv": nv, "pos": pos, "nrm": nrm, "uv": uv, "idx": idx,
        "subs": [(int(a) // isz, int(b), int(c), int(e)) for a, b, c, _, e in subs],
    }, None


def to_obj(mesh, name):
    """Mesh dict -> teks OBJ. Face invalid dilewati dan dihitung."""
    L = ["# %s (Unity->Godot)\n" % name]
    for p in mesh["pos"]:
        L.append("v %.6f %.6f %.6f\n" % p)
    has_uv = any(u is not None for u in mesh["uv"])
    has_n = any(n is not None for n in mesh["nrm"])
    if has_uv:
        for u in mesh["uv"]:
            L.append("vt %.6f %.6f\n" % (u if u else (0, 0)))
    if has_n:
        for n in mesh["nrm"]:
            L.append("vn %.6f %.6f %.6f\n" % (n if n else (0, 0, 1)))
    idx = mesh["idx"]
    nv = mesh["nv"]
    subs = mesh["subs"] or [(0, len(idx), 0, 0)]
    skipped = 0
    for s, (start, count, topo, firstv) in enumerate(subs):
        if topo != 0:
            continue
        seg = idx[start:start + count]
        cand = [v + firstv for v in seg]
        use_off = firstv if (cand and max(cand) < nv) else 0
        L.append("g sub%d\n" % s)
        for i in range(0, len(seg) - 2, 3):
            tri = [seg[i + k] + use_off + 1 for k in (0, 2, 1)]
            if any(v < 1 or v > nv for v in tri):
                skipped += 1
                continue
            a, c, b = tri
            if has_uv and has_n:
                L.append("f %d/%d/%d %d/%d/%d %d/%d/%d\n" % (a, a, a, c, c, c, b, b, b))
            elif has_n:
                L.append("f %d//%d %d//%d %d//%d\n" % (a, a, c, c, b, b))
            elif has_uv:
                L.append("f %d/%d %d/%d %d/%d\n" % (a, a, c, c, b, b))
            else:
                L.append("f %d %d %d\n" % (a, c, b))
    if skipped:
        L.append("# skipped %d invalid faces\n" % skipped)
    return "".join(L), skipped


def convert_mesh_file(src, dst):
    """Satu file. Kembalikan dict status."""
    mesh, err = parse_mesh(src)
    if err:
        return {"ok": False, "skipped": True, "reason": err}
    try:
        text, skipped_faces = to_obj(mesh, os.path.basename(dst))
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        return {"ok": True, "verts": mesh["nv"], "faces": sum(
            1 for line in text.splitlines() if line.startswith("f ")),
            "skipped_faces": skipped_faces}
    except OSError as e:
        return {"ok": False, "skipped": False, "reason": str(e)[:120]}


def safe_stem(filename):
    return re.sub(r"[^\w\-(). ]+", "_", filename).strip() or "mesh"


def convert_dir(src_dir, dst_dir):
    """Semua .asset di src_dir -> .obj di dst_dir. Kembalikan ringkasan."""
    os.makedirs(dst_dir, exist_ok=True)
    summary = {"ok": 0, "skipped": {}, "failed": {}, "faces_skipped": 0}
    for fn in sorted(os.listdir(src_dir)):
        if not fn.endswith(".asset"):
            continue
        st = convert_mesh_file(os.path.join(src_dir, fn),
                               os.path.join(dst_dir, safe_stem(fn[:-6]) + ".obj"))
        if st["ok"]:
            summary["ok"] += 1
            summary["faces_skipped"] += st.get("skipped_faces", 0)
        elif st.get("skipped"):
            r = st["reason"]
            summary["skipped"][r] = summary["skipped"].get(r, 0) + 1
        else:
            summary["failed"][fn] = st["reason"]
    return summary
