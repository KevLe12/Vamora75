"""Write MANIFEST.json: every delivered file with size, SHA-256 and the folder's role.

    python Source/make_manifest.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = {
    "PCB": "KiCad 10 project (schematic, board, library, 3D models)",
    "Plate": "KiCad boards for ordering the FR4 plate",
    "Mechanical": "case, plate, soft parts, assemblies (STEP/STL/DXF)",
    "Manufacturing": "fabrication and assembly outputs (Gerbers, BOM, CPL, PDFs)",
    "Firmware": "QMK + VIA, CircuitPython, layout files",
    "Artwork": "brand mark files",
    "Previews": "renders",
    "Source": "generators (rebuild everything with build_all.py)",
    "validation": "ERC / DRC / mechanical / firmware reports",
    "Licenses": "third-party licences",
    "Reference": "input snapshots supplied with the project",
    "Archive": "previous revisions, unchanged",
}
SKIP = {".history", "__pycache__"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    files = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if not p.is_file() or SKIP & set(rel.parts) or rel.name == "MANIFEST.json":
            continue
        files.append({"path": rel.as_posix(), "bytes": p.stat().st_size, "sha256": sha(p),
                      "role": ROLES.get(rel.parts[0], "documentation") if len(rel.parts) > 1 else "documentation"})
    m = {"project": "Vamora75", "revision": "1.1", "generated": datetime.date.today().isoformat(),
         "folders": ROLES, "file_count": len(files), "total_bytes": sum(f["bytes"] for f in files), "files": files}
    (ROOT / "MANIFEST.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("MANIFEST.json:", len(files), "files,", round(m["total_bytes"] / 1e6, 1), "MB")
