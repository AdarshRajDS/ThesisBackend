#!/usr/bin/env python3
"""Build §9.2 thesis results dashboard and restructure results overview."""

from __future__ import annotations

import json
import re
from pathlib import Path

from build_eval_section import PROFESSOR_META, _outcome
from build_eval_section12 import (
    EXCLUDED_IDS,
    _boundary_abstention_ok,
    _fig_success,
    _grounding_ok,
    _citation_ok,
    _in_scored_set,
    compute_aggregate_metrics,
    load_rag_results,
)

REPO = Path(__file__).resolve().parents[1]
MD = REPO / "evaluationThesis.md"
RETRIEVAL_METRICS_JSON = REPO / "eval" / "retrieval_metrics.json"
SECTION_START = "## 9.2 Thesis primary run — results dashboard (12 July 2026)"
SECTION_END = "## 10."


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}"


def _load_retr() -> dict:
    if not RETRIEVAL_METRICS_JSON.exists():
        return {}
    return json.loads(RETRIEVAL_METRICS_JSON.read_text(encoding="utf-8"))


def _professor_stats(rows: list[dict]) -> dict:
    ok = [r for r in rows if not r.get("error")]
    err = [r for r in rows if r.get("error")]
    outcomes = {}
    for r in ok:
        o = _outcome((r.get("response") or {}).get("answer"), None)
        outcomes[o] = outcomes.get(o, 0) + 1
    wk = outcomes.get("Answered (world knowledge)", 0)
    grounded = sum(
        1
        for r in ok
        if _outcome((r.get("response") or {}).get("answer"), None) == "Answered"
        and ((r.get("response") or {}).get("grounding") or {}).get("had_retrieved_passages_in_prompt")
    )
    return {
        "administered": len(rows),
        "scored": len(ok),
        "errors": len(err),
        "world_knowledge": wk,
        "corpus_answered": len(ok) - wk,
        "grounded_with_retrieval": grounded,
        "error_ids": [f"LM-R{i+1:02d}" for i, r in enumerate(rows) if r.get("error")],
    }


