"""
Thesis-only pipeline: baseline → strict RAG → coherent synthesized RAG → blind judge (baseline vs strict) + log.
Does not replace production `MultimodalRAG.ask` / `POST /rag/ask`.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.llm.llm_factory import get_groq_llm
from src.multimodal.run_multimodal_rag import get_rag


def _strip_json_fences(raw: str) -> str:
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```json\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^```\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _build_numbered_passages(bundle: dict[str, Any]) -> tuple[str, int]:
    """
    Flat passages with stable [n] ids for citations (text index + optional multimodal excerpt).
    """
    parts: list[str] = []
    n = 1
    for d in bundle.get("text_corpus_docs") or []:
        meta = getattr(d, "metadata", None) or {}
        raw_src = meta.get("source") or meta.get("file_path")
        src = os.path.basename(str(raw_src)) if raw_src else "unknown"
        page = meta.get("page", "?")
        body = (getattr(d, "page_content", None) or "").strip()
        if not body:
            continue
        parts.append(f"[{n}] Source: {src} | Page: {page}\n{body}")
        n += 1

    mt = (bundle.get("multimodal_text") or "").strip()
    if mt:
        cap = 3500
        mt_body = mt[:cap] + ("…" if len(mt) > cap else "")
        parts.append(f"[{n}] Source: multimodal_index | Page: n/a\n{mt_body}")
        n += 1

    text = "\n\n".join(parts)
    return text, len(parts)


def run_thesis_rag_experiment(question: str, *, persist_log: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    rag = get_rag()
    bundle = rag.gather_retrieval_bundle(question)
    blocks: list[str] = bundle["context_blocks"]
    numbered_passages, num_numbered = _build_numbered_passages(bundle)
    if num_numbered == 0:
        strict_context = "NO_PASSAGES_RETRIEVED"
    else:
        strict_context = numbered_passages

    baseline_llm = get_groq_llm(0.7)
    strict_llm = get_groq_llm(0.2)
    coherent_llm = get_groq_llm(0.3)
    judge_llm = get_groq_llm(0.0)

    baseline_ans = baseline_llm.invoke(question).content

    strict_prompt = f"""You are a medical anatomy assistant.

You MUST answer ONLY using the numbered passages below. Do not use other medical knowledge.

Rules:
- Every substantive claim must be traceable to a passage; cite with inline markers like [1] or [2] matching the passage numbers.
- Do NOT use external medical knowledge beyond what is clearly stated in the passages.
- If the answer cannot be found in the passages, respond exactly with: Not found in provided documents

Passages:
{strict_context}

Question:
{question}
"""

    strict_ans = strict_llm.invoke(strict_prompt).content

    if strict_context == "NO_PASSAGES_RETRIEVED":
        coherent_ans = "Not found in provided documents"
    else:
        coherent_prompt = f"""You are a medical anatomy assistant.

You must answer using ONLY information supported by the numbered passages below. Do not invent anatomy, pathways, or clinical facts that do not appear there.

Question:
{question}

Retrieved passages:
{strict_context}

Instructions:
- Write ONE coherent, readable explanation in flowing paragraphs. Do not produce a disjoint list of unrelated sentence fragments.
- You may synthesize and reorder ideas for clarity, but every substantive claim must still be traceable to the passages.
- Use inline citations [1], [2], etc. matching the passage numbers. Do not use placeholder citation text.
- If the passages do not contain enough information to answer, respond exactly with: Not found in provided documents
- If two passages appear to conflict, state both views briefly as given in the text.

Answer:
"""
        coherent_ans = coherent_llm.invoke(coherent_prompt).content

    rag_first = random.random() < 0.5
    if rag_first:
        text_a, label_a = strict_ans, "strict_rag"
        text_b, label_b = baseline_ans, "baseline"
    else:
        text_a, label_a = baseline_ans, "baseline"
        text_b, label_b = strict_ans, "strict_rag"

    judge_ctx = strict_context if strict_context != "NO_PASSAGES_RETRIEVED" else "(no passages in index)"
    max_ctx = 12000
    if len(judge_ctx) > max_ctx:
        judge_ctx = judge_ctx[:max_ctx] + "\n...[truncated]"

    judge_prompt = f"""You are an expert evaluator. Compare two answers to the same question.

Criteria:
1. Faithfulness to the provided context (when context exists)
2. Relevance to the question
3. Completeness
4. Clarity

Question:
{question}

Answer A:
{text_a}

Answer B:
{text_b}

Retrieved context (for faithfulness; may be minimal if empty index):
{judge_ctx}

Return a SINGLE JSON object only (no markdown fences), with this exact shape:
{{
  "winner": "A",
  "scores": {{
    "faithfulness_a": 0.0,
    "faithfulness_b": 0.0,
    "relevance_a": 0.0,
    "relevance_b": 0.0,
    "completeness_a": 0.0,
    "completeness_b": 0.0,
    "clarity_a": 0.0,
    "clarity_b": 0.0
  }},
  "confidence": 0.0,
  "reasoning": "short explanation"
}}

winner must be exactly \"A\" or \"B\"."""

    raw_judge = judge_llm.invoke(judge_prompt).content

    evaluation: dict[str, Any] = {
        "parse_error": None,
        "raw_winner": None,
        "winner_label": None,
        "scores": None,
        "confidence": None,
        "reasoning": None,
        "presentation": {"A": label_a, "B": label_b},
    }
    try:
        payload = json.loads(_strip_json_fences(raw_judge))
        w = str(payload.get("winner") or "").strip().upper()
        evaluation["raw_winner"] = payload.get("winner")
        mapping = {"A": label_a, "B": label_b}
        if w in mapping:
            evaluation["winner_label"] = mapping[w]
        evaluation["scores"] = payload.get("scores")
        evaluation["confidence"] = payload.get("confidence")
        evaluation["reasoning"] = payload.get("reasoning")
    except (json.JSONDecodeError, TypeError) as e:
        evaluation["parse_error"] = str(e)
        evaluation["reasoning"] = (raw_judge or "")[:2000]

    public_images = rag.rank_and_publish_images(question, bundle["image_metas"])

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    out: dict[str, Any] = {
        "question": question,
        "baseline_answer": baseline_ans,
        "strict_rag_answer": strict_ans,
        "strict_rag_coherent": coherent_ans,
        "sources": bundle["text_sources"],
        "images": public_images,
        "evaluation": evaluation,
        "debug": {
            "presentation_order_rag_first": rag_first,
            "latency_ms": elapsed_ms,
            "had_retrieved_passages": bool(blocks),
            "num_sources": len(bundle["text_sources"]),
            "num_numbered_passages": num_numbered,
        },
    }

    if persist_log:
        log_dir = Path(settings.base_data_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "thesis_rag_eval.jsonl"
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "baseline_answer": baseline_ans,
            "strict_rag_answer": strict_ans,
            "strict_rag_coherent": coherent_ans,
            "evaluation": evaluation,
            "debug": out["debug"],
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        out["log_path"] = str(log_path.resolve())

    return out
