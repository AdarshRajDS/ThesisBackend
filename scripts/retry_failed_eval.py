#!/usr/bin/env python3
"""Retry failed rows in an eval JSON file (merge back in place)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from run_german_eval import ask

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else REPO / "german_eval_lmstudio_results.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for i, row in enumerate(rows, 1):
        if not row.get("error"):
            continue
        q = row["question"]
        print(f"[retry {i}/{len(rows)}] {q[:60]}...", flush=True)
        try:
            data = ask(q)
            row["response"] = data
            row["error"] = None
            changed += 1
        except Exception as exc:
            row["error"] = str(exc)
            print(f"  still failed: {exc}", flush=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {path} — {changed} rows recovered")


if __name__ == "__main__":
    main()
