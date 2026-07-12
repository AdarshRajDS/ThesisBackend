#!/usr/bin/env python3
"""Build Section 9 of evaluationThesis.md from german_eval_results.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
JSON_PATH = REPO / "german_eval_results.json"
MD_PATH = REPO / "evaluationThesis.md"

# Professor question set metadata (IDs + gold hints)
META = [
    {
        "id": "EXP-R01",
        "category": "Complex / multi-step",
        "gold": "Peroneus longus/brevis, tibialis anterior/posterior, gastrocnemius/soleus, etc., grouped by dorsiflexion/plantarflexion/inversion/eversion — from lower-limb chapter in corpus.",
        "scores": (2, 1, 3, 4, 2, 4, "Correct refusal given bad retrieval; retrieval failure is the main issue"),
    },
    {
        "id": "EXP-R02",
        "category": "Complex + figure request",
        "gold": "Flexor digitorum superficialis/profundus, flexor pollicis longus, lumbricals; median/ulnar innervation; 2 relevant hand/forearm figures.",
        "scores": None,
        "error_note": "Reliability failure — HTTP 500",
    },
    {
        "id": "EXP-R03",
        "category": "Direct factual / clinical anatomy",
        "gold": "Humeral head high-riding: rotator cuff weakness, capsular tightness, postural factors; subacromial impingement — supraspinatus, bursa, acromion.",
        "scores": (2, 1, 3, 4, 2, 4, "Safe abstention; wrong passages retrieved (index/glossary)"),
    },
    {
        "id": "EXP-R04",
        "category": "Direct factual",
        "gold": "Iliopsoas (iliacus + psoas major) as primary hip flexor.",
        "scores": (2, 1, 3, 4, 2, 4, "Safe abstention; Recall@k failure"),
    },
    {
        "id": "EXP-R05",
        "category": "Direct factual + implicit figure",
        "gold": "Vestibular nuclei → oculomotor/trochlear/abducens nuclei; stabilizes retinal image during head movement; compensates head/body motion.",
        "scores": (4, 4, 5, 4, 3, 5, "Strong multimodal case; content aligned with page 131 passage"),
    },
    {
        "id": "EXP-R06",
        "category": "Complex / boundary",
        "gold": "Semicircular canals include horizontal and vertical planes; VOR operates in multiple planes — context may be partial.",
        "scores": (4, 3, 5, 5, 4, 5, "Good faithfulness — avoids over-claiming beyond corpus"),
    },
    {
        "id": "EXP-R07",
        "category": "Direct factual",
        "gold": "Pairings of rectus/oblique muscles with specific canal planes (superior/inferior/lateral).",
        "scores": (3, 2, 3, 3, 2, 4, "Incomplete; partial innervation only, no canal pairing"),
    },
    {
        "id": "EXP-R08",
        "category": "Direct factual",
        "gold": "Pump function, four-chamber flow, systemic/pulmonary circulation — from cardiovascular chapter.",
        "scores": (2, 1, 3, 4, 2, 4, "Abstention correct given retrieval; corpus likely has heart chapter"),
    },
    {
        "id": "EXP-R09",
        "category": "Complex / synthesis",
        "gold": "Scapulohumeral rhythm, deltoid, trapezius, serratus anterior, abduction/elevation — appendicular skeleton / shoulder chapters.",
        "scores": (2, 2, 2, 3, 2, 3, "Fluent but wrong topic (motor control vs shoulder girdle)"),
    },
]


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
        # Extract page hint from URL if present
        m = re.search(r"/page_(\d+)/", str(url))
        page_hint = f" (page {m.group(1)})" if m else ""
        lines.append(f"{i}. Figure URL{page_hint} — *(presigned URL from exploratory run; may be expired)*")
    return "\n".join(lines)


def _format_grounding(g: dict | None) -> str:
    if not g:
        return "*Not returned*"
    lines = []
    for k, v in g.items():
        lines.append(f"- **{k}:** {v}")
    return "\n".join(lines)


def _score_table(scores: tuple | None, error: str | None) -> str:
    if error:
        return f"**Exploratory scores:** N/A — {error}"
    if not scores:
        return ""
    acc, comp, rel, grnd, cit, bound, notes = scores
    return f"""**Exploratory scores (draft, 1–5)**

