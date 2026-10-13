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

# Nama komponen Unity dari ClassID resmi (docs.unity3d.com ClassIDReference).
CLASS_NAMES = {
    1: "GameObject", 4: "Transform", 20: "Camera", 21: "Material",
    23: "MeshRenderer", 28: "Texture2D", 33: "MeshFilter", 43: "Mesh",
    54: "Rigidbody", 64: "MeshCollider", 65: "BoxCollider",
    81: "AudioListener", 82: "AudioSource", 83: "AudioClip", 90: "Avatar",
    95: "Animator", 108: "Light", 111: "Animation", 114: "MonoBehaviour",
    115: "MonoScript", 120: "LineRenderer", 128: "Font",
    134: "PhysicMaterial", 135: "SphereCollider", 136: "CapsuleCollider",
    137: "SkinnedMeshRenderer", 143: "CharacterController", 146: "WheelCollider",
    153: "ConfigurableJoint", 154: "TerrainCollider",
    195: "NavMeshAgent", 198: "ParticleSystem", 199: "ParticleSystemRenderer",
    205: "LODGroup", 208: "NavMeshObstacle", 212: "SpriteRenderer",
    215: "ReflectionProbe", 218: "Terrain", 220: "LightProbeGroup",
    222: "CanvasRenderer", 223: "Canvas", 224: "RectTransform",
}


def class_name(cid):
    return CLASS_NAMES.get(cid, "class_%d" % cid)


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
            if c and c["class"] in (4, 224):
                t = c["body"]
                go["is_rect"] = (c["class"] == 224)
                go["rect_body"] = t
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


def _rect_props(body):
    """Ambil data RectTransform. Kembalikan dict, None bila bukan rect."""
    if "m_AnchorMin" not in body:
        return None
    def _xy(key):
        m = re.search(r"%s:\s*\{x:\s*([-+0-9.eE]+),\s*y:\s*([-+0-9.eE]+)\}" % key, body)
        return (float(m.group(1)), float(m.group(2))) if m else (0.5, 0.5)
    return {"amin": _xy("m_AnchorMin"), "amax": _xy("m_AnchorMax"),
            "apos": _xy("m_AnchoredPosition"),
            "size": _xy("m_SizeDelta"), "pivot": _xy("m_Pivot")}


def rect_to_control(rect):
    """RectTransform Unity -> props Control Godot. Kembalikan dict anchor/offset."""
    (al, ab) = rect["amin"]
    (ar, at) = rect["amax"]
    (apx, apy) = rect["apos"]
    (sw, sh) = rect["size"]
    (pvx, pvy) = rect["pivot"]
    return {
        "anchor_left": al, "anchor_top": 1.0 - at,
        "anchor_right": ar, "anchor_bottom": 1.0 - ab,
        "offset_left": apx - pvx * sw,
        "offset_top": -(apy + (1.0 - pvy) * sh),
        "offset_right": apx + (1.0 - pvx) * sw,
        "offset_bottom": -(apy - pvy * sh),
        "pivot_x": pvx * sw, "pivot_y": (1.0 - pvy) * sh,
    }


def detect_ui_mb(body):
    """Deteksi komponen UI Unity dari properti MonoBehaviour.
    Kembalikan (jenis, info) atau (None, {}). Jenis: image/text/button/rawimage.
    Urutan penting: button dulu (biasanya sekalian bawa Image)."""
    if re.search(r"m_OnClick:", body):
        return "button", {}
    if re.search(r"m_Sprite:", body):
        g = _guid_ref(body, "m_Sprite")
        col = re.search(r"m_Color:\s*\{r:\s*([-+0-9.eE]+),\s*g:\s*([-+0-9.eE]+),\s*b:\s*([-+0-9.eE]+),\s*a:\s*([-+0-9.eE]+)\}", body)
        return "image", {"guid": g, "color": tuple(float(col.group(i)) for i in range(1, 5)) if col else (1, 1, 1, 1)}
    if re.search(r"m_Texture:", body) and "m_Sprite:" not in body:
        return "rawimage", {"guid": _guid_ref(body, "m_Texture")}
    tm = re.search(r"m_Text:\s*(.*)", body) or re.search(r"m_text:\s*(.*)", body)
    if tm:
        size = re.search(r"m_FontSize:\s*(\d+)", body)
        col = re.search(r"m_Color:\s*\{r:\s*([-+0-9.eE]+),\s*g:\s*([-+0-9.eE]+),\s*b:\s*([-+0-9.eE]+),\s*a:\s*([-+0-9.eE]+)\}", body)
        align = re.search(r"m_Alignment:\s*(\d+)", body)
        return "text", {"text": tm.group(1).strip(),
                        "size": int(size.group(1)) if size else 14,
                        "color": tuple(float(col.group(i)) for i in range(1, 5)) if col else (0, 0, 0, 1),
                        "align": int(align.group(1)) % 3 if align else 1}
    for key, label in (("m_HandleRect", "Slider"), ("m_Graphic", "Toggle"),
                       ("m_TextComponent", "InputField"), ("m_Content", "ScrollRect")):
        if re.search(re.escape(key) + r":", body):
            return "manual", {"label": label}
    return None, {}
    if isinstance(classes, int):
        classes = (classes,)
    for cfid in go["components"]:
        c = comps.get(cfid)
        if c and c["class"] in classes:
            return c["body"]
    return None


