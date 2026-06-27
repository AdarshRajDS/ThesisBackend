import fitz  # PyMuPDF
import json
from pathlib import Path

from src.config.settings import settings
from src.utils.logger import get_logger
from app.services.object_storage import put_object, ensure_bucket, get_active_bucket_name
from src.ingestion.caption_extractor import extract_caption

logger = get_logger(__name__)


class ImageExtractor:

    def __init__(self):
        self.output_dir = Path(settings.processed_data_dir) / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.metadata = []

        # Pipeline stats for API/debug (accumulated across all PDFs in one run)
        self.stats = {
            "storage_provider": settings.storage_provider,
            "active_bucket": get_active_bucket_name(),
            "ensure_bucket_ok": False,
            "images_total": 0,
            "uploads_ok": 0,
            "uploads_failed": 0,
            "failed_object_keys": [],
        }

        logger.info(
            "[IMAGE_PIPELINE] Step 1: provider=%s bucket=%s",
            self.stats["storage_provider"],
            self.stats["active_bucket"],
        )
        self.stats["ensure_bucket_ok"] = bool(ensure_bucket())
        logger.info(
            "[IMAGE_PIPELINE] Step 2: ensure_bucket_ok=%s",
            self.stats["ensure_bucket_ok"],
        )
        if not self.stats["ensure_bucket_ok"]:
            logger.warning(
                "[IMAGE_PIPELINE] ensure_bucket failed — object uploads will likely fail. "
                "Check Supabase URL/key, bucket name, and that `pip install supabase` is installed."
            )

    def extract_from_pdf(self, pdf_path: Path):
        logger.info(f"[IMAGE_PIPELINE] Step 3: extracting images from {pdf_path.name}")

        doc = fitz.open(pdf_path)

        for page_number in range(len(doc)):
            page = doc[page_number]
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)

                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                image_filename = (
                    f"{pdf_path.stem}_page_{page_number+1}_img_{img_index}.{image_ext}"
                )

                local_image_path = self.output_dir / image_filename

                # Save locally (optional fallback/debug)
                with open(local_image_path, "wb") as img_file:
                    img_file.write(image_bytes)

                # ---- MINIO OBJECT KEY ----
                object_key = (
                    f"{pdf_path.stem}/page_{page_number+1}/{image_filename}"
                )

                # ---- UPLOAD TO OBJECT STORAGE (MinIO or Supabase) ----
                self.stats["images_total"] += 1
                uploaded = put_object(
                    object_key=object_key,
                    data=image_bytes,
                    content_type=f"image/{image_ext}",
                )

                if uploaded:
                    self.stats["uploads_ok"] += 1
                    logger.info(
                        "[IMAGE_PIPELINE] Step 4 OK: uploaded key=%s (%s, %s bytes)",
                        object_key,
                        image_ext,
                        len(image_bytes),
                    )
                else:
                    self.stats["uploads_failed"] += 1
                    self.stats["failed_object_keys"].append(object_key)
                    logger.warning(
                        "[IMAGE_PIPELINE] Step 4 FAIL: upload failed for key=%s",
                        object_key,
                    )

                # ---- EXTRACT NEARBY TEXT ----
                nearby_text = page.get_text()

                caption = extract_caption(nearby_text)

                context = nearby_text[:500] if nearby_text else ""

                # ---- SAVE METADATA ----
                metadata_item = {
                    "image_path": str(local_image_path),
                    "page": page_number + 1,
                    "source": pdf_path.name,
                    "image_index": img_index,
                    "width": base_image.get("width"),
                    "height": base_image.get("height"),
                    "caption": caption,
                    "context": context,
                    "nearby_text": nearby_text,
                    "object_key": object_key if uploaded else None,
                    "bucket": get_active_bucket_name() if uploaded else None,
                }

                self.metadata.append(metadata_item)

        doc.close()

    def save_metadata(self):
        metadata_path = Path(settings.processed_data_dir) / "image_metadata.json"

        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)

        logger.info(
            "[IMAGE_PIPELINE] Step 5: saved %s metadata rows to %s | uploads_ok=%s uploads_failed=%s",
            len(self.metadata),
            metadata_path,
            self.stats["uploads_ok"],
            self.stats["uploads_failed"],
        )