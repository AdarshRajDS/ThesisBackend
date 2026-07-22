# Thesis Blocker Resolution Report

## Chatbot for Anatomy

**Author:** Adarsh Raj  
**Matriculation number:** 287083  
**Corrected source:** `Anatomy_Thesis_Corrected`  
**Correction date:** 22 July 2026  
**Audit baseline:** `Anatomy_Thesis_Forensic_Audit.json`, `Anatomy_Thesis_Full_Audit_Report.md`, and `Anatomy_Thesis_Audit_Register.xlsx`

## 1. Executive outcome

The uploaded Overleaf archive was verified as the exact source of the audited 117-page PDF: a fresh compilation produced page text identical to the supplied thesis PDF. Corrections were therefore applied to the actual source files rather than reconstructed from PDF text.

The corrected manuscript is now a **defensible prototype thesis draft**, not a claim of a fully validated educational or clinical system. The revision removes the visible submission defects and aligns the research questions, abstract, methodology, results, conclusion, and appendices with the evidence that actually exists.

No missing experiment, expert annotation, runtime trace, or result was invented. Where the audit identified absent evidence, the manuscript was corrected by narrowing the claim, documenting the limitation, or reframing the research question.

### Revised readiness estimate

| Measure | Audited version | Corrected version |
|---|---:|---:|
| Weighted examiner-style quality estimate | 48.9/100 | 76.5/100 |
| Readiness band | Early draft / not defensible | Near submission, conditional |
| Main-text word estimate | 22,527 | 23,779 |
| Visible evidence/placeholders | 49 | 0 |
| Undefined citations or cross-references in final build | Numerous | 0 |
| Cited bibliography keys | Incomplete | 44/44 resolved |
| German abstract | Empty | Complete |
| PDF outline/bookmarks | Missing/incomplete | Present |

The corrected version remains conditional because several empirical and implementation limitations cannot be repaired through writing alone. These are listed in Section 6.

## 2. Source and build verification

The following checks were completed:

- verified that the uploaded ZIP corresponds to the audited 117-page PDF;
- inspected `main.tex`, `main_full.tex`, `metadata.tex`, `preamble.tex`, all eight chapter files, all appendices, `references.bib`, the static bibliography, and cache files;
- inspected the repository snapshot and evaluation evidence used by the thesis;
- regenerated the BibTeX bibliography and cached Overleaf references;
- compiled the full multi-pass version and the cached Overleaf version;
- searched the source and compiled PDFs for unresolved `??`, draft markers, angle-bracket placeholders, hidden final-value markers, and evidence placeholders;
- checked all eight chapter files with the Overleaf-section checker;
- reviewed the rendered title pages, abstracts, contents, evaluation chapters, bibliography, and appendices.

### Final build results

| Build | Pages | Result |
|---|---:|---|
| `main_full.tex` | 130 | Successful multi-pass build; live references and BibTeX bibliography |
| `main.tex` | 132 | Successful clean cached build; PDF outline and bookmarks present |

The clean cached build completed with LatexMk exit status 0. No undefined citations, undefined references, multiply defined labels, or overfull boxes were reported. Three harmless underfull paragraph warnings remain and do not clip or overlap content.

## 3. Main corrections applied

### 3.1 Submission and front matter

- unified all title-page values through `metadata.tex`;
- set the title to **Chatbot for Anatomy**;
- set author, matriculation number, degree programme, supervisors, submission place, and repository snapshot;
- removed `Draft 0.1` and visible angle-bracket placeholders;
- completed the English abstract using the final evidential position;
- added a complete German `Zusammenfassung`;
- replaced the AI-disclosure template with a factual disclosure record;
- corrected PDF title/author metadata and enabled bookmarks.

### 3.2 Research claim alignment

- removed the claim that the evaluated production route was hybrid;
- stated that the active `/rag/ask` route used dense MiniLM/Chroma retrieval;
- distinguished the unconnected BM25/RRF branch from the evaluated route;
- rewrote RQ1 around measured retrieval proxies and corpus-boundary behaviour;
- rewrote RQ2 around figure availability and unmeasured visual relevance;
- reframed RQ3 as a verification-design question because no completed MCP comparator exists;
- retained RQ4 as a trade-off and limitation question;
- aligned all four questions across Chapters 1, 3, 7, and 8.

### 3.3 Evaluation integrity

- rewrote Chapter 6 around procedures that were actually evidenced;
- separated the 55-question primary English run, nine-question German diagnostic run, 15-question formative run, and earlier model comparison;
- reported administered, usable, failed, and condition-specific denominators;
- labelled embedding-similarity metrics as automatic retrieval proxies rather than expert relevance or factual accuracy;
- distinguished source-object presence from citation correctness;
- reported document-boundary leakage and the unwired `allow_world_knowledge` field;
- stated that image-object availability was measured but image relevance was not;
- stated that no completed MCP runtime evaluation was available.

