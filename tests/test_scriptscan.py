import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from u2g.scriptscan import analyze_cs, template_gd

CS = """
using UnityEngine;
public class Lompat : MonoBehaviour {
    public float kuat = 5f;
    void Start() { rb = GetComponent<Rigidbody>(); }
    void Update() {
        if (Input.GetKeyDown(KeyCode.Space)) { rb.AddForce(Vector3.up * kuat); }
        StartCoroutine(Tunggu());
    }
    System.Collections.IEnumerator Tunggu() { yield return null; }
}
"""


def test_analyze(tmp_path):
    p = tmp_path / "Lompat.cs"
    p.write_text(CS)
    a = analyze_cs(str(p))
    assert a["ok"] and a["status"] == "template"
    assert "Lompat" in a["classes"] and a["is_behaviour"]
    assert "Start" in a["events"] and "Update" in a["events"]
    assert any("Input" in f for f in a["flags"])
    assert any("Coroutine" in f for f in a["flags"])


def test_template_jujur(tmp_path):
    p = tmp_path / "Lompat.cs"
    p.write_text(CS)
    a = analyze_cs(str(p))
    t = template_gd(a, "Lompat.cs")
    assert "TEMPLATE" in t and "func _process():" in t and "func _ready():" in t
    assert "TODO" in t


def test_file_hilang(tmp_path):
    a = analyze_cs(str(tmp_path / "x.cs"))
    assert a["status"] == "failed"
