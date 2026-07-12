#!/usr/bin/env python3
"""Rebuild §12 from latest rag_eval_55_results.json (safe to run while batch is in progress)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    script = REPO / "scripts" / "build_eval_section12.py"
    subprocess.check_call([sys.executable, str(script)])


if __name__ == "__main__":
    main()