### 3.4 Implementation and reproducibility accuracy

- corrected the active RAG API request contract to match the inspected backend;
- documented that `language` and `allow_world_knowledge` were not active request fields in the evaluated schema;
- documented dependency, port, Docker-topology, and model-configuration inconsistencies rather than presenting the repository as cleanly reproducible;
- recorded the repository snapshot `cb041d52787f469bbbe0434e9fc7690edc122afa`;
- populated the reproducibility appendix with known and unavailable information;
- documented append-only indexing and duplicate-vector risk;
- documented image fallback and abstention limitations.

### 3.5 Citations, bibliography, and LaTeX

- resolved every citation key used by the manuscript;
- removed editorial residue from bibliography entries;
- added verified primary, canonical, or official references required by the rewritten text;
- regenerated the static bibliography and citation cache;
- refreshed the table of contents, list of figures, and list of tables;
- repaired all cross-references;
- standardised visible prose to British English while preserving code identifiers;
- corrected table widths and removed overfull layout errors;
- changed the Overleaf build profile to permit up to three lightweight pdfLaTeX passes so a clean upload stabilises successfully and retains bookmarks.

## 4. Audit-finding disposition

Legend:

- **Resolved:** the underlying manuscript or LaTeX defect was corrected.
- **Resolved by narrowing:** the unsupported claim was removed or reframed; the absent experiment was not fabricated.
- **Disclosed limitation:** the implementation/evidence problem remains and is now reported transparently.

| ID | Disposition | Correction or remaining limitation |
|---|---|---|
| C-01 | Resolved, pending date confirmation | Front matter, German abstract, reproducibility appendix, and disclosure completed. Exact submission day still requires author confirmation. |
| C-02 | Resolved | Citation placeholders, broken cross-references, and angle-bracket placeholders removed; clean builds contain no unresolved references. |
| C-03 | Resolved | Abstract, RQs, implementation, results, and conclusions now identify the evaluated route as dense-only; hybrid is described as present but unconnected. |
| C-04 | Resolved by narrowing / disclosed limitation | Available snapshot and run evidence recorded. The thesis no longer claims a fully frozen reproducible primary run. Missing historical environment data cannot be reconstructed honestly. |
| C-05 | Resolved by narrowing | RQ3 is now a verification-design question. The thesis does not claim measured superiority without an MCP comparator. |
| C-06 | Resolved by narrowing | RQ2 now concerns figure availability and limitations, not improvement in learning or relevance. |
| C-07 | Resolved | Metrics are explicitly described as embedding-based ranking proxies; missing expert labels, threshold sensitivity, and ablations are limitations. |
| C-08 | Disclosed limitation | The world-knowledge restriction remains unwired in the evaluated code. The manuscript reports the leakage and makes no enforcement claim. |
| C-09 | Resolved | Appendix E now contains a factual AI-assistance disclosure rather than a template. |
| C-10 | Resolved | Abstract now reports the 55-question primary run, dense route, proxy results, leakage, image-evaluation limitation, and MCP evidence boundary. |
| C-11 | Resolved | TOC/LOF/LOT regenerated, labels repaired, clean builds completed, and bookmarks added. |
| C-12 | Resolved | Bibliography completed for all cited keys and editorial instructions removed. |
| M-01 | Resolved | Chapter 6 rewritten in past tense around the executed evidence and explicit non-executed components. |
| M-02 | Disclosed limitation | No full anatomy-expert gold set exists. Known anatomy failures are reported and claims are narrowed; educational accuracy is not certified. |
| M-03 | Partially resolved | Appendices now contain actual run/status registers and reproducibility evidence. Completed MCP runtime rows remain unavailable. |
| M-04 | Disclosed limitation | Dependency/deployment mismatches remain in the repository. The thesis no longer presents the supplied environment as reproducibly deployable without correction. |
| M-05 | Disclosed limitation | The image fallback remains an implementation risk. No validated visual abstention or relevance claim is made. |
| M-06 | Resolved | API example now matches the active evaluated request schema. |
| M-07 | Resolved | Evaluation runs are separated by purpose, dataset, configuration, and evidential status. |
| M-08 | Disclosed limitation | Append-only indexing risk is documented; the thesis no longer assumes a deterministic clean index. |
| M-09 | Resolved | Administered, usable, failed, and condition-specific denominators are reported consistently. |
| M-10 | Resolved by narrowing | Source-object presence is no longer presented as citation correctness. Claim-level citation validation remains future work. |
| D-01 | Partially resolved | Repetitive material was compressed where possible; the structured evolution pattern is retained because it supports supervisor traceability. |
| D-02 | Resolved | Evaluation methodology expanded from approximately 500 to approximately 1,870 words. |
| D-03 | Resolved | Visible prose standardised to British English. |
| D-04 | Resolved | PDF metadata and bookmarks corrected. |
| D-05 | Partially resolved | Long sentences were reduced in high-risk sections; several technical sentences remain long but readable. |
| L-01 | Substantially resolved | Table widths and overflow corrected. Some evidence tables remain dense but render legibly. |

