# Backend-evidence alignment — manuscript correction report

**Branch:** `thesis/backend-evidence-alignment`
**Date:** 22 July 2026
**Scope:** Overleaf thesis prose/figures/appendix alignment to ThesisBackend runtime + raw eval SoT. No raw eval JSON modified. No new retrieval architecture implemented. Branch not merged.

---

## Final build status

| Build | Commands | Result |
| ----- | -------- | ------ |
| Full local | `pdflatex -interaction=nonstopmode main_full.tex` (×2) then `python scripts/refresh_fast_cache.py` | **Success** — no `!` LaTeX errors. `main_full.pdf` **123 pages**, 992 332 bytes. |
| Free-plan | `pdflatex -interaction=nonstopmode main.tex` after cache refresh | **Success** — no `!` LaTeX errors. `main.pdf` **125 pages**, 929 768 bytes. |

### Remaining warnings (non-fatal)

- Free-plan one-pass destination warnings (`name{table.caption.*} has been referenced but does not exist`) — expected with cached aux/ToC; body text compiles.
- pdfTeX papersize specials on some older rendered figure PDFs (`research_cycle`, `evolution_timeline`, `mcp_runtime_sequence`).
- Occasional “Infinite glue shrinkage found in box being split” on wide tables (pre-existing layout).
- MiKTeX may note pending update checks.

---

## File-by-file change log (manuscript)

| File | Change |
| ---- | ------ |
| `frontmatter/abstract_en.tex` | P1 = hybrid-preferred after `5089fcc`; historical `cb041d5`; no superiority; type caps; WK not enforced |
| `frontmatter/abstract_de.tex` | German equivalent |
| `chapters/01_introduction.tex` | RQ1/C2/C4 hybrid-preferred; `\systemname` introduced |
| `chapters/03_methodology_requirements.tex` | 10-step verified route; FR5; RQ map |
| `chapters/04_system_evolution_design_decisions.tex` | Dense→hybrid evolution; early top-3 historical; July type caps |
| `chapters/05_final_system_design_implementation.tex` | Active hybrid path; component map; inactive WK/post-gen only |
| `chapters/06_evaluation_methodology.tex` | P1 config; proxy catalogue; **M1 scale explained at first detailed occurrence** |
| `chapters/07_results_discussion.tex` | Hybrid-preferred results; P@1 0.907; distribution; **Not evaluated / Pending expert annotation** wording; RQ answers |
| `chapters/08_conclusion_future_work.tex` | RQ answers per evidence; no new numbers |
| `figures/dual_pipeline_architecture.tex` + PDF | Hybrid-preferred; type-capped context |
| `figures/rag_pipeline.tex` + PDF | Active hybrid stages |
| `figures/final_runtime_architecture.tex` + PDF | New active architecture diagram |
| `figures/rag_runtime_sequence.tex` + PDF | New ask-path sequence |
| `appendices/a_reproducibility.tex` | `cb041d5` / `5089fcc` / `d3a544d` / timestamp / mode-trace gap |
| `appendices/f_supervisor_traceability.tex` | Compact/type-dependent wording |
| `references.bib` / `references_manual.tex` | Completed `thakur2021beir` (arXiv DOI/URL) |
| `preamble.tex` | `\systemname` used via keywords + Ch1 |
| `metadata.tex` | Repository commit → audit HEAD `d3a544d…` |
| `cache/*_snapshot.tex` | Refreshed from full build |
| `scripts/render_figures.py` | Figure regeneration helper |
| `main_full.tex`, `main_bibtex.tex` | Present at project root for local/full workflows |

---

## Before / after claim matrix

| Claim | Before | After | Status |
| ----- | ------ | ----- | ------ |
| P1 retrieval | Dense-only; hybrid unwired | Hybrid-preferred after `5089fcc`; dense fallback | Corrected |
| Hybrid superiority | Risk of misreading | Explicitly not claimed | Integrity preserved |
| Hard top-3 in July P1 | Unexplained discrepancy | Historical only; July caps ~4–8; mean 5.16 | Corrected |
| Source distribution | ~5.2 | `{0:2,2:1,4:27,5:3,6:3,8:15}`; mean 5.16 | Verified |
| Duplicate source–page | — | 0 / 263 | Derived |
| Proxies P@3…MRR | 0.86/0.58/0.90/0.93 | Unchanged | Proxy verified |
| P@1 | Absent | 0.907 (n=43) | Provisional |
| WK blocking | Recorded false | Recorded; **not schema-enforced** | Corrected |
| Boundary 1/8 | Provisional | Provisional; not primary | Softened |
| Image 10/10 | Availability | Availability only | Unchanged integrity |
| MCP effectiveness | Empty | Empty / not evaluated | Unchanged |
| Human Acc/Comp/Rel | Blank / vague | **Not evaluated** / **Pending expert annotation** | Clarified |
| M1 2.56/5.56/8.89 | Unexplained scale | Explained as exploratory relative ranks; 1–5-per-criterion tradition; max not frozen with means | Clarified |
| `\systemname` | Unused | Used in Ch1 + PDF keywords | Resolved |
| `thakur2021beir` | Incomplete | DOI + arXiv URL | Resolved |

---

## Remaining evidence limitations

1. Per-request `retrieval_mode` / hybrid provenance not logged in P1 JSON
2. No matched dense / BM25 / hybrid ablation
3. No context-size 1/3/5 controlled experiment
4. WK flag not enforceable without schema+prompt change + rerun
5. No per-request latency percentiles
6. Expert passage/claim/citation/quotation/anatomy labels pending
7. Figure relevance not evaluated
8. MCP scored workbook empty
9. Optional retry of four infrastructure failures
10. Corpus PDF hashes / hardware / quantisation not archived with P1

---

## Integrity checks

- `eval/*.json` and `german_eval_*.json`: **not modified**
- No ThesisBackend retrieval-architecture code changes in this commit
- Negative findings retained
- Chapter 8 introduces no new metrics beyond Ch7 cross-references
- Contradictory dense-only/hybrid-unwired claims removed from abstract and Ch1–8 body (historical dense-only language retained only as evolution context)

---

## Packaging note

Clean Overleaf ZIP: `Chatbot_for_Anatomy_Evidence_Aligned_2026-07-22.zip` (see sibling manifest/checksum after packaging).
