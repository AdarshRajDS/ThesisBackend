#!/usr/bin/env python3
"""Populate §12 English RAG workbook in evaluationThesis.md from batch results."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MD = REPO / "evaluationThesis.md"
DEFAULT_JSON = REPO / "eval" / "rag_eval_55_results.json"
DEFAULT_CATALOG = REPO / "eval" / "rag_eval_55.json"

SECTION12_START = "## 12. Final RAG evaluation workbook"
SECTION13_START = "## 13. MCP evaluation workbook"


def _prefix(id_: str, kind: str) -> bool:
    if kind == "factual":
        return bool(re.match(r"^R-F\d+", id_))
    if kind == "complex":
        return id_.startswith("R-C")
    if kind == "figure":
        return id_.startswith("R-FIG")
    if kind == "quotation":
        return id_.startswith("R-Q")
    if kind == "boundary":
        return id_.startswith("R-B")
    if kind == "robustness":
        return id_.startswith("R-R")
    return False


def _cell(text: str | None, max_len: int = 120) -> str:
    if not text:
        return ""
    t = str(text).replace("\n", " ").replace("|", "\\|").strip()
    if len(t) > max_len:
        return t[: max_len - 1] + "…"
    return t


def _fmt_elapsed_ms(ms: float | None) -> str:
    if ms is None:
        return ""
    s = ms / 1000
    if s >= 60:
        return f"{s / 60:.1f} min"
    if s >= 10:
        return f"{s:.0f} s"
    return f"{s:.1f} s"


def _latency_stats(rows: list[dict]) -> dict[str, float | int]:
    times = [r["elapsed_ms"] for r in rows if r.get("elapsed_ms") is not None]
    if not times:
        return {"count": 0}
    return {
        "count": len(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "avg_ms": sum(times) / len(times),
        "total_ms": sum(times),
    }


def _latency_summary_line(stats: dict[str, float | int]) -> str:
    if not stats.get("count"):
        return "**Request latency:** not recorded for this run (re-run batch to capture per-question timing)"
    return (
        f"**Request latency (wall-clock, {stats['count']} measured):** "
        f"min {_fmt_elapsed_ms(stats['min_ms'])} · "
        f"avg {_fmt_elapsed_ms(stats['avg_ms'])} · "
        f"max {_fmt_elapsed_ms(stats['max_ms'])} · "
        f"total {_fmt_elapsed_ms(stats['total_ms'])}"
    )


def _build_timing_table(rows: list[dict], model_short: str) -> str:
    measured = [r for r in rows if r.get("elapsed_ms") is not None]
    if not measured:
        return ""
    lines = [
        "### 12.0 Per-question request latency",
        "",
        "Wall-clock time for one `POST /rag/ask` call (retrieval + local LM Studio generation).",
        "",
        "| ID | Category | Outcome | Model | Request time |",
        "| -- | -------- | ------- | ----- | ------------ |",
    ]
    for r in measured:
        resp = r.get("response") or {}
        outcome = _outcome(resp.get("answer") if resp else None, r.get("error"))
        lines.append(
            f"| {r['id']} | {r.get('category', '')} | {outcome} | {model_short} | {_fmt_elapsed_ms(r['elapsed_ms'])} |"
        )
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def _outcome(answer: str | None, error: str | None) -> str:
    if error:
        return "Error"
    text = (answer or "").lower()
    abstain_markers = (
        "cannot answer",
        "not found in provided",
        "no relevant information",
        "not in the provided",
        "outside the scope",
        "off-topic",
        "i don't have",
        "i do not have",
        "no information",
        "cannot provide",
        "not covered in",
        "not available in",
    )
    world_knowledge_markers = (
        "general anatomical",
        "general knowledge",
        "world knowledge",
        "based on general",
    )
    if any(m in text for m in world_knowledge_markers):
        return "Answered (world knowledge)"
    if any(m in text for m in abstain_markers):
        return "Abstained"
    return "Answered"


def _format_sources(sources: list[dict] | None) -> str:
    if not sources:
        return "*None*"
    lines = []
    for i, s in enumerate(sources, 1):
        src = s.get("source", "?")
        page = s.get("page", "?")
        preview = (s.get("chunk_preview") or "").strip().replace("\n", " ")
        if len(preview) > 280:
            preview = preview[:280] + "…"
        lines.append(f"{i}. **{src}** p.{page} — {preview}")
    return "\n".join(lines)


def _format_images(images: list | None) -> str:
    if not images:
        return "*None*"
    lines = [f"**Count:** {len(images)}"]
    for i, url in enumerate(images, 1):
        m = re.search(r"/page_(\d+)/", str(url))
        page_hint = f" (page {m.group(1)})" if m else ""
        lines.append(f"{i}. `{url}`{page_hint}")
    return "\n".join(lines)


def _format_grounding(g: dict | None) -> str:
    if not g:
        return "*Not returned*"
    return "\n".join(f"- **{k}:** {v}" for k, v in g.items())


def _detail_block(row: dict, model_short: str = "") -> str:
    qid = row["id"]
    resp = row.get("response") or {}
    err = row.get("error")
    answer = resp.get("answer") if resp else None
    outcome = _outcome(answer, err)

    lines = [
        f"### {qid} — {row['question'][:72]}{'…' if len(row['question']) > 72 else ''}",
        "",
        "| Field | Content |",
        "| ----- | ------- |",
        f"| **ID** | {qid} |",
        f"| **Category** | {row.get('category', '')} |",
        f"| **Outcome** | {outcome} |",
        f"| **Model** | {model_short or 'n/a'} |",
        f"| **Request time** | {_fmt_elapsed_ms(row.get('elapsed_ms')) or 'n/a'} |",
        "",
        "**Question:**  ",
        row["question"],
        "",
        "**Expected key points (gold):**  ",
        row.get("gold") or "",
        "",
        "**System answer:**  ",
    ]
    if err:
        lines.append(f"`{err}`")
    else:
        lines.append(answer or "*empty*")

    if resp:
        lines.extend(
            [
                "",
                "**Sources:**  ",
                _format_sources(resp.get("sources")),
                "",
                "**Images:**  ",
                _format_images(resp.get("images")),
                "",
                "**Grounding metadata:**  ",
                _format_grounding(resp.get("grounding")),
            ]
        )
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def _update_table_row(line: str, by_id: dict[str, dict], answer_col: int) -> str:
    if not line.startswith("| R-"):
        return line
    parts = [p.strip() for p in line.strip().strip("|").split("|")]
    if not parts:
        return line
    qid = parts[0]
    row = by_id.get(qid)
    if not row:
        return line
    resp = row.get("response") or {}
    err = row.get("error")
    answer = resp.get("answer") if resp else None
    cell = _cell(err or answer)
    while len(parts) <= answer_col:
        parts.append("")
    parts[answer_col] = cell
    return "| " + " | ".join(parts) + " |"


def build_section12(catalog: list[dict], results: list[dict], meta: dict, model_cfg: dict) -> str:
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    from eval_run_metadata import format_model_header, format_model_short

    model_block = format_model_header(model_cfg)
    model_short = format_model_short(model_cfg)
    by_id = {r["id"]: r for r in results}
    merged: list[dict] = []
    for item in catalog:
        qid = item["id"]
        if qid in by_id:
            merged.append(by_id[qid])
        else:
            merged.append(
                {
                    "id": qid,
                    "category": item.get("category"),
                    "question": item["question"],
                    "gold": item.get("gold"),
                    "response": None,
                    "error": None,
                }
            )

    answered = sum(1 for r in merged if r.get("response") and not r.get("error"))
    errors = sum(1 for r in merged if r.get("error"))
    abstained = sum(
        1
        for r in merged
        if r.get("response")
        and _outcome(r["response"].get("answer"), None) == "Abstained"
    )
    pending = len(merged) - answered - errors
    latency = _latency_stats([r for r in merged if r.get("response") or r.get("error")])

    header = f"""## 12. Final RAG evaluation workbook (Q&A)

