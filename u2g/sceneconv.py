"""Prefab/scene Unity (.prefab/.unity YAML) -> Godot .tscn.

Didukung: hierarki GameObject, Transform (kidal->kanan), MeshFilter/
MeshRenderer (+material), Camera, Light (arah/omni/spot), AudioSource,
BoxCollider (+Rigidbody). Sisanya: warning + stub Metadata bila diminta.
Referensi antar-file via GUID (peta dari .meta).
"""
import math
import os
import re

DOC_RE = re.compile(r"--- !u!(\d+)\s*&(\d+)\s*\n")


def split_docs(text):
    """Pecah YAML multi-doc Unity -> [(class_id, file_id, body)]."""
    parts = DOC_RE.split(text)
    docs = []
    for i in range(1, len(parts), 3):
        cls, fid, body = int(parts[i]), parts[i + 1], parts[i + 2]
        docs.append((cls, fid, body))
    return docs


def _vec3(body, key):
    m = re.search(r"%s:\s*\{x:\s*([-+0-9.eE]+),\s*y:\s*([-+0-9.eE]+),\s*z:\s*([-+0-9.eE]+)\}" % key, body)
    return tuple(float(m.group(i)) for i in range(1, 4)) if m else (0.0, 0.0, 0.0)


def _quat(body, key):
    m = re.search(r"%s:\s*\{x:\s*([-+0-9.eE]+),\s*y:\s*([-+0-9.eE]+),\s*z:\s*([-+0-9.eE]+),\s*w:\s*([-+0-9.eE]+)\}" % key, body)
    return tuple(float(m.group(i)) for i in range(1, 5)) if m else (0.0, 0.0, 0.0, 1.0)


def _ref_list(body, key):
    return re.findall(r"-\s*component:\s*\{fileID:\s*(\d+)\}", body) if key == "m_Component" else []


def _guid_ref(body, key):
    m = re.search(r"%s:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-fA-F]{32})" % key, body)
    return m.group(1).lower() if m else None


def _all_guid_refs(body, key):
    sec = re.search(r"%s:(.*?)(?:\n  [A-Za-z_]|\Z)" % key, body, re.S)
    scope = sec.group(1) if sec else body
    return [g.lower() for g in re.findall(r"guid:\s*([0-9a-fA-F]{32})", scope)]


def quat_to_basis(q):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return (
        1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
        2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
        2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y),
    )


def unity_to_godot_transform(pos, quat, scale):
    """Unity (kidal) -> Godot (kanan): mirror sumbu X."""
    qx, qy, qz, qw = quat
    b = quat_to_basis((qx, -qy, -qz, qw))
    px, py, pz = -pos[0], pos[1], pos[2]
    sx, sy, sz = scale
    return (b[0] * sx, b[1] * sx, b[2] * sx,
            b[3] * sy, b[4] * sy, b[5] * sy,
            b[6] * sz, b[7] * sz, b[8] * sz,
            px, py, pz)


def parse_prefab(text):
    """Kembalikan (gameobjects, components). gameobjects: {fid: {...}}."""
    gos, comps = {}, {}
    for cls, fid, body in split_docs(text):
        if cls == 1:
            name = re.search(r"m_Name:\s*(.+)", body)
            gos[fid] = {
                "name": name.group(1).strip() if name else "GameObject",
                "active": "m_IsActive: 1" in body,
                "components": _ref_list(body, "m_Component"),
            }
        else:
            comps[fid] = {"class": cls, "body": body}
    for fid, go in gos.items():
        t = None
        for cfid in go["components"]:
            c = comps.get(cfid)
            if c and c["class"] == 4:
                t = c["body"]
                break
        if t:
            go["pos"] = _vec3(t, "m_LocalPosition")
            go["quat"] = _quat(t, "m_LocalRotation")
            go["scale"] = _vec3(t, "m_LocalScale") or (1.0, 1.0, 1.0)
            if go["scale"] == (0.0, 0.0, 0.0):
                go["scale"] = (1.0, 1.0, 1.0)
            fath = re.search(r"m_Father:\s*\{fileID:\s*(\d+)\}", t)
            go["father"] = fath.group(1) if fath and fath.group(1) != "0" else None
        else:
            go["pos"], go["quat"], go["scale"], go["father"] = (0, 0, 0), (0, 0, 0, 1), (1, 1, 1), None
    return gos, comps


def _comp_of(go, comps, classes):
    if isinstance(classes, int):
        classes = (classes,)
    for cfid in go["components"]:
        c = comps.get(cfid)
        if c and c["class"] in classes:
            return c["body"]
    return None


