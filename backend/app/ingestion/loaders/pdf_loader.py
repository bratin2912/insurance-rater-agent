
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image


@dataclass
class PDFPage:
    page_number: int
    text: str
    character_count: int
    extraction_method: str


@dataclass
class PDFDocument:
    page_count: int
    pages: list[PDFPage]


class PDFLoader:
    """Extract text from PDFs, using OCR for scanned pages."""

    OCR_DPI = 250
    MIN_TEXT_LENGTH = 20

    def load_file(self, file_path: str | Path) -> PDFDocument:
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("PDFLoader only supports PDF files.")

        with pymupdf.open(path) as pdf:
            return self._extract(pdf)

    def load_bytes(self, content: bytes) -> PDFDocument:
        if not content:
            raise ValueError("PDF content is empty.")

        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            return self._extract(pdf)

    def _extract(self, pdf: pymupdf.Document) -> PDFDocument:
        pages = []

        for index, page in enumerate(pdf):
            text = page.get_text("text").strip()

            if len(text) >= self.MIN_TEXT_LENGTH:
                method = "native_text"
            else:
                text = self._extract_with_ocr(page)
                method = "ocr"

            pages.append(
                PDFPage(
                    page_number=index + 1,
                    text=text,
                    character_count=len(text),
                    extraction_method=method,
                )
            )

        return PDFDocument(
            page_count=len(pages),
            pages=pages,
        )

    def _extract_with_ocr(self, page: pymupdf.Page) -> str:
        scale = self.OCR_DPI / 72

        matrix = pymupdf.Matrix(scale, scale)
        pixmap = page.get_pixmap(
            matrix=matrix,
            colorspace=pymupdf.csRGB,
            alpha=False,
        )

        image = Image.open(
            BytesIO(pixmap.tobytes("png"))
        )

        try:
            return pytesseract.image_to_string(
                image,
                lang="eng",
                config="--psm 3",
            ).strip()
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract OCR is not installed. "
                "Install it using: sudo apt install tesseract-ocr"
            ) from exc
