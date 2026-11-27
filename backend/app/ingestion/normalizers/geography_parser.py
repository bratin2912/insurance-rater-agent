
from dataclasses import asdict, dataclass
from typing import Any

from app.ingestion.extractors.pdf_table_extractor import ExtractedTable


@dataclass
class GeographyMapping:
    insurer: str
    product_line: str
    region: str | None
    state: str
    location: str
    zone: str
    mapping_type: str

    source_page: int
    source_table: int
    source_row: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GeographyParser:
    """
    Parse HDFC ERGO Private Car geographical zone mappings.

    Expected source layout:
        Column 0: Region
        Column 1: State Name
        Columns 2-5: Zone 1 area
        Columns 6-7: Zone 2 area

    Blank state cells continue the preceding state.
    The geography table may continue across PDF pages.
    """

    INSURER = "HDFC ERGO"
    PRODUCT_LINE = "Private Car"

    REGION_COLUMN = 0
    STATE_COLUMN = 1

    ZONE_COLUMNS = {
        "ZONE_1": (3, 4, 5),
        "ZONE_2": (6, 7),
    }

    def parse_document(
        self,
        tables: list[ExtractedTable],
    ) -> list[GeographyMapping]:
        """Find and parse all geography tables in the document."""

        geography_tables = [
            table
            for table in tables
            if self._contains_geography_header(table)
        ]

        if not geography_tables:
            raise ValueError("No geography tables found in the PDF.")

        geography_tables.sort(
            key=lambda table: (table.page_number, table.table_index)
        )

        mappings = []
        current_state = None
        current_region = None

        for table in geography_tables:
            header_index = self._find_header_index(table)

            for row_index in range(header_index + 1, len(table.rows)):
                row = table.rows[row_index]

                if len(row) < 8:
                    raise ValueError(
                        f"Unexpected geography row width at "
                        f"page {table.page_number}, "
                        f"row {row_index + 1}."
                    )

                region_value = self._clean(row[self.REGION_COLUMN])
                state_value = self._clean(row[self.STATE_COLUMN])

                # Region labels apply to subsequent state rows.
                if region_value:
                    current_region = region_value

                # State names continue into subsequent blank rows.
                if state_value:
                    current_state = state_value

                # Ignore rows that cannot be associated with a state.
                if not current_state:
                    continue

                for zone, column_indexes in self.ZONE_COLUMNS.items():
                    for column_index in column_indexes:
                        location = self._clean(row[column_index])

                        if not location:
                            continue

                        mappings.append(
                            GeographyMapping(
                                insurer=self.INSURER,
                                product_line=self.PRODUCT_LINE,
                                region=current_region,
                                state=current_state,
                                location=location,
                                zone=zone,
                                mapping_type=self._mapping_type(
                                    current_state,
                                    location,
                                ),
                                source_page=table.page_number,
                                source_table=table.table_index,
                                source_row=row_index + 1,
                            )
                        )

        self.validate(mappings)

        return mappings

    @staticmethod
    def _clean(value: Any) -> str | None:
        if value is None:
            return None

        cleaned = " ".join(str(value).split())

        return cleaned if cleaned else None

    @classmethod
    def _contains_geography_header(
        cls,
        table: ExtractedTable,
    ) -> bool:
        return cls._find_header_index(table) is not None

    @classmethod
    def _find_header_index(
        cls,
        table: ExtractedTable,
    ) -> int | None:
        for index, row in enumerate(table.rows):
            normalized = [
                str(value).strip().upper() if value is not None else ""
                for value in row
            ]

            if (
                "STATE NAME" in normalized
                and "ZONE-1" in normalized
                and "ZONE-2" in normalized
            ):
                return index

        return None

    @staticmethod
    def _mapping_type(state: str, location: str) -> str:
        """Classify the relationship without inferring geography."""

        if state.casefold() == location.casefold():
            return "STATE_WIDE"

        if location.casefold().startswith("rest of "):
            return "REMAINDER"

        return "LOCATION"

    @staticmethod
    def validate(mappings: list[GeographyMapping]) -> None:
        if not mappings:
            raise ValueError("No geography mappings were extracted.")

        unique_keys = {
            (
                mapping.state.casefold(),
                mapping.location.casefold(),
                mapping.zone,
            )
            for mapping in mappings
        }

        if len(unique_keys) != len(mappings):
            raise ValueError("Duplicate geography mappings detected.")

        for mapping in mappings:
            if mapping.zone not in {"ZONE_1", "ZONE_2"}:
                raise ValueError(
                    f"Invalid zone: {mapping.zone}"
                )

            if not mapping.state or not mapping.location:
                raise ValueError(
                    "Geography mapping has an empty state or location."
                )
