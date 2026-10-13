"""Builder: susun project Godot final dari hasil batch 2-4.

Struktur:
  OUT/
    project.godot
    models/ materials/ texture/ audio/ font/ scenes/ scripts/
    migration/{manifest.json, mapping.json, report.json}
    logs/
Tidak mengubah sumber. Idempoten (boleh jalan ulang).
"""
import json
import os
import shutil

PROJECT_GODOT = """config_version=5

[application]

config/name="{name}"
run/main_scene="{main_scene}"
config/features=PackedStringArray("4.3", "GL Compatibility")

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""


def build_project(convert_root, project_name, main_scene=""):
    """convert_root berisi models/ materials/ texture/ audio/ font/ scenes/
    scripts/. Tulis project.godot + migration/. Kembalikan dict hasil."""
    for sub in ("models", "materials", "texture", "audio", "font", "scenes",
                "scripts", "migration", "logs"):
        os.makedirs(os.path.join(convert_root, sub), exist_ok=True)
    with open(os.path.join(convert_root, "project.godot"), "w", encoding="utf-8") as f:
        f.write(PROJECT_GODOT.format(name=project_name, main_scene=main_scene))
    counts = {}
    for sub in ("models", "materials", "texture", "audio", "font", "scenes", "scripts"):
        d = os.path.join(convert_root, sub)
        n = sum(len(fs) for _, _, fs in os.walk(d))
        counts[sub] = n
    mapping = {"project": project_name, "counts": counts,
               "note": "script .gd = TEMPLATE, bukan convert. Shader custom = fallback."}
    with open(os.path.join(convert_root, "migration", "mapping.json"), "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=1, ensure_ascii=False)
    return {"ok": True, "counts": counts}


def copy_manifest(manifest_path, convert_root):
    dst = os.path.join(convert_root, "migration", "manifest.json")
    shutil.copy2(manifest_path, dst)
    return dst
