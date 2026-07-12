from pathlib import Path
import hashlib
import os
import re
import shutil
import numpy as np

from src.multimodal.multimodal_retriever import MultimodalRetriever
from src.llm.llm_factory import get_llm
from src.multimodal.clip_embedding import CLIPEmbedding
from src.embeddings.embedding_factory import get_text_embedding
from src.retrieval.vector_store import VectorStoreFactory
from src.rag.content_heuristics import infer_content_type
from src.rag.query_rewriter import rewrite_queries
from src.rag.passage_reranker import rerank_passages
from src.rag.citation_filter import filter_sources_pre_generation
from src.rag.question_classifier import classify_question, max_passages_for_type

# Fallback cap when no question-type-specific cap applies.
_MAX_UNIQUE_TEXT_PASSAGES = 6
# Candidates pulled per query variant / retrieval method before dedupe + rerank.
_CHROMA_TEXT_CANDIDATES = 40
# Fused candidate pool size returned by the hybrid retriever.
_HYBRID_FINAL = 32


def _normalize_pdf_stem(name: str | None) -> str:
    """Collapse filename variants (e.g. anatomy+phys vs anatomyphys) for dedupe keys."""
    if not name:
        return ""
    base = os.path.basename(str(name)).lower()
    base = re.sub(r"\.pdf$", "", base)
    return re.sub(r"[^a-z0-9]+", "", base)


def _text_fingerprint(text: str, n: int = 220) -> str:
    t = " ".join((text or "").split())[:n].lower()
    return hashlib.sha256(t.encode("utf-8", errors="ignore")).hexdigest()


def _normalize_image_dedupe_key(object_key: str | None, filename: str | None) -> str:
    raw = object_key or filename or ""
    return re.sub(r"[^a-z0-9]+", "", str(raw).lower())


