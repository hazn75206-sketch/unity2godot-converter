"""Analisis C# Unity -> laporan + template GDScript (BUKAN auto-convert).

Status per file: analyzed-template (selalu template, tak pernah klaim convert).
Mendeteksi: MonoBehaviour, event Unity, API rawan (Input/fisika/UI/coroutine).
"""
import os
import re

UNITY_EVENTS = ("Awake", "Start", "Update", "FixedUpdate", "LateUpdate",
                "OnEnable", "OnDisable", "OnDestroy", "OnCollisionEnter",
                "OnCollisionStay", "OnCollisionExit", "OnTriggerEnter",
                "OnTriggerStay", "OnTriggerExit", "OnAnimatorMove")

API_FLAGS = {
    "Input.": "API Input (petakan ke Input Godot manual)",
    "GetComponent": "GetComponent (cek path node Godot)",
    "Rigidbody": "API fisika (sesuaikan RigidBody/CharacterBody)",
    "CharacterController": "CharacterController (tidak ada padanan langsung)",
    "NavMeshAgent": "NavMeshAgent (gunakan NavigationAgent3D)",
    "Animator": "Animator (gunakan AnimationPlayer/Tree)",
    "Photon": "Networking Photon (server terpisah)",
    "Mirror": "Networking Mirror (server terpisah)",
    "IEnumerator": "Coroutine (gunakan await/tween)",
    "UnityEvent": "UnityEvent (gunakan signal)",
    "ScriptableObject": "ScriptableObject (gunakan Resource)",
    "DontDestroyOnLoad": "DontDestroyOnLoad (gunakan autoload)",
    "Instantiate": "Instantiate (gunakan PackedScene.instance)",
    "Resources.Load": "Resources.Load (preload path Godot)",
    "PlayerPrefs": "PlayerPrefs (gunakan ConfigFile)",
    "Canvas": "UI Canvas (modul UI terpisah)",
    "Raycast": "Raycast (gunakan raycast Godot)",
}

EVENT_TO_GD = {"Awake": "_ready()", "Start": "_ready()",
               "Update": "_process(delta)", "FixedUpdate": "_physics_process(delta)",
               "LateUpdate": "_process(delta)",
               "OnEnable": "_enter_tree()", "OnDisable": "_exit_tree()"}


def analyze_cs(path):
    """Kembalikan dict analisis. Tak pernah throw (file rusak -> status failed)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            t = f.read()
    except OSError as e:
        return {"ok": False, "status": "failed", "reason": str(e)[:120]}
    classes = re.findall(r"\bclass\s+(\w+)", t)
    is_behaviour = "MonoBehaviour" in t
    events = [e for e in UNITY_EVENTS if re.search(r"\b%s\s*\(" % e, t)]
    flags = sorted({v for k, v in API_FLAGS.items() if k in t})
    return {"ok": True, "status": "template", "classes": classes,
            "is_behaviour": is_behaviour, "events": events, "flags": flags}


def template_gd(analysis, source_name):
    """Template GDScript jujur: kerangka + TODO, bukan hasil convert."""
    L = ["# TEMPLATE migrasi dari %s (ditulis manual!)\n" % source_name,
         "# Status: template generated — logika asli TIDAK ikut.\n",
         "extends Node\n\n"]
    for cls in analysis.get("classes", [])[:3]:
        L.append("# class Unity: %s\n" % cls)
    mapped = []
    for e in analysis.get("events", []):
        if e in EVENT_TO_GD and EVENT_TO_GD[e] not in mapped:
            mapped.append(EVENT_TO_GD[e])
            L.append("func %s:\n\tpass # TODO: port dari %s()\n\n" % (EVENT_TO_GD[e], e))
    for f in analysis.get("flags", []):
        L.append("# TODO: %s\n" % f)
    return "".join(L)


def scan_scripts(manifest, src_root, out_scripts):
    """Semua .cs di manifest -> analisis + template. Kembalikan ringkasan."""
    os.makedirs(out_scripts, exist_ok=True)
    summary = {"total": 0, "template": 0, "failed": {}, "api_flags": {}}
    for f in manifest.get("files", []):
        if f["category"] != "script" or not f["path"].endswith(".cs"):
            continue
        summary["total"] += 1
        a = analyze_cs(os.path.join(src_root, f["path"]))
        if not a["ok"]:
            summary["failed"][f["path"]] = a["reason"]
            continue
        summary["template"] += 1
        for fl in a["flags"]:
            summary["api_flags"][fl] = summary["api_flags"].get(fl, 0) + 1
        base = os.path.splitext(os.path.basename(f["path"]))[0]
        stem = re.sub(r"[^\w\- ]+", "_", base).strip() or "script"
        with open(os.path.join(out_scripts, stem + ".gd"), "w", encoding="utf-8") as fh:
            fh.write(template_gd(a, f["path"]))
    return summary