## 5. Revised examiner-style quality matrix

| Category | Weight | Revised score /5 | Weighted result | Main reason |
|---|---:|---:|---:|---|
| Chapter aim and thesis alignment | 10 | 4.2 | 8.4 | RQs, chapters, contribution, and conclusion now align with available evidence. |
| Anatomical and medical correctness | 15 | 2.8 | 8.4 | Known failure is reported, but no comprehensive expert gold-set review exists. |
| Scientific argument and evidence | 12 | 3.7 | 8.9 | Stronger evidence boundaries and cautious interpretation; several experiments remain absent. |
| Literature integration and citation quality | 12 | 4.0 | 9.6 | All used keys resolve and sources are closer to claims. |
| Methodology and analytical rigour | 10 | 3.5 | 7.0 | Actual procedures and denominators documented; final controlled ablations and expert review are missing. |
| Structure and thesis flow | 10 | 4.2 | 8.4 | Cross-chapter consistency and traceability substantially improved. |
| Language and human academic style | 8 | 4.0 | 6.4 | More specific, cautious, and project-owned; some structured repetition remains. |
| Originality and risk management | 8 | 3.8 | 6.1 | Project-specific synthesis and attribution improved; no institutional similarity database was available. |
| Figures, tables, equations, and LaTeX | 7 | 4.4 | 6.2 | Clean builds, working references, bookmarks, and corrected table layouts. |
| Critical analysis and limitations | 5 | 4.5 | 4.5 | Missing evidence and negative results are now explicit. |
| Formatting, references, submission polish | 3 | 4.5 | 2.7 | Strong build and front-matter polish, subject to final metadata confirmation. |
| **Total** | **100** |  | **76.5/100** | **Near submission, conditional** |

This score is an examiner-style qualitative estimate, not an institutional grade.

## 6. Remaining author or supervisor decisions

The following items cannot be completed accurately without author or supervisor confirmation:

1. **Exact submission date.** The project currently states `August 2026`; replace it with the official day before submission.
2. **Official faculty wording.** The project uses `Faculty I: Computer Science & Applications`; confirm the exact HFU wording required on the title page.
3. **Second-supervisor title and spelling.** The project currently uses `Prof. Dr. med. habil. Stephan Heermann`; confirm this exact institutional form.
4. **AI disclosure format.** The factual disclosure is included, but HFU or the supervisors may require a particular form or appendix structure.
5. **RQ3 acceptance.** The corrected thesis treats RQ3 as a design-verification question. If the supervisors require an empirical comparison, an actual MCP runtime experiment and comparator must still be executed.
6. **Final anatomy validation.** A systematic anatomy-expert review is still needed for any stronger educational-accuracy claim.
7. **Final reproducible rerun.** A clean, frozen rerun would be required to claim reproducibility or final-system performance rather than exploratory evidence.

## 7. Integrity and originality limits

- No plagiarism percentage is reported because Turnitin, iThenticate, or an equivalent institutional database was not available.
- No AI-authorship percentage is reported because prose alone cannot establish authorship reliably.
- Structural analysis found no repeated thesis sentences and only short overlaps with supplied project planning documents, principally research-question wording and standard design-table headings.
- These observations reduce internal-reuse risk but are not a substitute for an institutional similarity check.

## 8. Recommended submission workflow

1. Confirm the four metadata/disclosure items in Section 6.
2. Upload the corrected ZIP to a new Overleaf project; keep the current project as backup.
3. Set `main.tex` as the Overleaf main document and select pdfLaTeX.
4. Compile the cached preview and check the title page and page count.
5. Use `main_full.tex` for the final locally generated submission PDF after any new citation, label, or structural change.
6. Have both supervisors review the reframed RQ2/RQ3 wording before final submission.
7. Run the university-required similarity and AI-use disclosure process.

## 9. Deliverable status

The corrected project removes the visible and logical blockers that can be repaired in the manuscript. It does **not** disguise absent experiments or unresolved implementation defects. Its defensible contribution is now stated as a dual-pipeline prototype, implementation/evolution record, verification design, exploratory RAG evaluation, and explicit limitation analysis.
