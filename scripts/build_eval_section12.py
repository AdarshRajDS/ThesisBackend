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
EXCLUDED_FILE = REPO / "eval" / "rag_eval_excluded.json"

SECTION12_START = "## 12. Final RAG evaluation workbook"
SECTION13_START = "## 13. MCP evaluation workbook"


def _load_excluded_ids() -> dict[str, str]:
    if not EXCLUDED_FILE.exists():
        return {}
    data = json.loads(EXCLUDED_FILE.read_text(encoding="utf-8"))
    reasons = data.get("reasons", {})
    return {qid: reasons.get(qid, "excluded") for qid in data.get("excluded_ids", [])}


EXCLUDED_IDS = _load_excluded_ids()


def load_rag_results(
    json_path: Path = DEFAULT_JSON,
    catalog_path: Path = DEFAULT_CATALOG,
) -> tuple[list[dict], list[dict]]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        results = data.get("results", [])
    else:
        results = []
    return catalog, results


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


def _sanitize_answer(text: str) -> str:
    if not text:
        return text
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            lines.append("#### " + line[3:])
        else:
            lines.append(line)
    return "\n".join(lines)


def _fmt_elapsed_ms(ms: float | None) -> str:
    if ms is None:
        return ""
    s = ms / 1000
    if s >= 60:
        return f"{s / 60:.1f} min"
    if s >= 10:
        return f"{s:.0f} s"
    return f"{s:.1f} s"


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


def _in_scored_set(row: dict) -> bool:
    if row.get("error"):
        return False
    if row["id"] in EXCLUDED_IDS:
        return False
    return bool(row.get("response"))


def _grounding_ok(resp: dict | None) -> bool:
    if not resp:
        return False
    g = resp.get("grounding") or {}
    return bool(g.get("had_retrieved_passages_in_prompt"))


def _citation_ok(resp: dict | None) -> bool:
    if not resp:
        return False
    return len(resp.get("sources") or []) > 0


def _fig_success(resp: dict | None) -> bool:
    if not resp:
        return False
    return len(resp.get("images") or []) > 0


def _boundary_abstention_ok(row: dict) -> bool:
    resp = row.get("response") or {}
    return _outcome(resp.get("answer"), row.get("error")) == "Abstained"


def _scored_label(row: dict) -> str:
    if row["id"] in EXCLUDED_IDS:
        return "No (infra)"
    if row.get("error"):
        return "No (error)"
    return "Yes"


def compute_aggregate_metrics(catalog: list[dict], results: list[dict]) -> dict:
    by_id = {r["id"]: r for r in results}
    merged = []
    for item in catalog:
        qid = item["id"]
        merged.append(by_id.get(qid) or {"id": qid, "category": item.get("category"), "response": None, "error": None})

    administered = len(merged)
    scored_rows = [r for r in merged if _in_scored_set(r)]
    excluded = len([r for r in merged if r["id"] in EXCLUDED_IDS])
    errors_other = len([r for r in merged if r.get("error") and r["id"] not in EXCLUDED_IDS])

    outcomes = {}
    for r in scored_rows:
        resp = r.get("response") or {}
        o = _outcome(resp.get("answer"), None)
        outcomes[o] = outcomes.get(o, 0) + 1

    grounding_yes = sum(1 for r in scored_rows if _grounding_ok(r.get("response")))
    citation_yes = sum(1 for r in scored_rows if _citation_ok(r.get("response")))

    fig_rows = [r for r in scored_rows if _prefix(r["id"], "figure")]
    fig_yes = sum(1 for r in fig_rows if _fig_success(r.get("response")))

    boundary_rows = [r for r in scored_rows if _prefix(r["id"], "boundary")]
    boundary_ok = sum(1 for r in boundary_rows if _boundary_abstention_ok(r))

    source_counts = [len((r.get("response") or {}).get("sources") or []) for r in scored_rows]
    mean_sources = sum(source_counts) / len(source_counts) if source_counts else 0.0

    latency_rows = [r for r in merged if r.get("elapsed_ms") is not None and _in_scored_set(r)]
    latencies = [r["elapsed_ms"] for r in latency_rows]

    return {
        "administered": administered,
        "scored": len(scored_rows),
        "excluded": excluded,
        "errors_other": errors_other,
        "answered_corpus": outcomes.get("Answered", 0),
        "answered_world": outcomes.get("Answered (world knowledge)", 0),
        "abstained": outcomes.get("Abstained", 0),
        "grounding_yes": grounding_yes,
        "grounding_pct": 100 * grounding_yes / len(scored_rows) if scored_rows else 0,
        "citation_yes": citation_yes,
        "citation_pct": 100 * citation_yes / len(scored_rows) if scored_rows else 0,
        "fig_yes": fig_yes,
        "fig_total": len(fig_rows),
        "fig_pct": 100 * fig_yes / len(fig_rows) if fig_rows else 0,
        "boundary_abst_ok": boundary_ok,
        "boundary_total": len(boundary_rows),
        "boundary_pct": 100 * boundary_ok / len(boundary_rows) if boundary_rows else 0,
        "mean_sources": mean_sources,
        "latency_count": len(latencies),
        "latency_min_ms": min(latencies) if latencies else None,
        "latency_max_ms": max(latencies) if latencies else None,
        "latency_avg_ms": sum(latencies) / len(latencies) if latencies else None,
        "latency_total_ms": sum(latencies) if latencies else None,
    }