def build_tscn(gos, comps, mesh_guid_to_obj, mat_guid_to_tres, tex_guid_to_path):
    """Kembalikan (teks_tscn, warnings, stats). Path obj/tres/tex = path res://."""
    warnings, stats = [], {"nodes": 0, "mesh": 0, "unsupported": {}}
    ext = {}
    lines = []

    def ext_id(kind, path):
        key = (kind, path)
        if key not in ext:
            ext[key] = str(len(ext) + 1)
        return ext[key]

    # urutan: root dulu (DFS), lalu anak
    order, seen = [], set()

    # petakan father component -> gameobject
    comp_to_go = {}
    for fid, go in gos.items():
        for cfid in go["components"]:
            comp_to_go[cfid] = fid
    for fid, go in gos.items():
        f = go.get("father")
        go["father_go"] = comp_to_go.get(f) if f else None
    children = {}
    for k, g in gos.items():
        fg = g.get("father_go")
        if fg and fg in gos:
            children.setdefault(fg, []).append(k)
    for fid in gos:
        if not gos[fid].get("father_go"):
            # DFS iteratif, total O(n)
            stack = [fid]
            while stack:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                order.append(cur)
                stack.extend(reversed(children.get(cur, [])))

    node_paths = {}
    used_names = {}
    body_lines = []
    for fid in order:
        go = gos[fid]
        name = re.sub(r"[^\w\- ]+", "_", go["name"]).strip() or "Node"
        parent = node_paths.get(go.get("father_go"), ".")
        key = (parent, name)
        n = used_names.get(key, 0)
        used_names[key] = n + 1
        if n:
            name = "%s@%d" % (name, n + 1)
        mesh_body = _comp_of(go, comps, 33)
        mesh_guid = _guid_ref(mesh_body, "m_Mesh") if mesh_body else None
        obj_path = mesh_guid_to_obj.get(mesh_guid) if mesh_guid else None
        camb = _comp_of(go, comps, 20)
        lightb = _comp_of(go, comps, 108)
        if obj_path:
            ntype = "MeshInstance3D"
            stats["mesh"] += 1
        elif camb:
            ntype = "Camera3D"
        elif lightb:
            ltype = re.search(r"m_Type:\s*(\d+)", lightb)
            ntype = {"0": "SpotLight3D", "1": "DirectionalLight3D"}.get(
                ltype.group(1) if ltype else "", "OmniLight3D")
        else:
            ntype = "Node3D"
        if mesh_guid and not obj_path:
            warnings.append("mesh guid %s tak ketemu (%s)" % (mesh_guid, name))
        tr = unity_to_godot_transform(go["pos"], go["quat"], go["scale"])
        path = name if parent == "." else parent + "/" + name
        node_paths[fid] = path
        stats["nodes"] += 1
        body_lines.append('[node name="%s" type="%s" parent="%s"]' % (name, ntype, parent))
        body_lines.append("transform = Transform3D(%s)" % ", ".join(
            ("%.5f" % v).rstrip("0").rstrip(".") if abs(v) >= 0.000005 else "0" for v in tr))
        if not go["active"]:
            body_lines.append("visible = false")
        if obj_path:
            body_lines.append('mesh = ExtResource("%s")' % ext_id("ArrayMesh", obj_path))
            rend = _comp_of(go, comps, 23)
            if rend:
                mguids = _all_guid_refs(rend, "m_Materials")
                for mi, mg in enumerate(mguids[:4]):
                    tp = mat_guid_to_tres.get(mg)
                    if tp:
                        body_lines.append('surface_material_override/%d = ExtResource("%s")' % (
                            mi, ext_id("StandardMaterial3D", tp)))
                    else:
                        warnings.append("material guid %s tak ketemu (%s)" % (mg, name))
        else:
            rend = _comp_of(go, comps, 23)
            if rend:
                mguids = _all_guid_refs(rend, "m_Materials")
                if mguids:
                    warnings.append("renderer tanpa mesh, %d material dilewati (%s)" % (len(mguids), name))
        # kamera / cahaya / audio / collider / fisika
        if ntype == "Camera3D" and camb:
            fov = re.search(r"field of view:\s*([-+0-9.eE]+)", camb)
            body_lines.append("fov = %.2f" % float(fov.group(1)) if fov else "fov = 60.0")
        if ntype in ("OmniLight3D", "SpotLight3D", "DirectionalLight3D"):
            warnings.append("Light %s: cek range/angle manual" % name)
        audb = _comp_of(go, comps, 82)
        if audb:
            warnings.append("AudioSource %s: assign klip manual" % name)
        boxb = _comp_of(go, comps, 65)
        if boxb:
            sz = _vec3(boxb, "m_Size") or (1.0, 1.0, 1.0)
            body_lines.append("# BoxCollider size=(%.2f, %.2f, %.2f): tambah CollisionShape manual" % sz)
        # komponen tak didukung
        for cfid in go["components"]:
            c = comps.get(cfid)
            if c and c["class"] not in (1, 4, 20, 23, 33, 54, 65, 82, 108, 114):
                stats["unsupported"][c["class"]] = stats["unsupported"].get(c["class"], 0) + 1
        if _comp_of(go, comps, 54):
            warnings.append("Rigidbody %s: setel fisika manual" % name)
        body_lines.append("")

    head = ["[gd_scene load_steps=%d format=3]\n" % (len(ext) + 1), ""]
    for (kind, path), eid in sorted(ext.items(), key=lambda kv: int(kv[1])):
        head.append('[ext_resource type="%s" path="%s" id="%s"]' % (kind, path, eid))
    if ext:
        head.append("")
    return "\n".join(head + body_lines), warnings, stats
