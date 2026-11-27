
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass
class PDFPage:
    page_number: int
    text: str
    character_count: int


@dataclass
class PDFDocument:
    page_count: int
    pages: list[PDFPage]


class PDFLoader:
    """Extract text from PDF documents while retaining page numbers."""

    def load_file(self, file_path: str | Path) -> PDFDocument:
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("PDFLoader only supports PDF files.")

        with fitz.open(path) as pdf:
            return self._extract(pdf)

    def load_bytes(self, content: bytes) -> PDFDocument:
        """Extract text directly from PDF bytes."""

        if not content:
            raise ValueError("PDF content is empty.")

        with fitz.open(stream=content, filetype="pdf") as pdf:
            return self._extract(pdf)

    @staticmethod
    def _extract(pdf: fitz.Document) -> PDFDocument:
        pages = []

        for index, page in enumerate(pdf):
            text = page.get_text("text").strip()

            pages.append(
                PDFPage(
                    page_number=index + 1,
                    text=text,
                    character_count=len(text),
                )
            )

        return PDFDocument(
            page_count=len(pages),
            pages=pages,
        )