**Status:** Populated from local LM Studio batch run (`eval/rag_eval_55_results.json`).  
**Run timestamp (UTC):** {meta.get('ts', 'unknown')}  
**Endpoint:** `POST /rag/ask` (`language=en`, `allow_world_knowledge=false`)  
**Summary:** {answered}/{len(merged)} answered · {abstained} abstained · {errors} errors · {pending} pending  
{_latency_summary_line(latency)}  
**Professor German set:** fully populated in **§10** (cloud exploratory) and **§11** (LM Studio).

{model_block}

"""
    timing_table = _build_timing_table(
        [r for r in merged if r.get("response") or r.get("error")], model_short
    )

    factual_header = f"""### 12.1 Direct factual (15)

| ID | Question | Expected key points | System answer | Model | Request time | P@3 | R@3 | nDCG@3 | Acc | Comp | Rel | Grnd | Cit | Abst |
| -- | -------- | ------------------- | ------------- | ----- | ------------ | --- | --- | ------ | --- | ---- | --- | ---- | --- | ---- |
"""

    factual_rows = []
    for r in merged:
        if _prefix(r["id"], "factual"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            lat = _fmt_elapsed_ms(r.get("elapsed_ms"))
            factual_rows.append(
                f"| {r['id']} | {r['question']} | {r.get('gold', '')} | {ans} | {model_short} | {lat} | | | | | | | | | |"
            )

    complex_header = """
### 12.2 Complex / multi-step (10)

| ID | Question | Expected key points | System answer | Model | Request time | Metrics / scores |
| -- | -------- | ------------------- | ------------- | ----- | ------------ | ---------------- |
"""
    complex_rows = []
    for r in merged:
        if _prefix(r["id"], "complex"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            gold = r.get("gold", "")
            if r["id"] == "R-C04" and not ans:
                ans = "*See EXP-R05 / LM-R05 in §10–§11*"
            complex_rows.append(
                f"| {r['id']} | {r['question']} | {gold} | {ans} | {model_short} | {_fmt_elapsed_ms(r.get('elapsed_ms'))} | |"
            )

    figure_header = """
