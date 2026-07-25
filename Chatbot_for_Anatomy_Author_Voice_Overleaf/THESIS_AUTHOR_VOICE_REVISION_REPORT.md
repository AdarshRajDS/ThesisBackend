# Full-Thesis Author-Voice Revision Report

## Scope

Target: the timeout-safe Overleaf source corresponding to the 123-page humanised thesis.

The English and German abstracts and every prose paragraph in Chapters 1-8 were reviewed. The revision focused on author-owned academic reasoning, sentence rhythm, paragraph structure, project specificity, and removal of repeated contrast/caution templates. Numerical results, citations, code paths, labels, tables, figures, research boundaries, and the AI-assistance disclosure were preserved.

This work does not establish an AI-authorship percentage and cannot guarantee a particular Turnitin or other detector result. The purpose was to improve the manuscript ethically, not to conceal assistance or manipulate a detector.

## Chapter-by-chapter work

- **Chapter 1:** rewritten throughout. The introduction now begins from the actual learning and trust problem, uses less symmetrical contrast, and moves more directly from motivation to the dual-pipeline decision.
- **Chapter 2:** rewritten throughout. Literature is synthesised around the thesis decisions instead of following a repeated definition-benefit-limitation pattern.
- **Chapter 3:** revised paragraph by paragraph. Design-science reasoning, requirements derivation, constraints, and reproducibility are expressed as decisions made in this project rather than as generic methodology prose.
- **Chapter 4:** revised paragraph by paragraph. The earlier checklist-like decision pattern was removed; the chapter now follows the chronology of observed failures, evidence, correction, and unresolved work without identical subsection templates.
- **Chapter 5:** revised paragraph by paragraph. Code inspection and runtime discrepancies are explained in a more direct engineering voice while retaining exact repository paths and implementation details.
- **Chapter 6:** rewritten throughout. The chapter now explains why each run, denominator, exclusion, proxy, and limitation was used, including the uncalibrated 0.38 threshold and incomplete MCP evaluation.
- **Chapter 7:** revised paragraph by paragraph. Results are interpreted as an imperfect research record, with failure cases and missing comparisons integrated into the argument rather than mechanically balanced against positive findings.
- **Chapter 8:** rewritten and compressed. Research questions are answered directly, Chapter 7 is not restated at length, and future work follows from the missing evidence.
- **Abstracts:** both language versions were rewritten for a more natural summary of the actual system and evaluation.
- **Appendix E:** retained unchanged so that AI assistance remains transparently disclosed.

## Structural comparison

The comparison scripts are conservative proxies. They do not detect AI authorship or plagiarism.

| Chapter | Original words | Revised words | Ratio |
|---|---:|---:|---:|
| 1 | 2,130 | 2,079 | 0.976 |
| 2 | 3,668 | 3,545 | 0.966 |
| 3 | 2,598 | 2,560 | 0.985 |
| 4 | 3,815 | 3,473 | 0.910 |
| 5 | 3,499 | 3,298 | 0.943 |
| 6 | 1,939 | 2,004 | 1.034 |
| 7 | 4,262 | 3,748 | 0.879 |
| 8 | 1,280 | 1,202 | 0.939 |
| **Total** | **23,191** | **21,909** | **0.945** |

The reduction comes mainly from duplicated qualifications, predictable transitions, and repeated explanations of the same evidence boundary. No content was added to inflate the manuscript.

Selected whole-thesis phrase changes:

- `does not`: 29 -> 18
- `therefore`: 54 -> 45
- `should not be interpreted as`: 1 -> 0
- `in conclusion`: 1 -> 0
- stock phrases such as `plays a crucial role`, `it is important to note`, `moreover`, and `furthermore`: 0

No revised chapter contains repeated full sentences. No repeated sentence-opener signal was introduced in Chapters 1, 2, 4, 5, 6, 7, or 8. The few repeated eight-word sequences reported in Chapters 2 and 3 arise from formulas, tables, headings, or unavoidable technical wording and require contextual rather than detector-based interpretation.

## Integrity and evidence controls

- No result value was changed.
- No missing experiment was invented.
- Dense retrieval remains distinguished from the unconnected hybrid branch.
- Figure availability remains separate from figure relevance.
- MCP implementation evidence remains separate from uncompleted runtime evaluation.
- The world-knowledge leakage, request failures, anatomy error, missing expert annotations, and reproducibility gaps remain visible.
- Existing citation keys and cross-references were preserved.
- The AI-assistance disclosure remains in the project.

## LaTeX and PDF verification

The cache was refreshed from a local multi-pass build and the timeout-safe project was then compiled from `main.tex`.

- Fast pdfLaTeX build: approximately 1.9 seconds locally
- Output: 121 pages
- Undefined citations: 0
- Undefined cross-references: 0
- Overfull boxes: 0
- Visible draft/evidence placeholders: 0
- Active Overleaf root document: `main.tex`
- Visual render check: 121 pages rendered; chapter openings, contents pages, tables, figures, bibliography, and appendices were inspected for clipping and layout defects

## Defensible final interpretation

The revised thesis has a more specific and varied authorial voice and substantially fewer formulaic signals than the uploaded humanised version. It is reasonable to describe the remaining stylistic risk as low to low-medium on an expert qualitative review. A numerical AI percentage remains unavailable and cannot be guaranteed by rewriting. The author should still read the complete thesis, confirm that every first-person judgement reflects his own reasoning, and make any personal wording changes before submission.
