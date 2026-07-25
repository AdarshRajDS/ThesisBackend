Liver — portable Anatomy Viewer
=====================================

This folder is a full copy of the thesis Anatomy Viewer for this export
(same labels, views, cross-section, exploded view, materials).

How to open
-----------
1. Double-click open.bat   (Windows), OR
2. In this folder run:  python -m http.server 5500
   then open http://127.0.0.1:5500/

Do not rely on the thesis backend / localhost:8000 — this package is self-contained.

Files
-----
index.html       full viewer
model.glb        3D model
annotations.json labels
viewer.js / vendor/   viewer runtime
