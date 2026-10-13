"""Material Unity (.mat YAML) -> StandardMaterial3D (.tres Godot).

Hanya shader Standard/legacy yang dipetakan; shader custom dicatat
dan difallback ke standar. Texture di-resolve via peta GUID.
Tidak menebak: properti tak dikenal -> warning, bukan nilai karangan.
"""
import os
import re


def _ref_guid(entry):
    m = re.search(r"guid:\s*([0-9a-fA-F]{32})", entry)
    return m.group(1).lower() if m else None


def parse_mat(path):
    """Kembalikan dict material + warnings. Tidak throw untuk file rusak
    ringan (kembalikan ok=False + alasan)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            t = f.read()
    except OSError as e:
        return {"ok": False, "reason": str(e)[:120], "warnings": []}
    if "Material:" not in t:
        return {"ok": False, "reason": "bukan file Material", "warnings": []}
    warnings = []
    name_m = re.search(r"m_Name:\s*(.+)", t)
    name = name_m.group(1).strip() if name_m else os.path.basename(path)
    sm = re.search(r"m_Shader:\s*\{([^}]*)\}", t)
    shader_guid = _ref_guid(sm.group(1)) if sm else None
    floats = dict(re.findall(r"^\s+(_\w+):\s*([-+0-9.eE]+)\s*$", t, re.M))
    colors = {}
    for cm in re.finditer(r"(_\w+):\s*\{r:\s*([-+0-9.eE]+),\s*g:\s*([-+0-9.eE]+),\s*b:\s*([-+0-9.eE]+),\s*a:\s*([-+0-9.eE]+)\}", t):
        colors[cm.group(1)] = tuple(float(cm.group(i)) for i in range(2, 6))
    texenvs = {}
    for tm in re.finditer(r"(_\w+):\s*\n\s*m_Texture:\s*\{([^}]*)\}\s*\n\s*m_Scale:\s*\{x:\s*([-+0-9.eE]+),\s*y:\s*([-+0-9.eE]+)\}\s*\n\s*m_Offset:\s*\{x:\s*([-+0-9.eE]+),\s*y:\s*([-+0-9.eE]+)\}", t):
        texenvs[tm.group(1)] = {"guid": _ref_guid(tm.group(2)),
                                 "scale": (float(tm.group(3)), float(tm.group(4))),
                                 "offset": (float(tm.group(5)), float(tm.group(6)))}
    return {"ok": True, "name": name, "shader_guid": shader_guid,
            "floats": floats, "colors": colors, "texenvs": texenvs,
            "warnings": warnings}


def _f(d, key, default=0.0):
    try:
        return float(d.get(key, default))
    except (TypeError, ValueError):
        return default


def to_tres(mat, guid_to_texpath):
    """Dict material -> (teks .tres, warnings). guid_to_texpath: {guid: path res://}."""
    warnings = list(mat.get("warnings", []))
    f = mat["floats"]
    c = mat["colors"]
    albedo = c.get("_Color", (1, 1, 1, 1))
    emission = c.get("_EmissionColor", (0, 0, 0, 1))
    metallic = _f(f, "_Metallic")
    gloss = _f(f, "_Glossiness", 0.5)
    mode = int(_f(f, "_Mode"))
    cutoff = _f(f, "_Cutoff", 0.5)
    maintex = mat["texenvs"].get("_MainTex", {})
    tex_guid = (maintex.get("guid") or "").lower()
    texpath = guid_to_texpath.get(tex_guid) if tex_guid else None
    if tex_guid and not texpath:
        warnings.append("tekstur _MainTex guid %s tak ketemu" % tex_guid)
    L = ['[gd_resource type="StandardMaterial3D" format=3]\n', "\n"]
    if texpath:
        L.append('[ext_resource type="Texture2D" path="%s" id="1"]\n' % texpath)
        L.append("\n")
    L.append("[resource]\n")
    L.append("albedo_color = Color(%.4f, %.4f, %.4f, %.4f)\n" % albedo)
    if texpath:
        L.append('albedo_texture = ExtResource("1")\n')
    L.append("metallic = %.4f\n" % metallic)
    L.append("roughness = %.4f\n" % max(0.0, min(1.0, 1.0 - gloss)))
    if any(v > 0.001 for v in emission[:3]):
        L.append("emission_enabled = true\n")
        L.append("emission = Color(%.4f, %.4f, %.4f, 1)\n" % emission[:3])
    if mode == 1:
        L.append("transparency = 1\n")
        L.append("alpha_scissor_threshold = %.4f\n" % cutoff)
    elif mode in (2, 3):
        L.append("transparency = 1\n")
        warnings.append("blend mode fade/transparent disederhanakan jadi alpha scissor")
    return "".join(L), warnings


def convert_mat_file(src, dst, guid_to_texpath):
    mat = parse_mat(src)
    if not mat["ok"]:
        return {"ok": False, "reason": mat["reason"], "warnings": []}
    try:
        text, warnings = to_tres(mat, guid_to_texpath)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        return {"ok": True, "name": mat["name"], "warnings": warnings}
    except OSError as e:
        return {"ok": False, "reason": str(e)[:120], "warnings": []}
