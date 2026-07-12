#!/usr/bin/env python3
"""Batch-evaluate the 55-question English RAG set against POST /rag/ask."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = REPO / "eval" / "rag_eval_55.json"
DEFAULT_OUTPUT = REPO / "eval" / "rag_eval_55_results.json"
BASE = "http://127.0.0.1:8000/rag/ask"
DEFAULT_TIMEOUT = int(os.getenv("RAG_EVAL_TIMEOUT", "900"))


def _fmt_elapsed(ms: float | None) -> str:
    if ms is None:
        return "?"
    s = ms / 1000
    if s >= 60:
        return f"{s / 60:.1f} min"
    return f"{s:.1f} s"


def ask(question: str, *, timeout: int = DEFAULT_TIMEOUT) -> dict:
    body = json.dumps(
        {"question": question, "language": "en", "allow_world_knowledge": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        BASE,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_questions(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_existing(path: Path) -> tuple[list[dict], dict[str, dict]]:
    if not path.exists():
        return [], {}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("results", data if isinstance(data, list) else [])
    by_id: dict[str, dict] = {}
    for row in rows:
        qid = row.get("id")
        if qid and row.get("error") is None and row.get("response") and row.get("elapsed_ms") is not None:
            by_id[qid] = row
    return rows, by_id


def save_checkpoint(output_path: Path, results: list[dict]) -> None:
    out_obj = {
        "meta": {
            "ts": datetime.now(timezone.utc).isoformat(),
            "base_url": "http://127.0.0.1:8000",
            "endpoint": "/rag/ask",
            "language": "en",
            "allow_world_knowledge": False,
            "timeout_s": DEFAULT_TIMEOUT,
            "count": len(results),
        },
        "results": results,
    }
    output_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    questions_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_QUESTIONS
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    items = load_questions(questions_path)
    existing_rows, done = load_existing(output_path)
    by_id = {r["id"]: r for r in existing_rows if r.get("id")}
    results: list[dict] = []

    for i, item in enumerate(items, 1):
        qid = item["id"]
        question = item["question"]
        if qid in done:
            print(f"[{i}/{len(items)}] {qid} skip (already OK)", flush=True)
            results.append(done[qid])
            continue

        print(f"[{i}/{len(items)}] {qid} {question[:70]}...", flush=True)
        row = {
            "id": qid,
            "category": item.get("category"),
            "question": question,
            "gold": item.get("gold"),
            "response": None,
            "error": None,
            "elapsed_ms": None,
        }
        started = time.perf_counter()
        try:
            row["response"] = ask(question)
        except Exception as exc:
            row["error"] = str(exc)
        finally:
            row["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        print(f"    done in {_fmt_elapsed(row['elapsed_ms'])}", flush=True)
        results.append(row)
        save_checkpoint(output_path, results)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
