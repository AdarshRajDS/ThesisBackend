#!/usr/bin/env python3
"""Regenerate §10 and §11 in evaluationThesis.md from eval JSON files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CLOUD_NOTE = """**Run date:** June 2026 (formative)  
**Status:** Exploratory — compare with §11 local LM Studio run"""

LOCAL_NOTE = """**Run date:** 12 July 2026  
**Model:** `qwen3.5-9b-deepseek-v4-flash` (Qwen DeepSeek Flash via LM Studio)  
**Outcome:** 7/9 answered · 1 HTTP 500 (LM-R02) · 1 timeout (LM-R09)  
**Thesis note:** Primary professor run — same model as §12 English batch. Several answers fall back to general anatomy when retrieval is weak."""


def run(*args: str) -> None:
    cmd = [sys.executable, str(REPO / "scripts" / "build_eval_section.py"), *args]
    subprocess.check_call(cmd, cwd=REPO)


def fix_mcp_subsections(md: Path) -> None:
    text = md.read_text(encoding="utf-8")
    start = text.find("## 13. MCP evaluation workbook")
    if start == -1:
        return
    head, tail = text[:start], text[start:]
    tail = tail.replace("### 11.", "### 13.")
    md.write_text(head + tail, encoding="utf-8")


def main() -> None:
    run(
        "--json", str(REPO / "german_eval_results.json"),
        "--section-num", "10",
        "--section-title", "Exploratory RAG results — cloud run (Q&A)",
        "--id-prefix", "EXP-R",
        "--run-key", "cloud_professor_de",
        "--run-note", CLOUD_NOTE,
    )
    run(
        "--json", str(REPO / "german_eval_lmstudio_results.json"),
        "--section-num", "11",
        "--section-title", "Local LM Studio experiment (Q&A)",
        "--id-prefix", "LM-R",
        "--run-key", "local_professor_de",
        "--run-note", LOCAL_NOTE,
    )
    fix_mcp_subsections(REPO / "evaluationThesis.md")
    subprocess.check_call(
        [sys.executable, str(REPO / "scripts" / "build_professor_metrics_workbook.py")],
        cwd=REPO,
    )
    subprocess.check_call(
        [sys.executable, str(REPO / "scripts" / "build_thesis_dashboard.py")],
        cwd=REPO,
    )
    _update_toc(REPO / "evaluationThesis.md")
    print("Refreshed evaluationThesis.md §9.0–§9.2, §10, and §11")


def _update_toc(md: Path) -> None:
    text = md.read_text(encoding="utf-8")
    old = """   - [9.1 Professor metrics workbook](#91-professor-evaluation-metrics-workbook)
10. [Exploratory RAG results — cloud run (Q&A)](#10-exploratory-rag-results--cloud-run-qa)
11. [Local LM Studio experiment (Q&A)](#11-local-lm-studio-experiment-qa)
12. [Final RAG evaluation workbook (Q&A templates)](#12-final-rag-evaluation-workbook-qa-templates)"""
    new = """   - [9.1 Professor metrics workbook](#91-professor-evaluation-metrics-workbook)
   - [9.2 Thesis results dashboard (12 Jul 2026)](#92-thesis-primary-run--results-dashboard-12-july-2026)
10. [Exploratory RAG results — cloud run (Q&A)](#10-exploratory-rag-results--cloud-run-qa)
11. [Local LM Studio experiment (Q&A)](#11-local-lm-studio-experiment-qa)
12. [Final RAG evaluation workbook (Q&A)](#12-final-rag-evaluation-workbook-qa)"""
    if old in text:
        text = text.replace(old, new)
    md.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