class MultimodalRAG:

    def __init__(self):

        print("DEBUG: Initializing MultimodalRAG")

        self.retriever = MultimodalRetriever()
        self.llm = get_llm()

        # cross modal models
        self.clip = CLIPEmbedding()
        self.text_embedder = get_text_embedding()
        # Text corpus (MiniLM) — same Chroma as `src/ingestion/run.py`
        self.text_vectordb = VectorStoreFactory.create(self.text_embedder)

        # Hybrid retriever (BM25 + dense + phrase, RRF fused). Built once; the
        # BM25 index is cached to disk. Falls back to plain dense search if it
        # cannot be constructed (e.g. empty corpus or missing rank_bm25).
        try:
            from src.retrieval.hybrid_retriever import HybridRetriever

            self.hybrid = HybridRetriever(self.text_vectordb, text_embedder=self.text_embedder)
            print("DEBUG hybrid retriever ready")
        except Exception as e:
            print("DEBUG hybrid retriever unavailable, using dense only:", str(e))
            self.hybrid = None

        # project root
        self.PROJECT_ROOT = Path(__file__).resolve().parents[2]
        print("DEBUG PROJECT_ROOT:", self.PROJECT_ROOT)

        self.BASE_DATA_DIR = Path(os.getenv("HF_HOME", "data"))

        self.OUTPUT_DIR = (self.PROJECT_ROOT / self.BASE_DATA_DIR / "outputs").resolve()
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        self.PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

    def _dedupe_candidates(self, candidates: list):
        """
        Dedupe candidate Documents by near-duplicate body text and by
        (normalized PDF stem + page), and drop obvious TOC/footer/index chunks.
        Returns aligned (docs, sources) lists.
        """
        seen_fp: set[str] = set()
        seen_loc: set[tuple[str, int | None]] = set()
        out_docs = []
        sources = []

        for d in candidates:
            body = (getattr(d, "page_content", None) or "").strip()
            if not body:
                continue

            fp = _text_fingerprint(body)
            if fp in seen_fp:
                continue

            meta = getattr(d, "metadata", None) or {}

            # Drop table-of-contents / footer / index chunks outright: these were
            # polluting sources (e.g. book index pages) and starving real content.
            if infer_content_type(body, meta) in ("toc", "footer", "index"):
                continue

            raw_src = meta.get("source") or meta.get("file_path")
            stem = _normalize_pdf_stem(str(raw_src) if raw_src else None)
            page = meta.get("page")
            if page is not None and not isinstance(page, int):
                try:
                    page = int(page)
                except (TypeError, ValueError):
                    page = None

            loc_key = (stem, page)
            if stem and loc_key in seen_loc:
                continue

            seen_fp.add(fp)
            if stem:
                seen_loc.add(loc_key)

            src = os.path.basename(str(raw_src)) if raw_src else None
            preview = body if len(body) <= 400 else body[:400] + "…"
            sources.append({"source": src, "page": page, "chunk_preview": preview})
            out_docs.append(d)

        return out_docs, sources

    def _retrieve_text_corpus(
        self,
        query: str,
        *,
        question_type: str = "simple",
        figure_id: str | None = None,
        max_passages: int | None = None,
    ):
        """
        Grounded text retrieval: query rewrite -> hybrid (BM25 + dense + phrase)
        candidate search -> dedupe + TOC/index drop -> support-score rerank ->
        pre-generation citation filter. Returns at most `max_passages` passages.
        """
        cap = max_passages if max_passages is not None else _MAX_UNIQUE_TEXT_PASSAGES
        if cap <= 0:
            return [], []

        # 1. Query variants (typo fix + anatomy synonym/corpus expansion).
        try:
            variants = rewrite_queries(query, question_type=question_type) or [query]
        except Exception as e:
            print("DEBUG query rewrite error:", str(e))
            variants = [query]

        # 2. Hybrid candidate retrieval (fallback to plain dense search).
        candidates = []
        if self.hybrid is not None:
            try:
                candidates = self.hybrid.search(
                    variants,
                    k_per_query=_CHROMA_TEXT_CANDIDATES,
                    k_final=_HYBRID_FINAL,
                )
            except Exception as e:
                print("DEBUG hybrid retrieval error:", str(e))
                candidates = []
        if not candidates:
            try:
                candidates = self.text_vectordb.similarity_search(
                    query, k=_CHROMA_TEXT_CANDIDATES
                )
            except Exception as e:
                print("DEBUG text corpus retrieval error:", str(e))
                return [], []

        # 3. Dedupe + drop TOC/index/footer.
        cand_docs, cand_sources = self._dedupe_candidates(candidates)
        if not cand_docs:
            print("DEBUG text corpus: no usable candidates after dedupe/filter")
            return [], []

        # 4. Support-score rerank (lexical overlap + semantic + content-type).
        try:
            ranked_docs, ranked_sources, _ = rerank_passages(
                query,
                cand_docs,
                cand_sources,
                question_type=question_type,
                figure_id=figure_id,
                text_embedder=self.text_embedder,
                min_score=0.10,
                max_passages=cap,
            )
        except Exception as e:
            print("DEBUG rerank error:", str(e))
            ranked_docs, ranked_sources = cand_docs[:cap], cand_sources[:cap]

        # 5. Pre-generation citation filter (residual footer/low-support drop).
        try:
            filtered_sources = filter_sources_pre_generation(ranked_sources)
        except Exception as e:
            print("DEBUG citation pre-filter error:", str(e))
            filtered_sources = ranked_sources

        if filtered_sources and len(filtered_sources) != len(ranked_sources):
            kept_ids = {id(s) for s in filtered_sources}
            pairs = [
                (d, s)
                for d, s in zip(ranked_docs, ranked_sources)
                if id(s) in kept_ids
            ]
            ranked_docs = [d for d, _ in pairs]
            ranked_sources = filtered_sources

        print(
            "DEBUG text corpus passages:",
            len(ranked_docs),
            f"(cap {cap}, type={question_type})",
        )

        return ranked_docs, ranked_sources

    def gather_retrieval_bundle(self, query: str) -> dict:
        """
        Shared retrieval for production `ask` and thesis `/rag/experiment` (no LLM calls).
        """
        classification = classify_question(query)
        question_type = classification.question_type
        figure_id = classification.figure_id
        cap = max_passages_for_type(question_type)
        print(f"DEBUG question_type={question_type} passage_cap={cap} figure_id={figure_id}")

        docs, metas = self.retriever.retrieve(query, k=20)

        print("DEBUG total metas:", len(metas))

        image_metas = [m for m in metas if m.get("type") == "image"]

        print("DEBUG image metas:", len(image_metas))

        text_corpus_docs, text_sources = self._retrieve_text_corpus(
            query,
            question_type=question_type,
            figure_id=figure_id,
            max_passages=cap,
        )
        print("DEBUG text corpus chunks:", len(text_corpus_docs))

        multimodal_text = "\n\n".join(d for d in docs if d and str(d).strip())
        text_block = "\n\n---\n\n".join(d.page_content for d in text_corpus_docs if d.page_content)

        blocks = []
        if text_block.strip():
            blocks.append(f"Text passages from uploaded documents:\n{text_block}")
        if multimodal_text.strip():
            blocks.append(f"Additional text from the multimodal index:\n{multimodal_text}")

        if blocks:
            context = "\n\n".join(blocks)
        else:
            context = (
                "(No document passages were retrieved from the text index or multimodal store. "
                "You may use general anatomy knowledge; briefly note that no uploaded passages were retrieved.)"
            )

        return {
            "docs": docs,
            "metas": metas,
            "image_metas": image_metas,
            "text_corpus_docs": text_corpus_docs,
            "text_sources": text_sources,
            "multimodal_text": multimodal_text,
            "context": context,
            "context_blocks": blocks,
            "question_type": question_type,
            "figure_id": figure_id,
        }

    def rank_and_publish_images(self, query: str, image_metas: list) -> list:
        """CLIP + caption rerank, then presigned/local URLs (same logic as production `ask`)."""
        reranked = []

        query_clip = self.clip.embed_text([query])[0]
        query_text = self.text_embedder.embed_query(query)

        for m in image_metas:

            raw_caption = m.get("caption") or ""
            context_text = m.get("context") or m.get("nearby_text") or ""
            object_key = m.get("object_key")

            candidate_text = raw_caption.strip() or context_text.strip()

            image_path = m.get("image_path")

            print("\n--- IMAGE CANDIDATE ---")
            print("DEBUG caption:", raw_caption)
            print("DEBUG candidate_text:", candidate_text[:200])
            print("DEBUG raw image_path:", image_path)

            if not candidate_text or len(candidate_text) < 10:
                print("DEBUG skipped: weak caption")
                continue

            local_file_exists = False

            if image_path:
                image_path = Path(image_path)

                if not image_path.is_absolute():
                    image_path = self.PROJECT_ROOT / image_path

                print("DEBUG resolved image_path:", image_path)
                local_file_exists = image_path.exists()
            else:
                print("DEBUG no local image_path in metadata")

            if not local_file_exists and not object_key:
                print("DEBUG skipped: file missing and no object_key")
                continue

            try:

                caption_embedding = self.text_embedder.embed_query(candidate_text)

                caption_score = float(
                    np.dot(query_text, caption_embedding)
                    / (np.linalg.norm(query_text) * np.linalg.norm(caption_embedding))
                )

                if local_file_exists:
                    print("DEBUG computing CLIP embedding")

                    image_embedding = self.clip.embed_image([str(image_path)])[0]

                    clip_score = float(
                        np.dot(query_clip, image_embedding)
                        / (np.linalg.norm(query_clip) * np.linalg.norm(image_embedding))
                    )

                    final_score = 0.25 * clip_score + 0.75 * caption_score
                    print("DEBUG clip_score:", clip_score)
                else:
                    final_score = caption_score
                    print("DEBUG remote-only rerank (no local file)")

                print("DEBUG caption_score:", caption_score)
                print("DEBUG final_score:", final_score)

                min_score = 0.18 if local_file_exists else 0.10
                if final_score < min_score:
                    print("DEBUG skipped: score too low")
                    continue

                reranked.append((final_score, m))

            except Exception as e:
                print("DEBUG embedding error:", str(e))
                continue

        print("\nDEBUG reranked count:", len(reranked))

        reranked.sort(key=lambda x: x[0], reverse=True)

        ranked_metas = [x[1] for x in reranked[:5]]

        print("DEBUG top image candidates:", len(ranked_metas))

        public_images = []
        seen_dedupe = set()

        MAX_IMAGES = 3

        for m in ranked_metas:

            if len(public_images) >= MAX_IMAGES:
                break

            object_key = m.get("object_key")

            print("\nDEBUG generating URL for:", object_key)

            if object_key:
                dedupe_k = _normalize_image_dedupe_key(object_key, None)
                if dedupe_k and dedupe_k in seen_dedupe:
                    continue

                try:

                    from app.services.object_storage import get_presigned_url

                    url = get_presigned_url(object_key)

                    print("DEBUG presigned url:", url)

                    if url:
                        public_images.append(url)
                        if dedupe_k:
                            seen_dedupe.add(dedupe_k)
                        continue

                except Exception as e:
                    print("DEBUG MinIO error:", str(e))

            src_path = m.get("image_path")

            if not src_path:
                continue

            src_path = Path(src_path)

            if not src_path.is_absolute():
                src_path = self.PROJECT_ROOT / src_path

            if not src_path.exists():
                continue

            filename = src_path.name
            local_k = _normalize_image_dedupe_key(None, filename)
            if local_k and local_k in seen_dedupe:
                continue

            if local_k:
                seen_dedupe.add(local_k)

            dst_path = self.OUTPUT_DIR / filename

            if not dst_path.exists():
                shutil.copy(src_path, dst_path)

            public_url = f"{self.PUBLIC_BASE_URL}/outputs/{filename}"

            print("DEBUG fallback url:", public_url)

            public_images.append(public_url)

        print("\nDEBUG FINAL IMAGE COUNT:", len(public_images))

        return public_images

    def ask(self, query):

        print("\n==============================")
        print("DEBUG QUERY:", query)
        print("==============================")

        bundle = self.gather_retrieval_bundle(query)
        text_corpus_docs = bundle["text_corpus_docs"]
        text_sources = bundle["text_sources"]
        multimodal_text = bundle["multimodal_text"]
        context = bundle["context"]
        image_metas = bundle["image_metas"]

        prompt = f"""
You are a medical anatomy assistant.

Base your answer on the context passages below whenever they are relevant to the
question. You may use general anatomy knowledge to fill small gaps, but never
contradict the context. If the context contains nothing relevant, say so briefly
and answer from general anatomy knowledge.

Always answer in the same language as the question.

Context:
{context}

Question:
{query}
"""

        response = self.llm.invoke(prompt)

        public_images = self.rank_and_publish_images(query, image_metas)

        used_multimodal_excerpts = bool(multimodal_text.strip())
        had_retrieved = bool(text_corpus_docs) or used_multimodal_excerpts

        if had_retrieved:
            primary = "retrieved_corpus_synthesized"
            prov = (
                "The model was given retrieved text from your index (and possibly multimodal text snippets). "
                "The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim "
                "extract, unless it explicitly quotes the context. General world knowledge may still appear "
                "where the model fills gaps."
            )
        else:
            primary = "general_knowledge_fallback"
            prov = (
                "No passages were retrieved from the text or multimodal text index for this query. "
                "The answer is driven mainly by the model's pretrained knowledge; treat it as ungrounded "
                "in your uploaded corpus."
            )

        grounding = {
            "had_retrieved_passages_in_prompt": had_retrieved,
            "unique_text_passages_used": len(text_corpus_docs),
            "used_multimodal_text_excerpts": used_multimodal_excerpts,
            "primary_basis": primary,
            "provenance_explanation": prov,
            "evaluation_note": (
                "Automatic correctness is not asserted. Options for thesis evaluation: human expert "
                "rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), "
                "and a small gold Q&A set over your PDFs."
            ),
        }

        return response.content, public_images, text_sources, grounding
