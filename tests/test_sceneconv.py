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
    assert '[node name="Kotak" type="MeshInstance3D" parent="."]' in text
    assert "transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -1, 2, 3)" in text
    assert "res://models/kotak.obj" in text
    assert "res://materials/kotak.tres" in text


def test_transform_mirror():
    tr = unity_to_godot_transform((1, 0, 0), (0, 0, 0, 1), (1, 1, 1))
    assert tr[9:] == (-1.0, 0.0, 0.0)


def test_missing_refs_warn():
    gos, comps = parse_prefab(PREFAB)
    _, warnings, _ = build_tscn(gos, comps, {}, {}, {})
    assert any("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in w for w in warnings)
    assert any("material dilewati" in w for w in warnings)
