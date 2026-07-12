#!/usr/bin/env python3
"""Fix evaluationThesis.md section ordering after build_eval_section insert bug."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MD = REPO / "evaluationThesis.md"


def main() -> None:
    text = MD.read_text(encoding="utf-8")

    # Extract misplaced LM block (### 11. Local ... through last LM-R09 ---)
    lm_match = re.search(
        r"(### 11\. Local LM Studio experiment.*?)(?=\n## Appendix A)",
        text,
        flags=re.DOTALL,
    )
    if not lm_match:
        raise SystemExit("LM block not found")
    lm_body = lm_match.group(1)
    lm_body = lm_body.replace("### 11. Local LM Studio experiment", "## 11. Local LM Studio experiment", 1)
    lm_body = lm_body.replace("### 11.0 Summary", "### 11.0 Summary", 1)

    # Remove misplaced block from text
    text = text[: lm_match.start()] + text[lm_match.end() :]

    # Remove orphan ## 13 MCP header if empty before appendix
    text = re.sub(
        r"## 13\. MCP evaluation workbook \(Q&A templates\)\s*\n\s*\*\*Status:\*\*[^\n]*\nRecord:[^\n]*\n\s*",
        "",
        text,
        count=1,
    )

    # Insert LM section before ## 12. Final RAG
    marker = "## 12. Final RAG evaluation workbook"
    if marker not in text:
        raise SystemExit("Section 12 marker not found")
    text = text.replace(
        f"---\n\n{marker}",
        f"---\n\n{lm_body.rstrip()}\n\n---\n\n{marker}",
        1,
    )

    # Restore MCP + reproduce from last git commit if missing
    if "## 13. MCP evaluation workbook" not in text:
        git_md = subprocess.check_output(
            ["git", "show", "HEAD:evaluationThesis.md"],
            cwd=REPO,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        mcp = re.search(
            r"(## 11\. MCP evaluation workbook.*?)(?=\n## 12\. How to reproduce)",
            git_md,
            flags=re.DOTALL,
        )
        repro = re.search(
            r"(## 12\. How to reproduce.*?)(?=\n## Appendix A)",
            git_md,
            flags=re.DOTALL,
        )
        if not mcp or not repro:
            raise SystemExit("Could not extract MCP/reproduce from git")
        mcp_text = mcp.group(1).replace("## 11. MCP", "## 13. MCP", 1)
        repro_text = repro.group(1).replace("## 12. How to reproduce", "## 14. How to reproduce", 1)
        repro_text = repro_text.replace("§10 + §2", "§12 + §2").replace("§11 + §3", "§13 + §3")
        insert_at = text.find("\n## Appendix A")
        text = text[:insert_at] + "\n\n" + mcp_text.rstrip() + "\n\n---\n\n" + repro_text.rstrip() + text[insert_at:]

    MD.write_text(text, encoding="utf-8")
    print(f"Fixed structure in {MD}")


if __name__ == "__main__":
    main()
