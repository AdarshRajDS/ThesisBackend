#!/usr/bin/env python3
"""Build a populated Q&A section in evaluationThesis.md from a JSON eval run."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PROFESSOR_META = [
    ("Complex / multi-step", "Peroneus longus/brevis, tibialis anterior/posterior, gastrocnemius/soleus, grouped by movement directions."),
    ("Complex + figure request", "Flexor digitorum superficialis/profundus, flexor pollicis longus, lumbricals; median/ulnar innervation; 2 figures."),
    ("Direct factual / clinical anatomy", "Humeral head high-riding: rotator cuff weakness, capsular tightness; subacromial impingement."),
    ("Direct factual", "Iliopsoas (iliacus + psoas major) as primary hip flexor."),
    ("Direct factual + implicit figure", "Vestibular nuclei → ocular motor nuclei; stabilizes retinal image during head movement."),
    ("Complex / boundary", "Semicircular canals: horizontal + vertical planes; VOR not limited to horizontal."),
    ("Direct factual", "Extraocular muscle ↔ semicircular canal pairings."),
    ("Direct factual", "Heart pump function, chambers, systemic/pulmonary circulation."),
    ("Complex / synthesis", "Shoulder girdle, abduction/elevation, scapulohumeral rhythm, relevant muscles."),
]

PROFESSOR_QUESTIONS = [
    "Bitte stelle mir die wichtigsten Muskeln für die Bewegung der Sprunggelenke zusammen und sortiere diese bitte nach Bewegungsrichtungen.",
    "Bitte stelle mir eine Übersicht über die wichtigen Muskeln zusammen, welche benötigt werden, um eine Faust zu schließen. Hierbei sollte die Innervation berücksichtigt werden. Bitte zeige mir dazu auch zwei didaktisch gute Bilder.",
    "Welche Faktoren begünstigen einen Hochstand des Humeruskopfes und damit eine Enge unter dem Schulterdach?",
    "Welcher Muskel ist der wichtigste Hüftbeuger beim Menschen?",
    "Kannst Du mir kurz erklären, wie der Vestibulo-Okuläre-Reflex funktioniert?",
    "Gibt es den Vestibulookulären Reflex nur in der Horizontalen?",
    "Welche Augenmuskeln wirken denn mit welchen Borgengängen zusammen?",
    "Bitte erkläre mir die Funktion des Herzens.",
    "Bitte erstelle mir ein Kurzreferat für 3 Minuten für den Schultergürtel wo es um Bewegungen des Armes geht und Dinge wie Abduktion und Elevation.",
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
        m = re.search(r"/page_(\d+)/", str(url))
        page_hint = f" (page {m.group(1)})" if m else ""
        lines.append(f"{i}. `{url}`{page_hint}")
    return "\n".join(lines)


def _format_grounding(g: dict | None) -> str:
    if not g:
        return "*Not returned*"
    return "\n".join(f"- **{k}:** {v}" for k, v in g.items())


def _outcome(answer: str | None, error: str | None) -> str:
    if error:
        return "Error"
    text = (answer or "").lower()
    abstain_markers = (
        "keine information",
        "nicht beantworten",
        "enthält keine",
        "not found in provided",
        "keine ausreichend",
        "keine relevanten informationen",
    )
    world_knowledge_markers = (
        "allgemeine anatomische",
        "allgemeinen anatomischen",
        "general anatomical",
        "basierend auf allgemeinen",
    )
    if any(m in text for m in world_knowledge_markers):
        return "Answered (world knowledge)"
    if any(m in text for m in abstain_markers):
        return "Abstained"
    return "Answered"


def build_cloud_vs_local_table(cloud: list[dict], local: list[dict]) -> str:
    lines = [
        "### 11.0.1 Cloud vs local comparison (same professor set)",
        "",
        "| ID | Cloud run (§10) | LM Studio (§11) | Thesis note |",
        "| -- | --------------- | --------------- | ----------- |",
    ]
    notes = {
        1: "Local answered with world knowledge; cloud abstained",
        2: "Both failed (500)",
        3: "Local world-knowledge fill; cloud abstained",
        4: "Local grounded answer (iliopsoas); cloud abstained",
        5: "Both answered VOR; local added images",
        6: "Both answered; local added images",
        7: "Local world knowledge; cloud partial",
        8: "Local corpus-grounded heart; cloud abstained",
        9: "Cloud off-topic answer; local timeout",
    }
    for i, (c, l) in enumerate(zip(cloud, local), 1):
        qid = f"R{i:02d}".replace("R", "EXP-R")  # fix
        qid = f"EXP-R{i:02d}"
        c_out = _outcome((c.get("response") or {}).get("answer"), c.get("error"))
        l_out = _outcome((l.get("response") or {}).get("answer"), l.get("error"))
        lines.append(f"| {qid} | {c_out} | {l_out} | {notes.get(i, '')} |")
    lines.extend(["", "---", ""])
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


def build_summary_table(rows: list[dict], id_prefix: str, model: str = "") -> str:
    model_cell = model or "—"
    header = (
        "| ID | Outcome | Model | Sources | Images | Request time |\n"
        "| -- | ------- | ----- | ------- | ------ | ------------ |\n"
    )
    body = []
    for i, item in enumerate(rows, 1):
        qid = f"{id_prefix}{i:02d}"
        err = item.get("error")
        resp = item.get("response") or {}
        lat = _fmt_elapsed_ms(item.get("elapsed_ms")) or "—"
        if err:
            body.append(f"| {qid} | Error | {model_cell} | — | — | {lat} |")
        else:
            ans = resp.get("answer")
            body.append(
                f"| {qid} | {_outcome(ans, None)} | {model_cell} | "
                f"{len(resp.get('sources') or [])} | {len(resp.get('images') or [])} | {lat} |"
            )
    return header + "\n".join(body)


def _sanitize_answer(text: str) -> str:
    """Prevent embedded markdown H2 headers from breaking evaluationThesis.md structure."""
    if not text:
        return text
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            lines.append("#### " + line[3:])
        else:
            lines.append(line)
    return "\n".join(lines)


def build_entry(item: dict, qid: str, category: str, gold: str, model: str = "") -> str:
    q = item["question"]
    err = item.get("error")
    resp = item.get("response") or {}
    title = q[:70] + ("…" if len(q) > 70 else "")

    parts = [
        f"### {qid} — {title}",
        "",
        "| Field | Content |",
        "| ----- | ------- |",
        f"| **ID** | {qid} |",
        f"| **Category** | {category} |",
        f"| **Language** | German |",
        f"| **Model** | {model or 'n/a'} |",
        f"| **Request time** | {_fmt_elapsed_ms(item.get('elapsed_ms')) or 'n/a'} |",
        "",
        "**Question:**  ",
        q,
        "",
        "**Expected key points (gold):**  ",
        gold,
        "",
    ]

    if err:
        parts += ["**System answer:**  ", f"`{err}`", ""]
    else:
        parts += [
            "**System answer:**  ",
            _sanitize_answer((resp.get("answer") or "").strip()) or "*Empty response*",
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
        ]

    parts += ["---", ""]
    return "\n".join(parts)


def build_question_list() -> str:
    lines = [
        "## 9. Professor evaluation question set (complete list)",
        "",
        "Nine German anatomy questions used by the professor and repeated across evaluation runs.",
        "",
        "| # | ID (exploratory) | ID (LM Studio) | Category | Question |",
        "| -: | ---------------- | -------------- | -------- | -------- |",
    ]
    for i, (q, (cat, _)) in enumerate(zip(PROFESSOR_QUESTIONS, PROFESSOR_META), 1):
        q_cell = q.replace("|", "\\|")
        if len(q_cell) > 100:
            q_cell = q_cell[:100] + "…"
        lines.append(
            f"| {i} | EXP-R{i:02d} | LM-R{i:02d} | {cat.split('/')[0].strip()} | {q_cell} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def build_section_header(
    section_num: str,
    title: str,
    *,
    json_name: str,
    run_note: str,
    model_block: str,
    id_prefix: str,
    rows: list[dict],
    model_short: str,
    comparison_block: str = "",
) -> str:
    return f"""## {section_num}. {title}

