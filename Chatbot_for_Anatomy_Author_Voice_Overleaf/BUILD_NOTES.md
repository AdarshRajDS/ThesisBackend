# Local Build Notes

Overleaf users can normally use the fast `main.tex` entry point.

To regenerate all cross-references and the BibTeX bibliography locally:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main_full.tex
bibtex main_full
pdflatex -interaction=nonstopmode -halt-on-error main_full.tex
pdflatex -interaction=nonstopmode -halt-on-error main_full.tex
python3 scripts/refresh_fast_cache.py
```

On systems where the `bibtex` wrapper is unavailable, `bibtex8 main_full` can
be used for this bibliography.

The project uses pdfLaTeX and BibTeX. No shell escape or external fonts are
required. The routine Overleaf build uses at most three lightweight pdfLaTeX passes through `.latexmkrc`; auxiliary writes remain enabled so the PDF contains bookmarks and the generated files stabilize cleanly.
