#!/usr/bin/env python3
"""Refresh the one-pass Overleaf cache after compiling main_full.tex locally.

Run from the project root after a successful normal multi-pass build:
    pdflatex main_full.tex
    bibtex main_full
    pdflatex main_full.tex
    pdflatex main_full.tex
    python3 scripts/refresh_fast_cache.py

If the full build job name is main_full, this script reads main_full.* and
chapter/appendix aux files, then updates cache/*.tex and references_manual.tex.
"""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
job = "main_full"
main_aux = root / f"{job}.aux"
if not main_aux.exists():
    raise SystemExit("Compile main_full.tex first; main_full.aux was not found.")

lines = []
for p in [main_aux, *sorted((root / "chapters").glob("*.aux")), *sorted((root / "appendices").glob("*.aux"))]:
    if not p.exists():
        continue
    for line in p.read_text(errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("\\newlabel") or s.startswith("\\bibcite"):
            lines.append(line)
seen = set()
out = []
for line in lines:
    if line not in seen:
        seen.add(line)
        out.append(line)
cache = root / "cache"
cache.mkdir(exist_ok=True)
(cache / "aux_snapshot.tex").write_text(
    "% Auto-generated label and citation snapshot for the one-pass Overleaf build.\n"
    + "\n".join(out) + "\n"
)
for ext, dst in [("toc", "toc_snapshot.tex"), ("lof", "lof_snapshot.tex"), ("lot", "lot_snapshot.tex")]:
    src = root / f"{job}.{ext}"
    if src.exists():
        shutil.copyfile(src, cache / dst)

bbl = root / f"{job}.bbl"
if bbl.exists():
    shutil.copyfile(bbl, root / "references_manual.tex")

print("Fast-build cache refreshed.")
