# Unity to Godot Universal Converter (core CLI)

Pipeline modular Unity -> Godot. GUI desktop (PySide6) = roadmap, bukan sekarang.

## Struktur

- `u2g/scanner.py` — scan project Unity -> manifest JSON (read-only)
- `u2g/guidmap.py` — peta GUID dari file .meta
- `u2g/meshconv.py` — (batch 2) mesh Unity -> OBJ
- `u2g/matconv.py` — (batch 2) material -> .tres
- `u2g/sceneconv.py` — (batch 3) prefab/scene -> .tscn
- `u2g/scriptscan.py` — (batch 4) analisis C# + template
- `u2g/builder.py`, `u2g/validator.py`, `u2g/report.py` — (batch 4-5)

## Pakai

```
python3 -m u2g.scanner /path/ke/ExportedProject manifest.json
```

## Batas jujur

- Script C# / shader custom: analisis + template saja, tidak auto-convert
- UI Canvas Unity: belum didukung
- Butuh Python 3.8+ saja (tanpa dependensi pihak ketiga untuk batch 1)