| Accuracy | Completeness | Relevance | Grounding | Citations | Boundary | Notes |
| --------: | -----------: | --------: | --------: | --------: | -------: | ----- |
| {acc} | {comp} | {rel} | {grnd} | {cit} | {bound} | {notes} |"""


def build_entry(item: dict, meta: dict) -> str:
    q = item["question"]
    err = item.get("error")
    resp = item.get("response") or {}
    title = q[:70] + ("…" if len(q) > 70 else "")

    parts = [
        f"### {meta['id']} — {title}",
        "",
        "| Field | Content |",
        "| ----- | ------- |",
        f"| **ID** | {meta['id']} |",
        f"| **Category** | {meta['category']} |",
        f"| **Language** | German |",
        f"| **Status** | Exploratory |",
        "",
        "**Question:**  ",
        q,
        "",
        "**Expected key points (gold, to verify manually):**  ",
        meta["gold"],
        "",
    ]

    if err:
        parts += [
            "**System answer:**  ",
            f"`{err}`",
            "",
            _score_table(None, meta.get("error_note", err)),
        ]
    else:
        answer = (resp.get("answer") or "").strip()
        parts += [
            "**System answer:**  ",
            answer if answer else "*Empty response*",
            "",
            "**Sources retrieved:**  ",
            _format_sources(resp.get("sources")),
            "",
            "**Images:**  ",
            _format_images(resp.get("images")),
            "",
            "**Grounding metadata:**  ",
            _format_grounding(resp.get("grounding")),
            "",
            _score_table(meta.get("scores"), None),
        ]

    parts.append("")
    parts.append("---")
    parts.append("")
    return "\n".join(parts)


def build_summary_table(rows: list[dict]) -> str:
    lines = [
        "| ID | Outcome | Sources | Images | Draft avg score |",
        "| -- | ------- | ------- | ------ | --------------- |",
    ]
    for item, meta in zip(rows, META):
        err = item.get("error")
        resp = item.get("response") or {}
        if err:
            outcome = "Error"
            src_n = "—"
            img_n = "—"
            avg = "N/A"
        else:
            ans = (resp.get("answer") or "").lower()
            if "keine information" in ans or "nicht beantworten" in ans or "enthält keine" in ans:
                outcome = "Abstained"
            else:
                outcome = "Answered"
            src_n = str(len(resp.get("sources") or []))
            img_n = str(len(resp.get("images") or []))
            sc = meta.get("scores")
            avg = f"{sum(sc[:6])/6:.1f}" if sc else "—"
        lines.append(f"| {meta['id']} | {outcome} | {src_n} | {img_n} | {avg} |")
    return "\n".join(lines)


def main() -> None:
    rows = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if len(rows) != len(META):
        raise SystemExit(f"Expected {len(META)} questions, got {len(rows)}")

    header = """## 9. Exploratory RAG results (Q&A)

**Source:** `german_eval_results.json` — professor question set (German), `POST /rag/ask`, OpenStax anatomy PDFs ingested.  
**Run date:** June 2026 (formative). **LLM at run time:** cloud Groq; **current repo default:** LM Studio local only.  
**Status:** Exploratory — use for thesis evolution narrative; rerun on frozen local stack for final claims.

### 9.0 Summary table

""" + build_summary_table(rows) + """

**Aggregate exploratory notes**

| Observation | Implication for final evaluation |
| ----------- | -------------------------------- |
| Weak retrieval on muscle/joint topics | Measure Recall@k and source hit rate per category |
| Correct “not in documents” refusals | Score boundary handling positively where appropriate |
| VOR question answered with figures | Good multimodal case for Section 2.6 |
| Shoulder talk used tangential neurology passages | Low grounding score despite fluent text |
| HTTP 500 on complex multi-part question | Reliability metric for production endpoint |
| 9 questions: 5 abstentions, 3 answered, 1 error | Report abstention rate separately from accuracy |

---

"""

    body = "".join(build_entry(item, meta) for item, meta in zip(rows, META))

    md = MD_PATH.read_text(encoding="utf-8")
    pattern = r"## 9\. Exploratory RAG results \(Q&A\).*?(?=## 10\. Final RAG evaluation workbook)"
    new_md, n = re.subn(pattern, header + body + "\n", md, count=1, flags=re.DOTALL)
    if n != 1:
        raise SystemExit("Could not find Section 9 boundary in evaluationThesis.md")
    MD_PATH.write_text(new_md, encoding="utf-8")
    print(f"Updated {MD_PATH} — Section 9 with {len(rows)} populated Q&A entries")


if __name__ == "__main__":
    main()
