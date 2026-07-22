"""Render TikZ figure sources to figures/rendered/*.pdf for the free-plan Overleaf build."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
RENDERED = FIGURES / "rendered"

PREAMBLE = r"""
\documentclass[tikz,border=2pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric,fit,calc}
\definecolor{RAGBlue}{HTML}{2563EB}
\definecolor{RAGBlueLight}{HTML}{EAF2FF}
\definecolor{MCPGreen}{HTML}{059669}
\definecolor{MCPGreenLight}{HTML}{EAF8F2}
\definecolor{WarningOrange}{HTML}{B45309}
\newcommand{\codepath}[1]{\texttt{\detokenize{#1}}}
\begin{document}
"""

FOOTER = r"""
\end{document}
"""

TARGETS = [
    "dual_pipeline_architecture",
    "rag_pipeline",
    "final_runtime_architecture",
    "rag_runtime_sequence",
]


def render(name: str) -> None:
    src = FIGURES / f"{name}.tex"
    body = src.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tex = tmp_path / f"{name}.tex"
        tex.write_text(PREAMBLE + body + FOOTER, encoding="utf-8")
        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex.name,
        ]
        proc = subprocess.run(
            cmd,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            print(proc.stdout[-4000:])
            print(proc.stderr[-2000:])
            raise SystemExit(f"Failed to render {name}")
        out_pdf = tmp_path / f"{name}.pdf"
        dest = RENDERED / f"{name}.pdf"
        dest.write_bytes(out_pdf.read_bytes())
        print(f"Wrote {dest}")


def main() -> None:
    RENDERED.mkdir(parents=True, exist_ok=True)
    for name in TARGETS:
        render(name)


if __name__ == "__main__":
    main()
