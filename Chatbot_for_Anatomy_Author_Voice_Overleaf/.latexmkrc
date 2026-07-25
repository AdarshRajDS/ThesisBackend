# TIMEOUT-SAFE OVERLEAF FREE-PLAN BUILD
# main.tex uses \nofiles plus frozen citation/reference/list snapshots, so only
# one pdfLaTeX pass is required. BibTeX/Biber and automatic repeat passes are
# intentionally disabled.
$pdf_mode = 1;
$bibtex_use = 0;
$interaction = 'nonstopmode';
$halt_on_error = 1;
$max_repeat = 1;
@default_files = ('main.tex');