def _category_metrics(rows: list[dict], kind: str) -> dict:
    cat_rows = [r for r in rows if _prefix(r["id"], kind) and _in_scored_set(r)]
    if not cat_rows:
        return {"n": 0}
    return {
        "n": len(cat_rows),
        "answered": sum(1 for r in cat_rows if _outcome((r.get("response") or {}).get("answer"), None) == "Answered"),
        "abstained": sum(1 for r in cat_rows if _outcome((r.get("response") or {}).get("answer"), None) == "Abstained"),
        "grounding": sum(1 for r in cat_rows if _grounding_ok(r.get("response"))),
        "citation": sum(1 for r in cat_rows if _citation_ok(r.get("response"))),
    }


def _build_at_a_glance(merged: list[dict], agg: dict, model_short: str) -> str:
    excluded_note = ", ".join(f"`{qid}` ({reason})" for qid, reason in sorted(EXCLUDED_IDS.items()))
    cats = [
        ("Direct factual", "factual", 15),
        ("Complex / multi-step", "complex", 10),
        ("Figure-related", "figure", 10),
        ("Exact quotation", "quotation", 5),
        ("Boundary / off-topic", "boundary", 10),
        ("Robustness variants", "robustness", 5),
    ]
    cat_lines = [
        "| Category | Administered | Scored | Answered | Abstained | Grnd (proxy) | Cit (proxy) |",
        "| -------- | ------------ | ------ | -------- | --------- | ------------ | ----------- |",
    ]
    for label, kind, total in cats:
        m = _category_metrics(merged, kind)
        admin = sum(1 for r in merged if _prefix(r["id"], kind))
        if m["n"]:
            cat_lines.append(
                f"| {label} | {admin} | {m['n']} | {m['answered']} | {m['abstained']} | "
                f"{m['grounding']}/{m['n']} | {m['citation']}/{m['n']} |"
            )
        else:
            cat_lines.append(f"| {label} | {admin} | 0 | — | — | — | — |")

    lat_line = ""
    if agg.get("latency_count"):
        lat_line = (
            f"\n**Latency (scored questions only):** min {_fmt_elapsed_ms(agg['latency_min_ms'])} · "
            f"avg {_fmt_elapsed_ms(agg['latency_avg_ms'])} · "
            f"max {_fmt_elapsed_ms(agg['latency_max_ms'])} · "
            f"total {_fmt_elapsed_ms(agg['latency_total_ms'])}\n"
        )

    return f"""### 12.0 At-a-glance metric summary (n={agg['scored']})

**Model:** {model_short}  
**Run date:** 12 July 2026  
**Scoring rule:** {agg['administered']} administered → **{agg['scored']} scored** (exclude {agg['excluded']} infra failures: {excluded_note})

| Aggregate | Value |
| --------- | ----- |
| Answered (corpus) | {agg['answered_corpus']} |
| Answered (world knowledge) | {agg['answered_world']} |
| Abstained | {agg['abstained']} |
| Retrieval in prompt (Grnd proxy) | {agg['grounding_yes']}/{agg['scored']} ({agg['grounding_pct']:.0f}%) |
| ≥1 source returned (Cit proxy) | {agg['citation_yes']}/{agg['scored']} ({agg['citation_pct']:.0f}%) |
| Figure w/ ≥1 image | {agg['fig_yes']}/{agg['fig_total']} ({agg['fig_pct']:.0f}%) |
| Boundary correct abstention | {agg['boundary_abst_ok']}/{agg['boundary_total']} ({agg['boundary_pct']:.0f}%) |
| Mean sources per scored Q | {agg['mean_sources']:.1f} |

{chr(10).join(cat_lines)}
{lat_line}
*P@3, R@3, nDCG@3 and human rubric (Acc, Comp, Rel) require expert labeling — left blank below.*

---

"""


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
        "### 12.0.1 Per-question request latency",
        "",
        "Wall-clock time for one `POST /rag/ask` call (retrieval + local LM Studio generation). Excluded infra failures still listed for traceability.",
        "",
        "| ID | Scored? | Category | Outcome | Model | Request time |",
        "| -- | ------- | -------- | ------- | ----- | ------------ |",
    ]
    for r in measured:
        resp = r.get("response") or {}
        outcome = _outcome(resp.get("answer") if resp else None, r.get("error"))
        lines.append(
            f"| {r['id']} | {_scored_label(r)} | {r.get('category', '')} | {outcome} | "
            f"{model_short} | {_fmt_elapsed_ms(r['elapsed_ms'])} |"
        )
    lines.extend(["", "---", ""])
    return "\n".join(lines)


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
    excluded = qid in EXCLUDED_IDS

    lines = [
        f"### {qid} — {row['question'][:72]}{'…' if len(row['question']) > 72 else ''}",
        "",
        "| Field | Content |",
        "| ----- | ------- |",
        f"| **ID** | {qid} |",
        f"| **Category** | {row.get('category', '')} |",
        f"| **Outcome** | {outcome} |",
        f"| **Scored in thesis metrics?** | {'No — ' + EXCLUDED_IDS.get(qid, 'excluded') if excluded else 'Yes'} |",
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
        lines.append(_sanitize_answer(answer or "*empty*"))

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


def _metric_cells(row: dict) -> tuple[str, str, str]:
    if not _in_scored_set(row):
        return "—", "—", "—"
    resp = row.get("response") or {}
    grnd = "Yes" if _grounding_ok(resp) else "No"
    cit = "Yes" if _citation_ok(resp) else "No"
    abst = "Yes" if _outcome(resp.get("answer"), None) == "Abstained" else "No"
    return grnd, cit, abst


def build_section12(catalog: list[dict], results: list[dict], meta: dict, model_cfg: dict) -> str:
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

    agg = compute_aggregate_metrics(catalog, results)
    scored_count = agg["scored"]
    errors = agg["excluded"] + agg["errors_other"]
    abstained = agg["abstained"]
    latency = _latency_stats([r for r in merged if r.get("response") or r.get("error")])

    header = f"""## 12. Final RAG evaluation workbook (Q&A)

**Thesis primary run:** 12 July 2026 · **{scored_count} scored** / {len(merged)} administered (4 infra failures excluded from metrics)  
**Status:** Populated from `eval/rag_eval_55_results.json`  
**Run timestamp (UTC):** {meta.get('ts', 'unknown')}  
**Endpoint:** `POST /rag/ask` (`language=en`, `allow_world_knowledge=false`)  
**Summary (scored only):** {agg['answered_corpus']} corpus answers · {agg['answered_world']} world-knowledge · {abstained} abstained · {errors} not scored  
{_latency_summary_line(latency)}  
**Professor German set:** §9.2 dashboard · §11 full Q&A · §10 historical cloud comparison

{model_block}

"""
    at_a_glance = _build_at_a_glance(merged, agg, model_short)
    timing_table = _build_timing_table(
        [r for r in merged if r.get("response") or r.get("error")], model_short
    )

    factual_header = f"""### 12.1 Direct factual (15)

| ID | Scored? | Question | Expected key points | System answer | Model | Request time | P@3 | R@3 | nDCG@3 | Acc | Comp | Rel | Grnd | Cit | Abst |
| -- | ------- | -------- | ------------------- | ------------- | ----- | ------------ | --- | --- | ------ | --- | ---- | --- | ---- | --- | ---- |
"""

    factual_rows = []
    for r in merged:
        if _prefix(r["id"], "factual"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            grnd, cit, abst = _metric_cells(r)
            factual_rows.append(
                f"| {r['id']} | {_scored_label(r)} | {r['question']} | {r.get('gold', '')} | {ans} | "
                f"{model_short} | {_fmt_elapsed_ms(r.get('elapsed_ms'))} | | | | | | | {grnd} | {cit} | {abst} |"
            )

    complex_header = """
### 12.2 Complex / multi-step (10)

| ID | Scored? | Question | Expected key points | System answer | Model | Request time | Grnd | Cit | Metrics / scores |
| -- | ------- | -------- | ------------------- | ------------- | ----- | ------------ | ---- | --- | ---------------- |
"""
    complex_rows = []
    for r in merged:
        if _prefix(r["id"], "complex"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            grnd, cit, _ = _metric_cells(r)
            gold = r.get("gold", "")
            if r["id"] == "R-C04" and not ans:
                ans = "*See EXP-R05 / LM-R05 in §10–§11*"
            complex_rows.append(
                f"| {r['id']} | {_scored_label(r)} | {r['question']} | {gold} | {ans} | {model_short} | "
                f"{_fmt_elapsed_ms(r.get('elapsed_ms'))} | {grnd} | {cit} | |"
            )

    figure_header = """
### 12.3 Figure-related (10)

| ID | Scored? | Question | Expected figure topic | System answer | Model | Request time | Fig success? | Images OK? | Scores |
| -- | ------- | -------- | --------------------- | ------------- | ----- | ------------ | ------------ | ---------- | ------ |
"""
    figure_rows = []
    for r in merged:
        if _prefix(r["id"], "figure"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            imgs = (resp.get("images") or []) if resp else []
            fig_ok = "Yes" if imgs and _in_scored_set(r) else ("No" if resp and _in_scored_set(r) else "—")
            images_ok = fig_ok
            figure_rows.append(
                f"| {r['id']} | {_scored_label(r)} | {r['question']} | {r.get('gold', '')} | {ans} | {model_short} | "
                f"{_fmt_elapsed_ms(r.get('elapsed_ms'))} | {fig_ok} | {images_ok} | |"
            )

    quote_header = """
### 12.4 Exact quotation (5)

| ID | Scored? | Question | Expected behavior | System answer | Model | Request time | Quote verified? | Grnd | Cit | Score |
| -- | ------- | -------- | ----------------- | ------------- | ----- | ------------ | --------------- | ---- | --- | ----- |
"""
    quote_rows = []
    for r in merged:
        if _prefix(r["id"], "quotation"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            grnd, cit, _ = _metric_cells(r)
            quote_rows.append(
                f"| {r['id']} | {_scored_label(r)} | {r['question']} | {r.get('gold', '')} | {ans} | {model_short} | "
                f"{_fmt_elapsed_ms(r.get('elapsed_ms'))} | | {grnd} | {cit} | |"
            )

    boundary_header = """
### 12.5 Unsupported / off-topic / boundary (10)

| ID | Scored? | Question | Expected behavior | System answer | Model | Request time | Correct abstention? | Unsafe answer? |
| -- | ------- | -------- | ----------------- | ------------- | ----- | ------------ | ------------------- | -------------- |
"""
    boundary_rows = []
    for r in merged:
        if _prefix(r["id"], "boundary"):
            resp = r.get("response") or {}
            ans = _cell(r.get("error") or resp.get("answer"))
            if _in_scored_set(r):
                abst_ok = "Yes" if _boundary_abstention_ok(r) else "No"
            else:
                abst_ok = "—"
            boundary_rows.append(
                f"| {r['id']} | {_scored_label(r)} | {r['question']} | {r.get('gold', '')} | {ans} | {model_short} | "
                f"{_fmt_elapsed_ms(r.get('elapsed_ms'))} | {abst_ok} | |"
            )

    robust_header = """
*Run subset with `allow_world_knowledge = true` to measure **consent compliance** separately.*

### 12.6 Robustness variants (5)

| ID | Scored? | Base | Variant | Question | System answer | Model | Request time | Stable? | Typo recovered? |
| -- | ------- | ---- | ------- | -------- | ------------- | ----- | ------------ | ------- | --------------- |
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
                f"| {r['id']} | {_scored_label(r)} | {base} | {variant} | {r['question']} | {ans} | {model_short} | "
                f"{_fmt_elapsed_ms(r.get('elapsed_ms'))} | | |"
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
        + at_a_glance
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

    catalog, results = load_rag_results(args.json, args.catalog)
    meta = {}
    if args.json.exists():
        meta = json.loads(args.json.read_text(encoding="utf-8")).get("meta", {})

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
    agg = compute_aggregate_metrics(catalog, results)
    print(f"Updated §12 in {args.md} ({len(results)}/{len(catalog)} results; n={agg['scored']} scored)")


if __name__ == "__main__":
    main()
