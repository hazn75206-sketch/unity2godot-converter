import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from u2g.meshconv import parse_mesh, to_obj

TRI_YAML = """%YAML 1.1
--- !u!43 &4300000
Mesh:
  m_VertexCount: 3
  m_Vertices: []
  m_Channels:
  - stream: 0
    offset: 0
    format: 0
    dimension: 3
  m_DataSize: 36
  m_IndexFormat: 0
  m_IndexBuffer: 000001000200
  m_SubMeshes:
  - firstByte: 0
    indexCount: 3
    topology: 0
    baseVertex: 0
    firstVertex: 0
  _typelessdata: {verts}
"""


def _tri_asset(tmp_path):
    verts = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0).hex()
    p = tmp_path / "tri.asset"
    p.write_text(TRI_YAML.format(verts=verts))
    return str(p)


def test_parse_triangle(tmp_path):
    mesh, err = parse_mesh(_tri_asset(tmp_path))
    assert err is None
    assert mesh["nv"] == 3
    assert mesh["pos"][0] == (0.0, 0.0, 0.0)
    assert mesh["pos"][1] == (-1.0, 0.0, 0.0)  # X dinegasi


def test_to_obj_valid(tmp_path):
    mesh, _ = parse_mesh(_tri_asset(tmp_path))
    text, skipped = to_obj(mesh, "tri")
    assert skipped == 0
    lines = text.splitlines()
    assert sum(1 for l in lines if l.startswith("v ")) == 3
    assert sum(1 for l in lines if l.startswith("f ")) == 1
    # indeks 1-based dan dalam batas
    for l in lines:
        if l.startswith("f "):
            for v in l.split()[1:]:
                assert 1 <= int(v.split("/")[0]) <= 3


def test_parse_bukan_mesh(tmp_path):
    p = tmp_path / "x.asset"
    p.write_text("bukan yaml mesh\n")
    mesh, err = parse_mesh(str(p))
    assert mesh is None and err


def test_short_blob_pos_only(tmp_path):
    import struct as st
    blob = st.pack("<6f", 1, 2, 3, 4, 5, 6)  # 2 vertex posisi saja
    yml = TRI_YAML.replace("  m_VertexCount: 3", "  m_VertexCount: 2")
    yml = yml.replace("  m_DataSize: 36", "  m_DataSize: 232")
    # deklarasi stride 116 (ada blok packed fiktif) tapi blob cuma 24 byte
    yml = yml.replace(
        "  - stream: 0\n    offset: 0\n    format: 0\n    dimension: 3\n",
        "  - stream: 0\n    offset: 0\n    format: 0\n    dimension: 3\n"
        "  - stream: 0\n    offset: 12\n    format: 1\n    dimension: 52\n")
    yml = yml.replace("{verts}", blob.hex())
    p = tmp_path / "short.asset"
    p.write_text(yml)
    mesh, err = parse_mesh(str(p))
    assert err is None, err
    assert mesh.get("pos_only") is True
    assert mesh["pos"][0] == (-1.0, 2.0, 3.0)
    text, _ = to_obj(mesh, "short")
    assert "vn " in text  # normal dihitung


def test_multistream_uv(tmp_path):
    import struct as st
    # stream0: posisi 3 float (stride 12), stream1: uv 2 float (stride 8)
    blob = st.pack("<6f", 0, 0, 0, 2, 0, 0) + st.pack("<4f", 0, 0, 1, 1)
    yml = TRI_YAML.replace(
        "  m_Channels:\n  - stream: 0\n    offset: 0\n    format: 0\n    dimension: 3\n",
        "  m_Channels:\n  - stream: 0\n    offset: 0\n    format: 0\n    dimension: 3\n"
        "  - stream: 0\n    offset: 0\n    format: 0\n    dimension: 0\n"
        "  - stream: 0\n    offset: 0\n    format: 0\n    dimension: 0\n"
        "  - stream: 0\n    offset: 0\n    format: 0\n    dimension: 0\n"
        "  - stream: 1\n    offset: 0\n    format: 0\n    dimension: 2\n")
    yml = yml.replace("  m_VertexCount: 3", "  m_VertexCount: 2")
    yml = yml.replace("  m_DataSize: 36", "  m_DataSize: 40")
    yml = yml.replace("{verts}", blob.hex())
    p = tmp_path / "ms.asset"
    p.write_text(yml)
    mesh, err = parse_mesh(str(p))
    assert err is None, err
    assert mesh["nv"] == 2
    assert mesh["uv"][1] == (1.0, 1.0)
    text, skipped = to_obj(mesh, "ms")
    assert "vt " in text
