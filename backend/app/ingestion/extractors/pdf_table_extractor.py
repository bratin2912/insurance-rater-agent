
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf


@dataclass
class ExtractedTable:
    page_number: int
    table_index: int
    row_count: int
    column_count: int
    bbox: tuple[float, float, float, float]
    rows: list[list[Any]]


@dataclass
class PDFTableExtractionResult:
    page_count: int
    tables: list[ExtractedTable]


class PDFTableExtractor:
    """Detect and extract tables from PDF pages using PyMuPDF."""

    def extract_file(
        self,
        file_path: str | Path,
    ) -> PDFTableExtractionResult:

        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("PDFTableExtractor only supports PDF files.")

        with pymupdf.open(path) as pdf:
            return self._extract(pdf)

    def extract_bytes(
        self,
        content: bytes,
    ) -> PDFTableExtractionResult:

        if not content:
            raise ValueError("PDF content is empty.")

        with pymupdf.open(
            stream=content,
            filetype="pdf",
        ) as pdf:
            return self._extract(pdf)

    @staticmethod
    def _extract(
        pdf: pymupdf.Document,
    ) -> PDFTableExtractionResult:

        extracted_tables = []

        for page_index, page in enumerate(pdf):
            table_finder = page.find_tables()

            for table_index, table in enumerate(
                table_finder.tables,
                start=1,
            ):
                rows = table.extract()

                extracted_tables.append(
                    ExtractedTable(
                        page_number=page_index + 1,
                        table_index=table_index,
                        row_count=len(rows),
                        column_count=max(
                            (len(row) for row in rows),
                            default=0,
                        ),
                        bbox=tuple(table.bbox),
                        rows=rows,
                    )
                )

        return PDFTableExtractionResult(
            page_count=len(pdf),
            tables=extracted_tables,
        )
