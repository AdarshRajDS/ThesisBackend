#!/usr/bin/env python3
"""Regenerate §10 and §11 in evaluationThesis.md from eval JSON files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CLOUD_NOTE = """**Run date:** June 2026 (formative)  
**LLM at run time:** cloud Groq (historical)  
**Endpoint:** `POST /rag/ask`  
**Status:** Exploratory — compare with §11 local LM Studio run"""

LOCAL_NOTE = """**Run date:** 12 July 2026 (900 s retry completed)  
**LLM provider:** LM Studio (`LLM_PROVIDER=lmstudio`, local-only enforced)  
**API base:** http://127.0.0.1:1234/v1  
**Configured model:** `google/gemma-4-e2b`  
**Models loaded (observed):** `qwen3.5-9b-deepseek-v4-flash`, `biomistral-7b`  
**Endpoint:** `POST /rag/ask` with `language=de`  
**Outcome:** 7/9 answered · 1 HTTP 500 (LM-R02) · 1 timeout (LM-R09)  
**Thesis note:** Several answers fall back to general anatomy when retrieval is weak (grounding / consent risk)."""


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
        "--run-note", CLOUD_NOTE,
    )
    run(
        "--json", str(REPO / "german_eval_lmstudio_results.json"),
        "--section-num", "11",
        "--section-title", "Local LM Studio experiment (Q&A)",
        "--id-prefix", "LM-R",
        "--run-note", LOCAL_NOTE,
    )
    fix_mcp_subsections(REPO / "evaluationThesis.md")
    print("Refreshed evaluationThesis.md §10 and §11")


if __name__ == "__main__":
    main()
