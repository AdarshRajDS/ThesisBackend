from pathlib import Path
from src.config.settings import settings
from src.ingestion.image_extractor import ImageExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_image_extraction():

    raw_path = Path(settings.raw_data_dir)
    pdf_files = list(raw_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning("No PDFs found.")
        return {
            "status": "warning",
            "message": "No PDFs for image extraction",
            "pdf_files": [],
            "extractor_stats": None,
        }

    extractor = ImageExtractor()

    for pdf in pdf_files:
        extractor.extract_from_pdf(pdf)

    extractor.save_metadata()

    logger.info("Image extraction complete.")

    return {
        "status": "success",
        "message": "Image extraction complete",
        "pdf_files": [p.name for p in pdf_files],
        "extractor_stats": extractor.stats,
    }


def main():
    run_image_extraction()


if __name__ == "__main__":
    main()
