import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from fpdf import FPDF, XPos, YPos
from PIL import Image

from app.services.extraction import ExtractionResult, extract

requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="Tesseract not installed"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_pdf(tmp_path: Path, filename: str, lines: list[str]) -> Path:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, text=lines[0], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=11)
    for line in lines[1:]:
        pdf.cell(0, 7, text=line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    path = tmp_path / filename
    pdf.output(str(path))
    return path


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """Single-page PDF with a real text layer pdfplumber can extract."""
    return _build_pdf(
        tmp_path,
        "lab_result.pdf",
        [
            "LABORATORY REPORT",
            "Patient: Dorothy Nguyen",
            "MRN: MRN-10002",
            "Date of Birth: 07/22/1955",
            "Collection Date: 04/10/2026",
            "Ordering Provider: Dr. Ramona Esteves",
            "Hemoglobin A1c: 6.8%   Reference: <5.7%",
            "Fasting Glucose: 118 mg/dL   Reference: 70-99 mg/dL",
        ],
    )


@pytest.fixture
def blank_pdf(tmp_path: Path) -> Path:
    """PDF with a page but no text content — triggers OCR fallback."""
    pdf = FPDF()
    pdf.add_page()
    path = tmp_path / "blank.pdf"
    pdf.output(str(path))
    return path


@pytest.fixture
def png_image(tmp_path: Path) -> Path:
    img = Image.new("RGB", (400, 100), color="white")
    path = tmp_path / "document.png"
    img.save(path)
    return path


@pytest.fixture
def mock_pil_image() -> Image.Image:
    return Image.new("RGB", (100, 100), color="white")


# ---------------------------------------------------------------------------
# PDF — text layer extraction
# ---------------------------------------------------------------------------


class TestExtractPdfTextLayer:
    def test_method_is_pdf(self, text_pdf: Path) -> None:
        result = extract(text_pdf)
        assert result.method == "pdf"

    def test_extracts_patient_identifiers(self, text_pdf: Path) -> None:
        result = extract(text_pdf)
        assert "Nguyen" in result.text
        assert "MRN-10002" in result.text

    def test_page_count(self, text_pdf: Path) -> None:
        result = extract(text_pdf)
        assert result.page_count == 1

    def test_returns_extraction_result(self, text_pdf: Path) -> None:
        result = extract(text_pdf)
        assert isinstance(result, ExtractionResult)
        assert isinstance(result.text, str)
        assert isinstance(result.page_count, int)

    def test_text_is_non_empty(self, text_pdf: Path) -> None:
        result = extract(text_pdf)
        assert len(result.text) >= 50


# ---------------------------------------------------------------------------
# PDF — OCR fallback
# ---------------------------------------------------------------------------


class TestExtractPdfOcrFallback:
    def test_method_is_ocr_when_text_sparse(
        self, blank_pdf: Path, mock_pil_image: Image.Image
    ) -> None:
        with patch("app.services.extraction._pdf_page_to_pil", return_value=mock_pil_image):
            with patch(
                "app.services.extraction.pytesseract.image_to_string",
                return_value="OCR extracted text",
            ):
                result = extract(blank_pdf)

        assert result.method == "ocr"

    def test_ocr_text_is_returned(self, blank_pdf: Path, mock_pil_image: Image.Image) -> None:
        expected = "Discharge Summary Patient: James Whitfield"
        with patch("app.services.extraction._pdf_page_to_pil", return_value=mock_pil_image):
            with patch(
                "app.services.extraction.pytesseract.image_to_string",
                return_value=expected,
            ):
                result = extract(blank_pdf)

        assert result.text == expected

    def test_page_to_pil_called_once_per_page(
        self, blank_pdf: Path, mock_pil_image: Image.Image
    ) -> None:
        with patch(
            "app.services.extraction._pdf_page_to_pil", return_value=mock_pil_image
        ) as mock_render:
            with patch("app.services.extraction.pytesseract.image_to_string", return_value=""):
                extract(blank_pdf)

        assert mock_render.call_count == 1  # one page in blank_pdf

    def test_page_count_preserved(self, blank_pdf: Path, mock_pil_image: Image.Image) -> None:
        with patch("app.services.extraction._pdf_page_to_pil", return_value=mock_pil_image):
            with patch("app.services.extraction.pytesseract.image_to_string", return_value=""):
                result = extract(blank_pdf)

        assert result.page_count == 1


# ---------------------------------------------------------------------------
# Image files
# ---------------------------------------------------------------------------


class TestExtractImage:
    def test_method_is_ocr(self, png_image: Path) -> None:
        with patch("app.services.extraction.pytesseract.image_to_string", return_value="text"):
            result = extract(png_image)
        assert result.method == "ocr"

    def test_page_count_is_one(self, png_image: Path) -> None:
        with patch("app.services.extraction.pytesseract.image_to_string", return_value=""):
            result = extract(png_image)
        assert result.page_count == 1

    def test_pytesseract_called_with_image(self, png_image: Path) -> None:
        with patch(
            "app.services.extraction.pytesseract.image_to_string", return_value="result"
        ) as mock_ocr:
            extract(png_image)
        mock_ocr.assert_called_once()
        assert isinstance(mock_ocr.call_args[0][0], Image.Image)

    def test_returns_extraction_result(self, png_image: Path) -> None:
        with patch("app.services.extraction.pytesseract.image_to_string", return_value=""):
            result = extract(png_image)
        assert isinstance(result, ExtractionResult)

    @requires_tesseract
    def test_real_ocr_runs_without_error(self, png_image: Path) -> None:
        result = extract(png_image)
        assert result.method == "ocr"
        assert isinstance(result.text, str)


# ---------------------------------------------------------------------------
# Unsupported and error cases
# ---------------------------------------------------------------------------


class TestExtractEdgeCases:
    def test_unsupported_extension_returns_failed(self, tmp_path: Path) -> None:
        f = tmp_path / "report.docx"
        f.write_bytes(b"not a real docx")
        result = extract(f)
        assert result.method == "failed"
        assert result.text == ""
        assert result.page_count == 0

    def test_missing_file_returns_failed(self, tmp_path: Path) -> None:
        result = extract(tmp_path / "nonexistent.pdf")
        assert result.method == "failed"

    def test_corrupt_pdf_does_not_raise(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"%PDF-1.4\nnot a real pdf")
        result = extract(bad)
        assert isinstance(result, ExtractionResult)
        assert isinstance(result.text, str)

    def test_empty_pdf_page_triggers_ocr_path(
        self, blank_pdf: Path, mock_pil_image: Image.Image
    ) -> None:
        with patch("app.services.extraction._pdf_page_to_pil", return_value=mock_pil_image):
            with patch("app.services.extraction.pytesseract.image_to_string", return_value=""):
                result = extract(blank_pdf)
        assert result.method == "ocr"

    def test_accepts_string_path(self, text_pdf: Path) -> None:
        result = extract(str(text_pdf))
        assert result.method == "pdf"
