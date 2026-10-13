import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from u2g.matconv import parse_mat, to_tres

MAT = """%YAML 1.1
--- !u!21 &2100000
Material:
  m_Name: Kotak
  m_Shader: {fileID: 4800000, guid: edac787a5024aa84db92b5bbb22b20ab, type: 3}
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
      _MainTex:
        m_Texture: {fileID: 2800000, guid: 91d6d2bc92639284dbb9dbd4b4c2b04d, type: 3}
        m_Scale: {x: 1, y: 1}
        m_Offset: {x: 0, y: 0}
    m_Floats:
      _Metallic: 0.5
      _Glossiness: 0.8
      _Mode: 0
    m_Colors:
      _Color: {r: 1, g: 0.5, b: 0.25, a: 1}
      _EmissionColor: {r: 0, g: 0, b: 0, a: 1}
"""


def test_parse_mat(tmp_path):
    p = tmp_path / "k.mat"
    p.write_text(MAT)
    m = parse_mat(str(p))
    assert m["ok"] and m["name"] == "Kotak"
    assert m["floats"]["_Metallic"] == "0.5"
    assert m["colors"]["_Color"] == (1.0, 0.5, 0.25, 1.0)
    assert m["texenvs"]["_MainTex"]["guid"] == "91d6d2bc92639284dbb9dbd4b4c2b04d"


def test_to_tres_mapping(tmp_path):
    p = tmp_path / "k.mat"
    p.write_text(MAT)
    m = parse_mat(str(p))
    text, warnings = to_tres(m, {"91d6d2bc92639284dbb9dbd4b4c2b04d": "res://texture/kotak.png"})
    assert 'albedo_color = Color(1.0000, 0.5000, 0.2500, 1.0000)' in text
    assert "metallic = 0.5000" in text
    assert "roughness = 0.2000" in text
    assert 'ExtResource("1")' in text and "res://texture/kotak.png" in text


def test_to_tres_tanpa_tekstur(tmp_path):
    p = tmp_path / "k.mat"
    p.write_text(MAT)
    m = parse_mat(str(p))
    text, warnings = to_tres(m, {})
    assert "albedo_texture" not in text
    assert any("91d6d2bc" in w for w in warnings)


def test_parse_bukan_material(tmp_path):
    p = tmp_path / "x.mat"
    p.write_text("hello\n")
    assert parse_mat(str(p))["ok"] is False
