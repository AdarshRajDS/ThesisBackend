# Overleaf compile-timeout fix

The prior package could still time out because it exposed multiple root
entry-point files and allowed repeated pdfLaTeX passes. This revision is a
strict single-pass package.

## Use these settings

- **Main document:** `main.tex`
- **Compiler:** `pdfLaTeX`
- After upload: **Recompile from scratch** once

## Technical safeguards

- `main.tex` invokes `\nofiles`, preventing `.aux`, `.toc`, `.lof`, `.lot`, and
  `.out` updates that would trigger latexmk reruns.
- `.latexmkrc` disables BibTeX and limits the build to one pass.
- citation and reference definitions come from `cache/aux_snapshot.tex`;
- contents and lists come from static cache files;
- bibliography entries come from `references_manual.tex`;
- diagrams are already rendered as PDF files;
- alternative full-build roots are stored under `local_build_sources/` with
  the extension `.disabled`.

The cost of strict timeout-safe mode is that bookmarks and structural caches do
not automatically refresh in Overleaf. Use the corrected full-build PDF for the
final archived submission, or refresh caches through the documented local
workflow after structural changes.
