#!/usr/bin/env python3
"""Build §9.1 professor metrics workbook tables in evaluationThesis.md."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from build_eval_section import (
    PROFESSOR_META,
    _outcome,
)
from eval_run_metadata import format_model_header, format_model_short, resolve_model_block

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
MD = REPO / "evaluationThesis.md"
CLOUD_JSON = REPO / "german_eval_results.json"
LOCAL_JSON = REPO / "german_eval_lmstudio_results.json"

SECTION_90_START = "## 9.0 Experiment runs and models"
SECTION_START = "## 9.1 Professor evaluation metrics workbook"
SECTION_END = "## 10."


def _cell(text: str | None, max_len: int = 100) -> str:
    if not text:
        return ""
    t = str(text).replace("\n", " ").replace("|", "\\|").strip()
    if len(t) > max_len:
        return t[: max_len - 1] + "…"
    return t


def _system_answer(item: dict) -> str:
    err = item.get("error")
    if err:
        return _cell(err, 100)
    resp = item.get("response") or {}
    return _cell(resp.get("answer"), 100)


def _metrics_row(qid: str, question: str, gold: str, item: dict, model: str) -> str:
    q = _cell(question, 90)
    g = _cell(gold, 80)
    ans = _system_answer(item)
    return f"| {qid} | {q} | {g} | {ans} | {model} | | | | | | | | | |"


def build_metrics_table(rows: list[dict], id_prefix: str, model: str) -> str:
    if len(rows) != len(PROFESSOR_META):
        raise ValueError(f"Expected {len(PROFESSOR_META)} rows, got {len(rows)}")
    header = (
        "| ID | Question | Expected key points | System answer | Model | "
        "P@3 | R@3 | nDCG@3 | Acc | Comp | Rel | Grnd | Cit | Abst |\n"
        "| -- | -------- | ------------------- | ------------- | ----- | "
        "--- | --- | ------ | --- | ---- | --- | ---- | --- | ---- |"
    )
    body = []
    for i, (item, (_, gold)) in enumerate(zip(rows, PROFESSOR_META), 1):
        qid = f"{id_prefix}{i:02d}"
        body.append(_metrics_row(qid, item["question"], gold, item, model))
    return header + "\n" + "\n".join(body)


def build_section(cloud: list[dict], local: list[dict]) -> str:
    cloud_cfg = resolve_model_block("cloud_professor_de")
    local_cfg = resolve_model_block("local_professor_de")
    cloud_model = format_model_short(cloud_cfg)
    local_model = format_model_short(local_cfg)
    local_summary = []
    for i, item in enumerate(local, 1):
        out = _outcome((item.get("response") or {}).get("answer"), item.get("error"))
        local_summary.append(f"LM-R{i:02d}: {out}")
    cloud_summary = []
    for i, item in enumerate(cloud, 1):
        out = _outcome((item.get("response") or {}).get("answer"), item.get("error"))
        cloud_summary.append(f"EXP-R{i:02d}: {out}")

    return f"""{SECTION_START}

**Status:** System answers populated from `{LOCAL_JSON.name}` (§11) and `{CLOUD_JSON.name}` (§10).  
**Retrieval metrics** (P@3, R@3, nDCG@3) require gold relevant passages — fill after manual relevance judging.  
**Human rubric** (Acc–Abst): score 1–5 per §6 (**Acc**uracy · **Comp**leteness · **Rel**evance · **Grnd**ing · **Cit**ation · **Abst**ention/boundary).

**Local outcomes:** {' · '.join(local_summary)}  
**Cloud outcomes:** {' · '.join(cloud_summary)}

### 9.1.1 Local LM Studio run (primary thesis experiment)

{format_model_header(local_cfg)}

{build_metrics_table(local, "LM-R", local_model)}

### 9.1.2 Cloud exploratory run (historical comparison)

{format_model_header(cloud_cfg)}

{build_metrics_table(cloud, "EXP-R", cloud_model)}

---

"""


def main() -> None:
    from eval_run_metadata import build_experiment_registry_table

    cloud = json.loads(CLOUD_JSON.read_text(encoding="utf-8"))
    local = json.loads(LOCAL_JSON.read_text(encoding="utf-8"))
    registry = build_experiment_registry_table()
    section = registry + build_section(cloud, local)

    md = MD.read_text(encoding="utf-8")
    start = md.find(SECTION_90_START)
    if start < 0:
        start = md.find(SECTION_START)
    end = md.find(SECTION_END)
    if start >= 0 and end > start:
        md = md[:start] + section + md[end:]
    else:
        anchor = md.find("\n---\n\n## 10.")
        if anchor < 0:
            raise SystemExit("Could not find insertion point before §10")
        md = md[: anchor + 1] + "\n" + section + md[anchor + 1 :]

    # Fix duplicated run-commands fence in §9 if present
    md = re.sub(
        r"```powershell\npython scripts/refresh_eval_md\.py\n```\n```\n",
        "```powershell\npython scripts/refresh_eval_md.py\n```\n",
        md,
    )

    MD.write_text(md, encoding="utf-8")
    print(f"Updated {MD} — §9.1 professor metrics workbook (9 + 9 rows)")


if __name__ == "__main__":
    main()
