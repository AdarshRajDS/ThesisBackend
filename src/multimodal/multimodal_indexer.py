import json
from pathlib import Path
from langchain_chroma import Chroma

from src.config.settings import settings
from src.multimodal.clip_embedding import CLIPEmbedding
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MultimodalIndexer:

    def __init__(self):
        self.embedding = CLIPEmbedding()

        self.persist_dir = Path(settings.processed_data_dir) / "multimodal_chroma"

        self.vectorstore = Chroma(
            collection_name="multimodal_rag",
            persist_directory=str(self.persist_dir)
        )

    def index_images(self):
        metadata_path = Path(settings.processed_data_dir) / "image_metadata.json"

        if not metadata_path.exists():
            logger.warning("image_metadata.json not found.")
            return

        with open(metadata_path) as f:
            metadata = json.load(f)

        if not metadata:
            logger.warning("No image metadata found.")
            return

        logger.info(f"Loaded {len(metadata)} image metadata entries.")

        # ---- CLEAR EXISTING COLLECTION ----
        try:
            existing = self.vectorstore._collection.get()
            if existing and existing.get("ids"):
                self.vectorstore._collection.delete(ids=existing["ids"])
                logger.info("Cleared existing multimodal collection.")
        except Exception as e:
            logger.warning(f"Could not clear collection: {e}")

        valid_items = []

        for item in metadata:
            image_path = Path(item.get("image_path", ""))

            if not image_path.exists():
                logger.warning(f"Missing image file: {image_path}")
                continue

            valid_items.append(item)

        if not valid_items:
            logger.warning("No valid images found for indexing.")
            return

        image_paths = [str(item["image_path"]) for item in valid_items]

        logger.info(f"Embedding {len(image_paths)} images with CLIP...")

        image_embeddings = self.embedding.embed_image(image_paths)

        ids = []
        documents = []
        metadatas = []

        for i, (embedding, item) in enumerate(zip(image_embeddings, valid_items)):

            image_id = f"{item.get('source', 'unknown')}_page_{item.get('page', 0)}_{i}"
            ids.append(image_id)

            # Document text (safe string)
            caption = item.get("caption")

            if caption:
                documents.append(caption)
            else:
                documents.append(str(item.get("nearby_text", "")))

            # ---- STRICT CHROMA-SAFE METADATA ----
            meta = {}

            meta["type"] = "image"
            meta["image_path"] = str(item.get("image_path", ""))

            # Safe int conversion
            try:
                meta["page"] = int(item.get("page", 0))
            except Exception:
                meta["page"] = 0

            meta["source"] = str(item.get("source", ""))
            caption = item.get("caption")
            if caption:
                meta["caption"] = str(caption)

            context = item.get("context")
            if context:
                meta["context"] = str(context)

            # Only add MinIO info if valid string
            bucket = item.get("bucket")
            if isinstance(bucket, str) and bucket.strip():
                meta["bucket"] = bucket

            object_key = item.get("object_key")
            if isinstance(object_key, str) and object_key.strip():
                meta["object_key"] = object_key

            metadatas.append(meta)

        self.vectorstore._collection.add(
            embeddings=image_embeddings.tolist(),
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info("Image embeddings stored in Chroma successfully.")