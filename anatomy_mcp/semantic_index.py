"""Semantic (embedding) fallback index over the exportable Z-Anatomy catalog.

The deterministic tiers in ``catalog_suggest`` (token / partial / fuzzy /
colloquial synonym) cover the common cases, but they still miss queries whose
wording never overlaps the Latin catalog labels (e.g. "blood filter" -> kidney,
"voice box" -> larynx). This module adds a small MiniLM embedding index so those
queries can be resolved by meaning instead of by lexical overlap.

Design goals:
  * Build ONCE, offline, from ``exportable_catalog.json`` (no Blender needed).
  * At query time do a plain NumPy cosine over a few thousand vectors — no FAISS,
    no external service. The catalog is bounded (~6k entries), so this is fast.
  * Degrade gracefully: if the index file, the model, or ``sentence-transformers``
    is unavailable, every entry point returns empty and the caller falls back to
    the existing deterministic behaviour.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np

try:  # dual import: flat when run as anatomy_mcp/server.py, packaged otherwise
    from config import EXPORTABLE_CATALOG_PATH
    from catalog_exportability import is_exportable_catalog_entry
except ImportError:  # pragma: no cover - exercised only in packaged imports
    from anatomy_mcp.config import EXPORTABLE_CATALOG_PATH
    from anatomy_mcp.catalog_exportability import is_exportable_catalog_entry


_LABEL_INDEX_DIR = EXPORTABLE_CATALOG_PATH.parent
SEMANTIC_INDEX_PATH = _LABEL_INDEX_DIR / "semantic_index.npz"
SEMANTIC_META_PATH = _LABEL_INDEX_DIR / "semantic_index_meta.json"

EMBEDDING_MODEL_NAME = os.getenv(
    "ANATOMY_SEMANTIC_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# Below this cosine similarity a hit is treated as noise and dropped.
DEFAULT_MIN_SCORE = float(os.getenv("ANATOMY_SEMANTIC_MIN_SCORE", "0.30"))

_LATERAL_SUFFIXES = (".l", ".r", ".i", ".j")
# Z-Anatomy top-level collections are prefixed with an ordering number ("1: Skeletal
# system"); that prefix is noise for semantic matching.
_ORDER_PREFIX = re.compile(r"^\s*\d+\s*[:.\-]\s*")


def semantic_enabled() -> bool:
    """Feature flag; on by default but easy to disable for A/B or debugging."""
    return os.getenv("ANATOMY_SEMANTIC_SUGGEST_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )


def _humanize_label(label: str, side: str | None) -> str:
    """Turn a catalog label like ``Femur.l`` into readable text ``femur left``."""
    text = _ORDER_PREFIX.sub("", str(label or "").strip())
    lower = text.lower()
    for suffix in _LATERAL_SUFFIXES:
        if lower.endswith(suffix):
            text = text[: -len(suffix)]
            break
    text = text.replace("_", " ").replace(".", " ").strip()
    if side in ("left", "right"):
        text = f"{text} {side}"
    return " ".join(text.split())


def _top_level_region(entry: dict[str, Any]) -> str | None:
    paths = entry.get("collection_paths") or []
    if paths and isinstance(paths[0], list) and paths[0]:
        return str(paths[0][0])
    parents = entry.get("parent_collections") or []
    if parents:
        return str(parents[0])
    return None


def build_entry_document(entry: dict[str, Any]) -> str:
    """Compose the natural-language description embedded for one catalog entry.

    Kept deterministic (no LLM) so the index is cheap and reproducible; the
    metadata Z-Anatomy already carries (label, side, collection hierarchy) is
    enough signal for semantic retrieval.
    """
    label = str(entry.get("label") or "")
    side = entry.get("side")
    readable = _humanize_label(label, side)

    parts: list[str] = [readable]

    kind = "region" if entry.get("match_type") == "collection" else "structure"
    parts.append(f"anatomical {kind}")

    region = _top_level_region(entry)
    region_readable = _humanize_label(region, None) if region else ""
    if region_readable and region_readable.lower() != readable.lower():
        parts.append(f"in the {region_readable}")

    parents = []
    for p in (entry.get("parent_collections") or [])[:4]:
        if not p or str(p) == region:
            continue
        parent_readable = _humanize_label(str(p), None)
        if parent_readable and parent_readable.lower() != readable.lower():
            parents.append(parent_readable)
    if parents:
        parts.append("part of " + ", ".join(parents))

    return ". ".join(part for part in parts if part).strip()


def _iter_exportable_entries(catalog_data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in catalog_data.get("entries", [])
        if isinstance(entry, dict) and is_exportable_catalog_entry(entry)
    ]


def build_semantic_index(
    *,
    catalog_path: Path = EXPORTABLE_CATALOG_PATH,
    index_path: Path = SEMANTIC_INDEX_PATH,
    meta_path: Path = SEMANTIC_META_PATH,
    batch_size: int = 64,
) -> dict[str, Any]:
    """Embed every exportable catalog entry and persist the vectors + metadata.

    Returns a small summary dict. Requires ``sentence-transformers``; raises if it
    is unavailable so the offline build fails loudly (unlike the query path, which
    degrades silently).
    """
    from sentence_transformers import SentenceTransformer

    catalog_data = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    entries = _iter_exportable_entries(catalog_data)
    if not entries:
        raise ValueError(f"No exportable entries found in {catalog_path}")

    documents = [build_entry_document(entry) for entry in entries]

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embeddings = model.encode(
        documents,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype(np.float32)

    index_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(index_path, embeddings=embeddings)

    meta = {
        "model_name": EMBEDDING_MODEL_NAME,
        "embedding_dim": int(embeddings.shape[1]),
        "count": int(embeddings.shape[0]),
        "catalog_entry_count": int(catalog_data.get("entry_count") or len(entries)),
        "source_blend": catalog_data.get("source_blend"),
        "entries": [
            {
                "label": str(entry.get("label") or ""),
                "match_type": entry.get("match_type"),
                "id": entry.get("id"),
                "document": document,
            }
            for entry, document in zip(entries, documents)
        ],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "index_path": str(index_path),
        "meta_path": str(meta_path),
        "count": meta["count"],
        "embedding_dim": meta["embedding_dim"],
        "model_name": EMBEDDING_MODEL_NAME,
    }


class SemanticCatalogIndex:
    """Lazy-loaded query side of the semantic catalog index."""

    def __init__(self, index_path: Path, meta_path: Path) -> None:
        self._index_path = index_path
        self._meta_path = meta_path
        self._embeddings: np.ndarray | None = None
        self._labels: list[str] = []
        self._match_types: list[str | None] = []
        self._model_name: str = EMBEDDING_MODEL_NAME
        self._model: Any = None
        self._loaded = False
        self._load_failed = False

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return not self._load_failed and self._embeddings is not None and len(self._labels) > 0

    def _ensure_loaded(self) -> None:
        if self._loaded or self._load_failed:
            return
        try:
            if not self._index_path.exists() or not self._meta_path.exists():
                self._load_failed = True
                return
            meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
            entries = meta.get("entries") or []
            with np.load(self._index_path) as payload:
                embeddings = payload["embeddings"].astype(np.float32)
            if embeddings.shape[0] != len(entries) or embeddings.shape[0] == 0:
                self._load_failed = True
                return
            self._embeddings = embeddings
            self._labels = [str(item.get("label") or "") for item in entries]
            self._match_types = [item.get("match_type") for item in entries]
            self._model_name = str(meta.get("model_name") or EMBEDDING_MODEL_NAME)
            self._loaded = True
        except Exception:
            # Any corruption / version mismatch -> disable semantic tier quietly.
            self._load_failed = True

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            return True
        except Exception:
            self._load_failed = True
            return False

    def search(
        self,
        query_text: str,
        *,
        limit: int = 8,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> list[dict[str, Any]]:
        query = (query_text or "").strip()
        if not query:
            return []
        self._ensure_loaded()
        if not self.available or not self._ensure_model():
            return []

        try:
            query_vec = self._model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)[0]
        except Exception:
            return []

        assert self._embeddings is not None  # for type checkers; guarded by available
        scores = self._embeddings @ query_vec
        if scores.size == 0:
            return []

        top_n = min(len(self._labels), max(limit, 1))
        top_idx = np.argpartition(-scores, top_n - 1)[:top_n]
        top_idx = top_idx[np.argsort(-scores[top_idx])]

        results: list[dict[str, Any]] = []
        for idx in top_idx:
            score = float(scores[idx])
            if score < min_score:
                continue
            results.append(
                {
                    "label": self._labels[idx],
                    "match_type": self._match_types[idx],
                    "score": score,
                }
            )
        return results


_INDEX_SINGLETON: SemanticCatalogIndex | None = None


def get_semantic_index() -> SemanticCatalogIndex | None:
    """Return the process-wide semantic index, or ``None`` when disabled."""
    global _INDEX_SINGLETON
    if not semantic_enabled():
        return None
    if _INDEX_SINGLETON is None:
        _INDEX_SINGLETON = SemanticCatalogIndex(SEMANTIC_INDEX_PATH, SEMANTIC_META_PATH)
    return _INDEX_SINGLETON


if __name__ == "__main__":
    summary = build_semantic_index()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