def _comp_of(go, comps, classes):
    if isinstance(classes, int):
        classes = (classes,)
    for cfid in go["components"]:
        c = comps.get(cfid)
        if c and c["class"] in classes:
            return c["body"]
    return None


def _emit_ui_widget(body_lines, ext_id, ntype, ui_kind, ui_info, tex_guid_to_path, name, warnings):
    if ntype in ("TextureRect",) or ui_kind in ("image", "rawimage"):
        g = (ui_info.get("guid") or "").lower()
        tp = tex_guid_to_path.get(g) if g else None
        if tp:
            body_lines.append('texture = ExtResource("%s")' % ext_id("Texture2D", tp))
        elif g == "0000000000000000f000000000000000" or (g and g.startswith("0000000000000000")):
            warnings.append("UI %s pakai sprite bawaan Unity (tak terbawa): %s" % (name, ntype))
        elif g:
            warnings.append("tekstur UI guid %s tak ketemu (%s)" % (g, name))
        body_lines.append("expand_mode = 1")
        body_lines.append("stretch_mode = 5")
        col = ui_info.get("color", (1, 1, 1, 1))
        if col[:3] != (1, 1, 1):
            body_lines.append("modulate = Color(%.3f, %.3f, %.3f, %.3f)" % col)
    elif ntype == "Label" or ui_kind == "text":
        body_lines.append("text = %s" % _gd_str(ui_info.get("text", "")))
        body_lines.append("horizontal_alignment = %d" % ui_info.get("align", 1))
        body_lines.append("theme_override_font_sizes/font_size = %d" % ui_info.get("size", 14))
        col = ui_info.get("color", (0, 0, 0, 1))
        body_lines.append("theme_override_colors/font_color = Color(%.3f, %.3f, %.3f, %.3f)" % col)
    elif ntype == "Button" or ui_kind == "button":
        body_lines.append('text = ""')
        warnings.append("Button %s: isi teks + hubungkan pressed() manual" % name)
    if ui_kind == "manual":
        warnings.append("UI %s (%s): migrasikan manual" % (name, ui_info.get("label", "?")))


