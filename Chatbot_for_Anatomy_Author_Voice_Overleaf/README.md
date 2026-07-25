# Anatomy Thesis — Overleaf Free-Plan Project

**Approved title in this project:** *Chatbot for Anatomy*

This version is optimized for Overleaf's short free-plan compile window.

## Quick start

1. In Overleaf, choose **New Project -> Upload Project**.
2. Upload `Chatbot_for_Anatomy_Corrected_Overleaf.zip`.
3. Set the **Main document** to `main.tex`.
4. Select **pdfLaTeX**.
5. Select **Stop on first error**.
6. Compile in **Normal** mode.

`main.tex` is a lightweight preview build. It uses pre-rendered PDF diagrams, a static bibliography, and cached cross-reference/list snapshots. LatexMk may run a second inexpensive pdfLaTeX pass to stabilize auxiliary files and bookmarks, but it does not run TikZ, Biber, or BibTeX during routine Overleaf compilation.

Read `OVERLEAF_TIMEOUT_FIX.md` before changing the bibliography, labels, or
chapter structure.

## Build entry points

| File | Purpose | Recommended environment |
|---|---|---|
| `main.tex` | Fast cached full-document preview (at most three lightweight passes) | Overleaf free plan |
| `main_full.tex` | Normal multi-pass build with live references and BibTeX bibliography | Local machine / extended compile time |
| `main_bibtex.tex` | Compatibility entry point for a dynamic BibTeX build | Local machine / extended compile time |

## What updates immediately in fast mode

- chapter text;
- tables;
- pre-rendered figures;
- ordinary formatting;
- existing citations and cross-references.

## What needs a cache refresh

- new citation keys;
- new or renamed labels;
- table-of-contents page numbers;
- list-of-figures and list-of-tables entries;
- changed cross-reference page numbers.

After a normal local build, run:

```bash
python3 scripts/refresh_fast_cache.py
```

Then upload the updated `cache/*.tex` files and, when necessary,
`references_manual.tex`.

## Edit first

1. Update all fields in `metadata.tex`.
2. Freeze the repository and replace `\RepositoryCommit`.
3. Open `project_resources/THESIS_COMPLETE_CHAT_AND_CHAPTER_GUIDE.md`.
4. Use one prompt from `chapter_prompts/` per chapter chat.
5. Add approved screenshots under `assets/screenshots/` and result files under
   `assets/results/`.
6. Keep numerical claims tied to the recorded run register and do not reintroduce evidence placeholders as results.

Draft notes are hidden by default in `preamble.tex`:

```latex
\draftnotesfalse
```

Change it to `\draftnotestrue` only when you need the lightweight evidence
reminders.

## Final thesis structure

1. Introduction
2. Background and Related Work
3. Research Methodology and Requirements
4. System Evolution and Design Decisions
5. Final System Design and Implementation
6. Evaluation Methodology
7. Results and Discussion
8. Conclusion and Future Work

## Critical thesis rule

RAG and MCP remain separate in evaluation:

- RAG: retrieval, faithfulness, citations, hallucination, abstention, images.
- MCP: catalog resolution, tool execution, GLB/JSON validity, viewer loading,
  latency, cache behaviour, and safe failure.

## Copyright and data handling

Do not upload copyrighted course PDFs, personal data, credentials, or service
keys to Overleaf unless institutional policy and the relevant rights permit it.
Use filenames, hashes, sanitized excerpts, and approved screenshots where
possible.
