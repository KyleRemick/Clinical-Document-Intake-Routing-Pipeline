from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pdfplumber
import pytesseract
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


@dataclass
class ExtractionResult:
    text: str
    method: Literal["pdf", "ocr", "failed"]
    page_count: int


def extract(file_path: str | Path) -> ExtractionResult:
    path = Path(file_path)

    if not path.exists():
        logger.error("File not found: %s", path)
        return ExtractionResult(text="", method="failed", page_count=0)

    ext = path.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(path)
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return _extract_image(path)

    logger.warning("Unsupported file extension '%s': %s", ext, path.name)
    return ExtractionResult(text="", method="failed", page_count=0)


def _extract_pdf(path: Path) -> ExtractionResult:
    try:
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)

            text_parts = [p.extract_text() or "" for p in pdf.pages]
            text = "\n".join(text_parts).strip()

            if len(text) >= settings.min_text_chars:
                logger.debug("PDF text extraction succeeded (%d chars)", len(text))
                return ExtractionResult(text=text, method="pdf", page_count=page_count)

            logger.info(
                "PDF text sparse (%d chars < threshold %d), falling back to OCR: %s",
                len(text),
                settings.min_text_chars,
                path.name,
            )
            return _ocr_pdf_pages(pdf.pages, page_count)

    except Exception:
        logger.exception("PDF extraction failed: %s", path.name)
        return ExtractionResult(text="", method="failed", page_count=0)


def _ocr_pdf_pages(pages, page_count: int) -> ExtractionResult:
    ocr_parts: list[str] = []
    for page in pages:
        pil_image = _pdf_page_to_pil(page)
        ocr_parts.append(pytesseract.image_to_string(pil_image))
    return ExtractionResult(
        text="\n".join(ocr_parts).strip(),
        method="ocr",
        page_count=page_count,
    )


def _pdf_page_to_pil(page) -> Image.Image:
    """Render a pdfplumber page to a PIL Image. Isolated for testability."""
    return page.to_image(resolution=200).original


def _extract_image(path: Path) -> ExtractionResult:
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img).strip()
        return ExtractionResult(text=text, method="ocr", page_count=1)
    except Exception:
        logger.exception("Image extraction failed: %s", path.name)
        return ExtractionResult(text="", method="failed", page_count=1)
