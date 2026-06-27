#!/usr/bin/env python3
"""
Run many questions against the API concurrently (bounded parallelism).

Examples:
  # Thesis experiment pipeline (baseline + strict + coherent + judge)
  python scripts/run_thesis_batch.py --questions-file scripts/thesis_questions_sample.txt

  # Production RAG only
  python scripts/run_thesis_batch.py --endpoint rag --questions-file scripts/thesis_questions_sample.txt

  # Limit parallel in-flight requests (Groq + local models are heavy)
  python scripts/run_thesis_batch.py --concurrency 3

Default base URL: http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

DEFAULT_QUESTIONS = [
    "What is the difference between the upper motor neuron and the lower motor neuron?",
    "Where is the cell body of the upper motor neuron located?",
    "What is gray matter versus white matter in the CNS?",
    "What is the role of the cerebellum in motor control?",
    "What structures make up the brainstem?",
    "Tell me about the brain.",
    "What is the capital of France?",
]


async def _post_one(
    client: httpx.AsyncClient,
    base: str,
    endpoint: str,
    question: str,
    persist_log: bool,
    sem: asyncio.Semaphore,
    idx: int,
) -> dict:
    path = "/rag/ask" if endpoint == "rag" else "/rag/experiment/ask"
    payload = {"question": question}
    if endpoint != "rag":
        payload["persist_log"] = persist_log

    async with sem:
        r = await client.post(f"{base.rstrip('/')}{path}", json=payload, timeout=600.0)
        try:
            body = r.json()
        except Exception:
            body = {"_raw": r.text}
        return {
            "index": idx,
            "question": question,
            "status_code": r.status_code,
            "body": body,
        }


async def main_async() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    ap.add_argument(
        "--endpoint",
        choices=("experiment", "rag"),
        default="experiment",
        help="experiment = POST /rag/experiment/ask; rag = POST /rag/ask",
    )
    ap.add_argument("--concurrency", type=int, default=4, help="Max parallel HTTP requests")
    ap.add_argument(
        "--questions-file",
        type=Path,
        help="One question per line (empty lines and # comments skipped)",
    )
    ap.add_argument(
        "--persist-log",
        action="store_true",
        help="For experiment endpoint: append each run to thesis_rag_eval.jsonl",
    )
    ap.add_argument(
        "--output",
        type=Path,
        help="Write JSON lines results here (default: stdout)",
    )
    args = ap.parse_args()

    if args.questions_file:
        text = args.questions_file.read_text(encoding="utf-8")
        questions = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            questions.append(line)
    else:
        questions = DEFAULT_QUESTIONS

    if not questions:
        print("No questions to run.", file=sys.stderr)
        return 1

    sem = asyncio.Semaphore(max(1, args.concurrency))
    results: list[dict] = []

    async with httpx.AsyncClient() as client:
        tasks = [
            _post_one(
                client,
                args.base_url,
                args.endpoint,
                q,
                args.persist_log,
                sem,
                i,
            )
            for i, q in enumerate(questions)
        ]
        for coro in asyncio.as_completed(tasks):
            results.append(await coro)

    results.sort(key=lambda x: x["index"])
    out_obj = {
        "meta": {
            "ts": datetime.now(timezone.utc).isoformat(),
            "base_url": args.base_url,
            "endpoint": args.endpoint,
            "concurrency": args.concurrency,
            "count": len(results),
        },
        "results": results,
    }

    line = json.dumps(out_obj, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(line, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(line)

    failed = sum(1 for r in results if r["status_code"] != 200)
    return 1 if failed else 0


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