def _gd_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


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

    # tandai subtree di bawah Canvas (untuk cabang UI)
    for fid in order:
        go = gos[fid]
        fg = go.get("father_go")
        go["in_canvas"] = bool(_comp_of(go, comps, 223)) or (gos[fg].get("in_canvas") if fg in gos else False)

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
        is_ui = bool(go.get("in_canvas"))
        canvas_body = _comp_of(go, comps, 223)
        rect = _rect_props(go["rect_body"]) if go.get("is_rect") else None
        ui_kind, ui_info = (None, {})
        if is_ui and not canvas_body:
            for cfid in go["components"]:
                c = comps.get(cfid)
                if c and c["class"] == 114:
                    k, info = detect_ui_mb(c["body"])
                    if k:
                        ui_kind, ui_info = k, info
                        break
        mesh_body = _comp_of(go, comps, 33)
        mesh_guid = _guid_ref(mesh_body, "m_Mesh") if mesh_body else None
        skin_body = _comp_of(go, comps, 137)
        if not mesh_guid and skin_body:
            mesh_guid = _guid_ref(skin_body, "m_Mesh")
            if mesh_guid:
                warnings.append("SkinnedMesh %s: jadi mesh statis, bones/animasi tak ikut" % name)
        obj_path = mesh_guid_to_obj.get(mesh_guid) if mesh_guid else None
        camb = _comp_of(go, comps, 20)
        lightb = _comp_of(go, comps, 108)
        if canvas_body:
            ntype = "CanvasLayer"
            stats["canvas"] = stats.get("canvas", 0) + 1
        elif is_ui and rect is not None:
            ntype = {"image": "TextureRect", "rawimage": "TextureRect",
                     "text": "Label", "button": "Button"}.get(ui_kind, "Control")
            stats["ui"] = stats.get("ui", 0) + 1
        elif obj_path:
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
        if ntype == "CanvasLayer":
            body_lines.append("layer = 1")
        elif ntype in ("Control", "TextureRect", "Label", "Button"):
            cp = rect_to_control(rect)
            for k in ("anchor_left", "anchor_top", "anchor_right", "anchor_bottom",
                      "offset_left", "offset_top", "offset_right", "offset_bottom"):
                v = cp[k]
                body_lines.append("%s = %.4f" % (k, v))
            body_lines.append("pivot_offset = Vector2(%.2f, %.2f)" % (cp["pivot_x"], cp["pivot_y"]))
            qx, qy, qz, qw = go["quat"]
            if abs(qx) + abs(qy) < 1e-6:
                import math as _m
                ang = -2.0 * _m.atan2(qz, qw)
                if abs(ang) > 1e-4:
                    body_lines.append("rotation = %.5f" % ang)
            else:
                warnings.append("rotasi 3D pada UI %s disederhanakan" % name)
            if not go["active"]:
                body_lines.append("visible = false")
            _emit_ui_widget(body_lines, ext_id, ntype, ui_kind, ui_info, tex_guid_to_path, name, warnings)
            stats["nodes"] += 1
            body_lines.append("")
            continue
        body_lines.append("transform = Transform3D(%s)" % ", ".join(
            ("%.5f" % v).rstrip("0").rstrip(".") if abs(v) >= 0.000005 else "0" for v in tr))
        if not go["active"]:
            body_lines.append("visible = false")
        if obj_path:
            body_lines.append('mesh = ExtResource("%s")' % ext_id("ArrayMesh", obj_path))
            rend = _comp_of(go, comps, (23, 137))
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
            rend = _comp_of(go, comps, (23, 137))
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
        sphb = _comp_of(go, comps, 135)
        if sphb:
            r = re.search(r"m_Radius:\s*([-+0-9.eE]+)", sphb)
            body_lines.append("# SphereCollider r=%s: tambah CollisionShape manual" % (
                r.group(1) if r else "?"))
        capb = _comp_of(go, comps, 136)
        if capb:
            r = re.search(r"m_Radius:\s*([-+0-9.eE]+)", capb)
            h = re.search(r"m_Height:\s*([-+0-9.eE]+)", capb)
            body_lines.append("# CapsuleCollider r=%s h=%s: tambah CollisionShape manual" % (
                r.group(1) if r else "?", h.group(1) if h else "?"))
        mcolb = _comp_of(go, comps, 64)
        if mcolb:
            body_lines.append("# MeshCollider: buat ConcavePolygonShape3D manual dari mesh")
        # komponen tak didukung
        for cfid in go["components"]:
            c = comps.get(cfid)
            if c and c["class"] not in (1, 4, 20, 23, 33, 54, 64, 65, 82, 108, 114, 135, 136, 137):
                stats["unsupported"][class_name(c["class"])] = stats["unsupported"].get(
                    class_name(c["class"]), 0) + 1
        if _comp_of(go, comps, 54):
            warnings.append("Rigidbody %s: setel fisika manual" % name)
        body_lines.append("")

    head = ["[gd_scene load_steps=%d format=3]\n" % (len(ext) + 1), ""]
    for (kind, path), eid in sorted(ext.items(), key=lambda kv: int(kv[1])):
        head.append('[ext_resource type="%s" path="%s" id="%s"]' % (kind, path, eid))
    if ext:
        head.append("")
    return "\n".join(head + body_lines), warnings, stats
