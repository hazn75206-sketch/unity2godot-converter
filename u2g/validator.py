"""Validator: Godot CLI headless --import + kumpulkan error.

Butuh executable Godot (linux/mac/win). Tanpa Godot -> status skipped.
Validasi impor membuktikan resource termuat, BUKAN gameplay benar.
"""
import json
import os
import re
import subprocess


def find_godot(hint=None):
    if hint and os.path.isfile(hint):
        return hint
    for c in ("godot", "Godot", "godot.exe"):
        for d in os.environ.get("PATH", "").split(os.pathsep):
            p = os.path.join(d, c)
            if os.path.isfile(p):
                return p
    return None


def run_import(godot_bin, project_dir, timeout=1200):
    """Jalankan --headless --import. Kembalikan dict hasil."""
    try:
        r = subprocess.run(
            [godot_bin, "--headless", "--import", "--path", project_dir],
            capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "status": "error", "reason": str(e)[:200]}
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    errors = [l for l in out.splitlines() if "ERROR" in l]
    parse_err = [l for l in errors if "Parse Error" in l or "SCRIPT ERROR" in l]
    return {"ok": r.returncode == 0 and not parse_err,
            "status": "checked",
            "returncode": r.returncode,
            "errors": len(errors), "parse_errors": len(parse_err),
            "sample": errors[:20],
            "log_tail": out[-3000:]}


def validate_project(project_dir, godot_bin=None, out_path=None):
    exe = find_godot(godot_bin)
    if not exe:
        res = {"ok": False, "status": "skipped",
               "reason": "Godot tidak ditemukan (set GODOT_BIN)"}
    else:
        res = run_import(exe, project_dir)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
    return res


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("pakai: validator.py PROJECT_DIR [GODOT_BIN]")
    print(json.dumps(validate_project(
        sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), indent=1)[:1500])