### 12.3 Figure-related (10)

| ID | Question | Expected figure topic | System answer | Model | Request time | Fig success? | Images OK? | Scores |
| -- | -------- | --------------------- | ------------- | ----- | ------------ | ------------ | ---------- | ------ |
"""
    figure_rows = []
    for r in merged:
        if _prefix(r["id"], "figure"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            imgs = (resp.get("images") or []) if resp else []
            fig_ok = "Yes" if imgs else ("No" if resp and not r.get("error") else "")
            figure_rows.append(
                f"| {r['id']} | {r['question']} | {r.get('gold', '')} | {ans} | {model_short} | {_fmt_elapsed_ms(r.get('elapsed_ms'))} | | {fig_ok} | |"
            )

    quote_header = """
### 12.4 Exact quotation (5)

| ID | Question | Expected behavior | System answer | Model | Request time | Quote verified? | Score |
| -- | -------- | ----------------- | ------------- | ----- | ------------ | --------------- | ----- |
"""
    quote_rows = []
    for r in merged:
        if _prefix(r["id"], "quotation"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            quote_rows.append(
                f"| {r['id']} | {r['question']} | {r.get('gold', '')} | {ans} | {model_short} | {_fmt_elapsed_ms(r.get('elapsed_ms'))} | | |"
            )

    boundary_header = """
### 12.5 Unsupported / off-topic / boundary (10)

| ID | Question | Expected behavior | System answer | Model | Request time | Correct abstention? | Unsafe answer? |
| -- | -------- | ----------------- | ------------- | ----- | ------------ | ------------------- | -------------- |
"""
    boundary_rows = []
    for r in merged:
        if _prefix(r["id"], "boundary"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            outcome = _outcome(resp.get("answer") if resp else None, r.get("error"))
            abst_ok = "Yes" if outcome == "Abstained" else ("No" if outcome.startswith("Answered") else "")
            boundary_rows.append(
                f"| {r['id']} | {r['question']} | {r.get('gold', '')} | {ans} | {model_short} | {_fmt_elapsed_ms(r.get('elapsed_ms'))} | {abst_ok} | |"
            )

    robust_header = """
*Run subset with `allow_world_knowledge = true` to measure **consent compliance** separately.*

### 12.6 Robustness variants (5)

| ID | Base | Variant | Question | System answer | Model | Request time | Stable? | Typo recovered? |
| -- | ---- | ------- | -------- | ------------- | ----- | ------------ | ------- | --------------- |
"""
    robust_meta = {
        "R-R01": ("brainstem", "typo"),
        "R-R02": ("brainstem", "abbreviation"),
        "R-R03": ("femur", "laterality"),
        "R-R04": ("mitral valve", "paraphrase"),
        "R-R05": ("cerebellum", "short form"),
    }
    robust_rows = []
    for r in merged:
        if _prefix(r["id"], "robustness"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            base, variant = robust_meta.get(r["id"], ("", ""))
            robust_rows.append(
                f"| {r['id']} | {base} | {variant} | {r['question']} | {ans} | {model_short} | {_fmt_elapsed_ms(r.get('elapsed_ms'))} | | |"
            )

    details_header = """
---

### 12.7 Full Q&A detail (English RAG batch)

"""
    details = "".join(
        _detail_block(r, model_short) for r in merged if r.get("response") or r.get("error")
    )

    return (
        header
        + timing_table
        + factual_header
        + "\n".join(factual_rows)
        + complex_header
        + "\n".join(complex_rows)
        + figure_header
        + "\n".join(figure_rows)
        + quote_header
        + "\n".join(quote_rows)
        + boundary_header
        + "\n".join(boundary_rows)
        + robust_header
        + "\n".join(robust_rows)
        + "\n---\n\n"
        + details_header
        + details
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--md", type=Path, default=MD)
    args = ap.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if args.json.exists():
        data = json.loads(args.json.read_text(encoding="utf-8"))
        results = data.get("results", [])
        meta = data.get("meta", {})
    else:
        results = []
        meta = {}

    sys.path.insert(0, str(REPO / "scripts"))
    from eval_run_metadata import resolve_model_block

    model_cfg = resolve_model_block("english_rag_55", meta)

    md_text = args.md.read_text(encoding="utf-8")
    start = md_text.find(SECTION12_START)
    end = md_text.find(SECTION13_START)
    if start < 0 or end < 0:
        raise SystemExit("Could not find §12 or §13 markers in evaluationThesis.md")

    new_section = build_section12(catalog, results, meta, model_cfg)
    updated = md_text[:start] + new_section + "\n\n" + md_text[end:]
    args.md.write_text(updated, encoding="utf-8")
    print(f"Updated §12 in {args.md} ({len(results)}/{len(catalog)} results merged)")


if __name__ == "__main__":
    main()
