# Full-Thesis Humanisation Report

## Purpose and integrity boundary

The revision addressed the stylistic risks identified in the supplied AI-writing assessment, especially the repeated ten-part design template in Chapter 4, the protocol-like wording in Chapter 6, and the polished restatement patterns in Chapters 1 and 8.

This work does **not** claim that an AI detector will return 5%, or any other percentage. Detector outputs are model-, version-, threshold-, language-, and document-dependent. The defensible outcome is a reduction in observable stylistic risk through clearer author-owned reasoning, varied paragraph structures, concrete project evidence, and removal of repeated templates. The external detector score remains **N/A until a named institutional tool is run**.

## Scope completed

The following files received a full prose revision:

- `frontmatter/abstract_en.tex`
- `frontmatter/abstract_de.tex`
- all eight files under `chapters/`

Appendix E was intentionally retained. It already provides a transparent account of AI-assisted brainstorming, language review, LaTeX revision, code explanation, and consistency checking, while preserving the author's responsibility for evidence, interpretation, and submitted wording.

## Main changes

### Chapter 1 - Introduction

- Replaced a sequence of polished contrasts with a clearer research journey.
- Reduced repeated warnings while preserving the scope boundaries.
- Connected the motivation more directly to the project's observed problems.

### Chapter 2 - Background and Related Work

- Compressed textbook-style definitions and repeated limitation paragraphs.
- Increased comparison and synthesis between sources.
- Retained all substantive literature areas and verified citation keys.

### Chapter 3 - Methodology and Requirements

- Recast the methodology as decisions taken during the project rather than a generic framework description.
- Explained why evidence units and denominators differ between RAG and MCP.
- Preserved the requirements and traceability tables.

### Chapter 4 - System Evolution and Design Decisions

- Removed all 14 repeated `description` templates.
- Rewrote the chapter as evidence-led engineering case narratives.
- Preserved the chronology, code paths, literature support, failures, corrections, and decision matrix.
- This was the largest reduction in the supplied detector-risk pattern.

### Chapter 5 - Final System Design and Implementation

- Reduced inventory-like prose and connected code facts to runtime consequences.
- Preserved route names, schemas, hashes, model details, diagrams, and code paths.
- Kept the distinction between code presence, runtime wiring, and measured execution.

### Chapter 6 - Evaluation Methodology

- Replaced protocol-template language with an account of the procedures actually used.
- Added reasoning for denominators, proxy labels, the 0.38 threshold, and separation of runs.
- Kept planned experiments explicitly separate from completed methods.

### Chapter 7 - Results and Discussion

- Reorganised the chapter around preserved evidence and concrete failure cases.
- Retained every reported denominator and numerical result.
- Added author-owned interpretation without converting missing experiments into claims.
- Reduced repeated cautionary formulations by integrating limitations into the result discussion.

### Chapter 8 - Conclusion and Future Work

- Removed repeated Chapter 7 discussion.
- Answered the four research questions directly.
- Shortened the chapter by 6.9% while preserving the contribution table, limitations, and prioritised future work.

## Structural before-and-after indicators

These metrics are conservative scripts, not AI detectors or authorship tests.

| Indicator | Before | After | Interpretation |
|---|---:|---:|---|
| Estimated body words, Chapters 1-8 | 23,779 | 23,191 | 97.5% of source length |
| Chapter 4 repeated `description` environments | 14 | 0 | Main template signal removed |
| Mean sentence length, combined script | 21.29 | 19.56 | Less uniformly long prose |
| Sentences over 40 words | 61 | 38 | Dense sentence load reduced |
| Sentences under 8 words | 62 | 99 | More cadence variation |
| Sentence-length coefficient of variation | 1.132 | 1.198 | Greater variation; tables affect this proxy |
| Repeated full sentences | 0 | 0 | No new direct repetition introduced |
| Phrase `does not guarantee` | 10 | 0 | Recurrent caution formula removed |
| Phrase `does not establish` | 6 | 1 | Recurrent caution formula reduced |
| Phrase `is not evidence of` | 2 | 0 | Recurrent caution formula removed |

### Length control by chapter

| Chapter | Before | After | Ratio | Status |
|---|---:|---:|---:|---|
| 1 | 2,096 | 2,130 | 1.016 | Near-source length |
| 2 | 4,425 | 3,668 | 0.829 | Compressed; repeated textbook-style material removed |
| 3 | 2,582 | 2,598 | 1.006 | Near-source length |
| 4 | 3,470 | 3,815 | 1.099 | Expanded within limit; labels converted into connected reasoning |
| 5 | 3,643 | 3,499 | 0.960 | Near-source length |
| 6 | 1,820 | 1,939 | 1.065 | Slight expansion for methodological reasoning |
| 7 | 4,368 | 4,262 | 0.976 | Near-source length |
| 8 | 1,375 | 1,280 | 0.931 | Near-source length and less repetitive |

## Qualitative before-and-after assessment

| Dimension | Before revision | After revision | Basis and limitation |
|---|---|---|---|
| Human academic voice | Credible but strongly systematised | More reflective, specific, and varied | Expert stylistic assessment, not proof of authorship |
| AI-writing stylistic risk | Medium overall; high in Chapters 4 and 6 in the supplied report | Low-to-medium qualitative risk | No detector result or guaranteed percentage |
| Project specificity | Strong in Chapters 5 and 7 | Strong throughout all chapters | Code paths, failures, decisions, and evidence retained |
| Structural repetition | High in Chapter 4 | Low | Fourteen repeated templates removed |
| Methodological reasoning | Correct but protocol-like | More explicit about choices and constraints | Chapter 6 rewrite |
| Internal repetition | Low-to-moderate conceptual restatement | Low | Chapter 8 compressed; caution phrases reduced |
| Similarity/plagiarism risk | Low in the supplied originality audit | No increase identified | External source matching was not repeated in this revision |
| Citation and reference integrity | Resolved in corrected baseline | Preserved | Compilation produced no undefined citations |
| External AI score | N/A | N/A | Requires a named institutional report |

## Build verification

The full local build and the timeout-safe Overleaf build were both compiled after the revision.

- Full local build: 121 pages
- Timeout-safe `main.tex`: 123 pages
- Undefined citations: 0
- Undefined cross-references: 0
- Duplicate PDF destinations: 0
- Overfull boxes: 0
- Visible `??` markers: 0
- Visible draft or evidence placeholders: 0
- Rendered pages visually checked: title page, abstract, Chapters 4, 6, 7, 8, and Appendix E

## Author review still required

Before submission, the author should:

1. read the complete revised thesis and confirm that first-person observations in Chapter 7 accurately reflect the work performed;
2. confirm the official faculty name, submission date, supervisor titles, and repository snapshot on the title page;
3. confirm that Appendix E matches the university's current disclosure requirements;
4. run the university's normal similarity and AI-writing report, if required, and inspect individual highlighted passages rather than relying on the aggregate score;
5. retain source notes, raw evaluation files, and the repository snapshot as evidence of author responsibility.

The project was revised for clarity and credible academic ownership, not to conceal disclosed AI assistance or manipulate a detector.
