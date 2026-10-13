import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from u2g.sceneconv import parse_prefab, build_tscn, unity_to_godot_transform

PREFAB = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &100
GameObject:
  m_Name: Kotak
  m_IsActive: 1
  m_Component:
  - component: {fileID: 200}
  - component: {fileID: 300}
  - component: {fileID: 400}
--- !u!4 &200
Transform:
  m_GameObject: {fileID: 100}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 1, y: 2, z: 3}
  m_LocalScale: {x: 1, y: 1, z: 1}
  m_Children: []
  m_Father: {fileID: 0}
--- !u!33 &300
MeshFilter:
  m_GameObject: {fileID: 100}
  m_Mesh: {fileID: 4300000, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, type: 2}
--- !u!23 &400
MeshRenderer:
  m_GameObject: {fileID: 100}
  m_Materials:
  - {fileID: 2100000, guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, type: 2}
"""


def test_parse_prefab():
    gos, comps = parse_prefab(PREFAB)
    assert gos["100"]["name"] == "Kotak"
    assert gos["100"]["pos"] == (1.0, 2.0, 3.0)
    assert gos["100"]["father"] is None


def test_build_tscn():
    gos, comps = parse_prefab(PREFAB)
    text, warnings, stats = build_tscn(
        gos, comps,
        {"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": "res://models/kotak.obj"},
        {"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb": "res://materials/kotak.tres"},
        {})
    assert stats["nodes"] == 1 and stats["mesh"] == 1
    assert '[node name="Kotak" type="MeshInstance3D"]' in text
    assert "transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -1, 2, 3)" in text
    assert "res://models/kotak.obj" in text
    assert "res://materials/kotak.tres" in text


def test_transform_mirror():
    tr = unity_to_godot_transform((1, 0, 0), (0, 0, 0, 1), (1, 1, 1))
    assert tr[9:] == (-1.0, 0.0, 0.0)


SKIN_PREFAB = PREFAB.replace("--- !u!33 &300\nMeshFilter:", "--- !u!137 &300\nSkinnedMeshRenderer:").replace(
    "  m_Mesh: {fileID: 4300000, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, type: 2}",
    "  m_Mesh: {fileID: 4300000, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, type: 2}\n"
    "  m_Bones: []\n  m_RootBone: {fileID: 0}")


def test_skinned_jadi_mesh_statis():
    gos, comps = parse_prefab(SKIN_PREFAB)
    text, warnings, stats = build_tscn(
        gos, comps,
        {"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": "res://models/kulit.obj"}, {}, {})
    assert 'type="MeshInstance3D"' in text
    assert any("SkinnedMesh" in w for w in warnings)


def test_ordering_cepat():
    import time
    gos, comps = {}, {}
    for i in range(3000):
        fid = str(1000 + i)
        cfid = str(2000 + i)
        gos[fid] = {"name": "N%d" % i, "active": True, "components": [cfid],
                    "pos": (0, 0, 0), "quat": (0, 0, 0, 1), "scale": (1, 1, 1),
                    "father": None}
        comps[cfid] = {"class": 4, "body": ""}
    # 3000 root: pastikan ordering tetap O(n)
    t0 = time.time()
    text, _, stats = build_tscn(gos, comps, {}, {}, {})
    dt = time.time() - t0
    assert stats["nodes"] == 3000
    assert dt < 10, "terlalu lambat: %.1fs" % dt


def test_missing_refs_warn():
    gos, comps = parse_prefab(PREFAB)
    _, warnings, _ = build_tscn(gos, comps, {}, {}, {})
    assert any("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in w for w in warnings)
    assert any("material dilewati" in w for w in warnings)


UI_PREFAB = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &10
GameObject:
  m_Name: Kanvas
  m_IsActive: 1
  m_Component:
  - component: {fileID: 20}
  - component: {fileID: 30}
--- !u!4 &20
Transform:
  m_GameObject: {fileID: 10}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 0, y: 0, z: 0}
  m_LocalScale: {x: 1, y: 1, z: 1}
  m_Children:
  - {fileID: 31}
  m_Father: {fileID: 0}
--- !u!223 &30
Canvas:
  m_GameObject: {fileID: 10}
  m_RenderMode: 0
--- !u!1 &11
GameObject:
  m_Name: Judul
  m_IsActive: 1
  m_Component:
  - component: {fileID: 21}
  - component: {fileID: 41}
--- !u!224 &21
RectTransform:
  m_GameObject: {fileID: 11}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 0, y: 0, z: 0}
  m_LocalScale: {x: 1, y: 1, z: 1}
  m_Children: []
  m_Father: {fileID: 20}
  m_AnchorMin: {x: 0.5, y: 0.5}
  m_AnchorMax: {x: 0.5, y: 0.5}
  m_AnchoredPosition: {x: 0, y: 100}
  m_SizeDelta: {x: 400, y: 60}
  m_Pivot: {x: 0.5, y: 0.5}
--- !u!114 &41
MonoBehaviour:
  m_GameObject: {fileID: 11}
  m_Text: Halo Dunia
  m_FontSize: 32
  m_Color: {r: 1, g: 1, b: 1, a: 1}
  m_Alignment: 4
"""


def test_ui_canvas_label():
    from u2g.sceneconv import rect_to_control
    gos, comps = parse_prefab(UI_PREFAB)
    assert gos["11"].get("is_rect") is True
    text, warnings, stats = build_tscn(gos, comps, {}, {}, {})
    assert stats.get("canvas") == 1
    assert stats.get("ui") == 1
    assert '[node name="Kanvas" type="CanvasLayer"]' in text
    assert '[node name="Judul" type="Label" parent="Kanvas"]' in text
    assert "text = " in text and "Halo Dunia" in text
    assert "anchor_left = 0.5000" in text
    assert "anchor_top = 0.5000" in text
    # offset_top = -(100 + 0.5*60) = -130 ; offset_bottom = -(100 - 30) = -70
    assert "offset_top = -130.0000" in text
    assert "offset_bottom = -70.0000" in text
    cp = rect_to_control({"amin": (0, 0), "amax": (1, 1), "apos": (0, 0),
                          "size": (100, 50), "pivot": (0.5, 0.5)})
    assert cp["anchor_top"] == 0.0 and cp["anchor_bottom"] == 1.0
    assert cp["offset_left"] == -50.0 and cp["offset_right"] == 50.0


def test_root_tanpa_parent():
    from u2g.sceneconv import parse_prefab, build_tscn
    from tests.test_sceneconv import PREFAB
    gos, comps = parse_prefab(PREFAB)
    text, _, _ = build_tscn(gos, comps, {}, {}, {})
    first = [l for l in text.splitlines() if l.startswith("[node ")][0]
    assert "parent=" not in first
