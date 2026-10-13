"""Report: gabung semua ringkasan -> report.json + status jujur.

Status: success | success_with_warnings | partial | failed | cancelled.
Aturan: gagal > 0 dan sukses == 0 -> failed; gagal > 0 -> partial;
warnings > 0 -> success_with_warnings; selain itu success.
"""
import json
import os

NOT_SUPPORTED = [
    "C# game logic (butuh tulis ulang GDScript)",
    "shader custom Unity (fallback StandardMaterial3D)",
    "animasi skeletal runtime (skin jadi mesh statis)",
    "ParticleSystem (node+peringatan, tanpa simulasi)",
    "UI Canvas (modul terpisah, belum)",
    "networking multiplayer (server terpisah)",
    "Terrain digital (catat manual bila ada)",
    "NavMesh (gunakan NavigationRegion3D manual)",
]


def build_report(parts, out_path):
    conv = parts.get("conversion", {})
    mesh, mat = conv.get("mesh", {}), conv.get("material", {})
    scene = parts.get("scene", {})
    scripts = parts.get("scripts", {})
    ok = mesh.get("ok", 0) + mat.get("ok", 0) + scene.get("scenes", 0) + scene.get("prefabs", 0)
    failed = len(mesh.get("failed", {})) + len(mat.get("failed", {})) + len(scene.get("failed", {}))
    warnings = (mat.get("warnings", 0) + scene.get("warnings", 0)
                + sum(1 for _ in scene.get("unsupported", {})))
    if failed > 0 and ok == 0:
        status = "failed"
    elif failed > 0:
        status = "partial"
    elif warnings > 0:
        status = "success_with_warnings"
    else:
        status = "success"
    report = {"status": status,
              "converted_ok": ok, "failed": failed, "warnings": warnings,
              "not_supported": NOT_SUPPORTED,
              "unsupported_components": scene.get("unsupported", {}),
              "script_templates": scripts.get("template", 0),
              "script_failed": len(scripts.get("failed", {})),
              "details": parts}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    return report
