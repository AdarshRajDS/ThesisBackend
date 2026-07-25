from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentLoader:

    def load_pdfs(self, pdf_names: list[str] | None = None):
        data_path = Path(settings.raw_data_dir)
        if pdf_names:
            pdf_files = []
            for name in pdf_names:
                candidate = data_path / Path(name).name
                if candidate.exists():
                    pdf_files.append(candidate)
                else:
                    logger.warning("Requested PDF not found: %s", candidate)
        else:
            pdf_files = list(data_path.glob("*.pdf"))

        if not pdf_files:
            logger.warning("No PDFs found in data/raw")
            return []

        documents = []

        for pdf in pdf_files:
            logger.info(f"Loading PDF: {pdf.name}")
            loader = PyMuPDFLoader(str(pdf))

            pages = loader.load()

            clean_pages = []

            for page in pages:
                text = page.page_content.strip().lower()

                # 🚫 remove index pages
                if "index" in text[:200]:
                    continue

                # 🚫 remove table of contents
                if "chapter" in text and "...." in text:
                    continue

                # 🚫 remove glossary-style alphabetical lists
                if text.count(",") > 20 and len(text) < 1500:
                    continue

                clean_pages.append(page)

            logger.info(f"Kept {len(clean_pages)} useful pages.")

            documents.extend(clean_pages)

        logger.info(f"Total kept pages: {len(documents)}")

        return documents



    def split_documents(self, documents):

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150
        )

        chunks = text_splitter.split_documents(documents)

        filtered_chunks = []

        for chunk in chunks:
            text = chunk.page_content.strip()

            # Remove very short chunks
            if len(text) < 200:
                continue

            # Remove index/table-of-contents style chunks
            if text.count(".....") > 2:
                continue

            filtered_chunks.append(chunk)

        logger.info(f"Split into {len(filtered_chunks)} clean chunks.")

        return filtered_chunks