**Source file:** `{json_name}`  
{run_note}

{model_block}

### {section_num}.0 Summary

{build_summary_table(rows, id_prefix, model_short)}

{comparison_block}---

"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, required=True)
    ap.add_argument("--section-num", default="10")
    ap.add_argument("--section-title", default="Local LM Studio experiment (Q&A)")
    ap.add_argument("--id-prefix", default="LM-R")
    ap.add_argument("--run-note", default="")
    ap.add_argument("--replace-section", help="Regex of section header to replace through next ## N+1")
    ap.add_argument("--run-key", default="", help="Key in eval/experiment_runs.json for model metadata")
    ap.add_argument("--cloud-json", type=Path, default=REPO / "german_eval_results.json")
    ap.add_argument("--md", type=Path, default=REPO / "evaluationThesis.md")
    args = ap.parse_args()

    rows = json.loads(args.json.read_text(encoding="utf-8"))
    if len(rows) != len(PROFESSOR_META):
        raise SystemExit(f"Expected {len(PROFESSOR_META)} questions, got {len(rows)}")

    run_note = args.run_note or f"**Endpoint:** `POST /rag/ask` · **Status:** populated from `{args.json.name}`"
    model_block = ""
    model_short = "—"
    if args.run_key:
        sys.path.insert(0, str(REPO / "scripts"))
        from eval_run_metadata import format_model_header, format_model_short, resolve_model_block

        cfg = resolve_model_block(args.run_key)
        model_block = format_model_header(cfg)
        model_short = format_model_short(cfg)

    comparison = ""
    if args.section_num == "11" and args.cloud_json.exists():
        cloud_rows = json.loads(args.cloud_json.read_text(encoding="utf-8"))
        if len(cloud_rows) == len(rows):
            comparison = build_cloud_vs_local_table(cloud_rows, rows)
    body = build_section_header(
        args.section_num,
        args.section_title,
        json_name=args.json.name,
        run_note=run_note,
        model_block=model_block,
        id_prefix=args.id_prefix,
        rows=rows,
        model_short=model_short,
        comparison_block=comparison,
    )
    for i, (item, (cat, gold)) in enumerate(zip(rows, PROFESSOR_META), 1):
        body += build_entry(item, f"{args.id_prefix}{i:02d}", cat, gold, model_short)

    md = args.md.read_text(encoding="utf-8")

    if args.replace_section:
        pattern = args.replace_section
    else:
        # Insert before "## 10. Final RAG" or similar workbook
        pattern = r"(## 12\. Final RAG evaluation workbook)"

    if args.replace_section or re.search(rf"## {re.escape(args.section_num)}\.", md):
        # Replace existing section with same number
        sec_pattern = rf"## {re.escape(args.section_num)}\..*?(?=\n## {int(args.section_num) + 1}\.|\n## Appendix|\Z)"
        new_md, n = re.subn(sec_pattern, body.rstrip() + "\n\n", md, count=1, flags=re.DOTALL)
        if n != 1:
            raise SystemExit(f"Could not replace section {args.section_num}")
    else:
        new_md, n = re.subn(
            r"(## 10\. Final RAG evaluation workbook)",
            body + r"\1",
            md,
            count=1,
        )
        if n != 1:
            raise SystemExit("Could not insert before section 10 workbook")

    # Ensure question list exists once at section 9
    if "## 9. Professor evaluation question set" not in new_md:
        new_md = re.sub(
            r"## 9\. Exploratory RAG results",
            build_question_list() + "## 9. Exploratory RAG results",
            new_md,
            count=1,
        )

    args.md.write_text(new_md, encoding="utf-8")
    print(f"Updated {args.md} — section {args.section_num} ({len(rows)} entries)")


if __name__ == "__main__":
    main()
