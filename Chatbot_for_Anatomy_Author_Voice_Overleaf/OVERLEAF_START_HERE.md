# Start here: Overleaf free-plan build

This package is configured to avoid the message **“Your compile timed out”**.

## Required Overleaf settings

1. Open **Menu** in the top-left corner.
2. Set **Main document** to `main.tex`.
3. Set **Compiler** to `pdfLaTeX`.
4. Choose **Recompile from scratch** once after uploading this ZIP.
5. Click **Recompile**.

Only `main.tex` is active in this package. The expensive full-build entry files
have been moved to `local_build_sources/` and renamed with the extension
`.disabled`, preventing Overleaf from choosing them automatically.

## Why this compiles faster

- one pdfLaTeX pass only;
- no BibTeX or Biber during Overleaf compilation;
- no auxiliary-file writing or automatic reruns;
- cached citations and cross-references;
- cached table of contents, list of figures, and list of tables;
- static bibliography;
- pre-rendered PDF architecture diagrams;
- no TikZ diagram generation in the cloud build.

## What updates immediately

Normal chapter text, tables, existing figures, and wording changes update on the
next compile.

## What requires a local cache refresh

Refresh the cache after adding or renaming:

- chapters, sections, labels, or cross-references;
- bibliography keys;
- figures or tables that must appear in the lists;
- changes that alter final page numbering substantially.

For a local full build, rename
`local_build_sources/main_full.tex.disabled` to `main_full.tex`, move it to the
project root, compile it locally, and run:

```bash
python3 scripts/refresh_fast_cache.py
```

Do not make `main_full.tex` the main Overleaf document on a short free-plan
compile window.