def build_dashboard() -> str:
    from eval_run_metadata import format_model_short, resolve_model_block

    prof_cfg = resolve_model_block("local_professor_de")
    eng_cfg = resolve_model_block("english_rag_55")
    model = prof_cfg.get("model_display") or format_model_short(prof_cfg)

    prof_rows = json.loads((REPO / "german_eval_lmstudio_results.json").read_text(encoding="utf-8"))
    catalog, rag_rows = load_rag_results()
    agg = compute_aggregate_metrics(catalog, rag_rows)

    ps = _professor_stats(prof_rows)
    retr = _load_retr()
    eng_retr = retr.get("english_rag_55", {}).get("summary_non_boundary", {})
    prof_retr = retr.get("professor_de", {}).get("summary", {})

    excluded_lines = "\n".join(
        f"| {eid} | {EXCLUDED_IDS.get(eid, '?')} | Infrastructure — excluded from thesis metrics |"
        for eid in sorted(EXCLUDED_IDS)
    )

    return f"""{SECTION_START}

**Primary model (12 July 2026):** {model}  
**Stack:** LM Studio · `POST /rag/ask` · local hybrid RAG · `allow_world_knowledge=false` (English)

This dashboard summarizes the **thesis primary evaluation**. Historical cloud Groq results remain in **§10** for comparison only.

### Quick navigation

| Section | Content |
| ------- | ------- |
| [§9.1](#91-professor-evaluation-metrics-workbook) | Professor metrics tables (9 + 9) |
| [§11](#11-local-lm-studio-experiment-qa) | Professor German — full Q&A detail |
| [§12.0](#120-at-a-glance-metric-summary) | English 55-Q — metric summary (n=51) |
| [§12.1–12.7](#121-direct-factual-15) | English category tables + full Q&A |

---

### Professor German set (n=9)

| Metric | Value |
| ------ | ----- |
| Model | `{prof_cfg.get('model_configured')}` |
| Administered | {ps['administered']} |
| Successful responses | {ps['scored']} |
| Infrastructure errors | {ps['errors']} ({', '.join(ps['error_ids']) or '—'}) |
| Answered from corpus | {ps['corpus_answered']} |
| World-knowledge fallback | {ps['world_knowledge']} |
| With retrieved passages in prompt | {ps['grounded_with_retrieval']} |
| **P@3** (embedding proxy) | {_fmt(prof_retr.get('precision_at_k'))} |
| **R@3** | {_fmt(prof_retr.get('recall_at_k'))} |
| **nDCG@3** | {_fmt(prof_retr.get('ndcg_at_k'))} |
| **MRR** | {_fmt(prof_retr.get('mrr'))} |
| **Source overlap** | {_fmt(prof_retr.get('source_overlap'))} |

---

### English RAG workbook (55 administered → **51 scored**)

| Metric | Value |
| ------ | ----- |
| Model | `{eng_cfg.get('model_configured')}` |
| Batch completed | 12 July 2026 (~5.8 h) |
| Administered | {agg['administered']} |
| **Scored (thesis n)** | **{agg['scored']}** |
| Excluded (infra) | {agg['excluded']} |
| Answered (corpus) | {agg['answered_corpus']} |
| Answered (world knowledge) | {agg['answered_world']} |
| Abstained | {agg['abstained']} |
| Retrieval present (Grnd) | {agg['grounding_yes']}/{agg['scored']} ({agg['grounding_pct']:.0f}%) |
| ≥1 source returned (Cit proxy) | {agg['citation_yes']}/{agg['scored']} ({agg['citation_pct']:.0f}%) |
| Figure w/ ≥1 image (10 fig Q, scored) | {agg['fig_yes']}/{agg['fig_total']} ({agg['fig_pct']:.0f}%) |
| Boundary correct abstention (scored) | {agg['boundary_abst_ok']}/{agg['boundary_total']} ({agg['boundary_pct']:.0f}%) |
| Mean sources per scored question | {agg['mean_sources']:.1f} |
| **P@3** (non-boundary, n={eng_retr.get('n', '—')}) | {_fmt(eng_retr.get('precision_at_k'))} |
| **R@3** | {_fmt(eng_retr.get('recall_at_k'))} |
| **nDCG@3** | {_fmt(eng_retr.get('ndcg_at_k'))} |
| **MRR** | {_fmt(eng_retr.get('mrr'))} |
| **Source overlap** | {_fmt(eng_retr.get('source_overlap'))} |

**Excluded from English metrics (do not count toward n=51):**

| ID | Failure | Note |
| -- | ------- | ---- |
{excluded_lines}

*Retrieval metrics: automatic embedding proxy (`eval/retrieval_metrics.json`, §12.0.2). Human rubric (Acc, Comp, Rel) still pending.*

---

"""


def patch_section2_measured(md_text: str, eng_retr: dict) -> str:
    """Add measured retrieval row under §2.1 criteria table."""
    if not eng_retr.get("precision_at_k"):
        return md_text
    marker = "**Thesis use:** Compare dense-only vs final hybrid BM25 + dense + RRF pipeline on the same frozen question set."
    insert = (
        "\n\n**Measured (12 Jul 2026, English n=43 non-boundary, k=3):** "
        f"P@3={_fmt(eng_retr.get('precision_at_k'))} · "
        f"R@3={_fmt(eng_retr.get('recall_at_k'))} · "
        f"nDCG@3={_fmt(eng_retr.get('ndcg_at_k'))} · "
        f"MRR={_fmt(eng_retr.get('mrr'))} · "
        f"source overlap={_fmt(eng_retr.get('source_overlap'))}. "
        "Automatic proxy — see §12.0.2.\n"
    )
    if insert.strip() in md_text:
        return md_text
    return md_text.replace(marker, insert + "\n" + marker, 1)


def main() -> None:
    retr = _load_retr()
    eng_retr = retr.get("english_rag_55", {}).get("summary_non_boundary", {})
    section = build_dashboard()
    md = MD.read_text(encoding="utf-8")
    md = patch_section2_measured(md, eng_retr)
    start = md.find(SECTION_START)
    end = md.find(SECTION_END)
    if start >= 0 and end > start:
        md = md[:start] + section + md[end:]
    else:
        anchor = md.find("\n## 10.")
        if anchor < 0:
            raise SystemExit("Could not find §10")
        md = md[:anchor] + "\n" + section + md[anchor:]
    MD.write_text(md, encoding="utf-8")
    print(f"Updated {MD} — §9.2 thesis dashboard")


if __name__ == "__main__":
    main()
