
from dataclasses import asdict, dataclass
from typing import Any

from app.ingestion.extractors.pdf_table_extractor import ExtractedTable


@dataclass
class CommissionRule:
    insurer: str
    product_line: str
    zone: str
    business_type: str
    fuel_type: str
    ncb_type: str
    gwp_slab: str
    commission_rate: float

    source_page: int
    source_table: int
    source_row: int
    source_column: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CommissionGridParser:
    """
    Parse the HDFC ERGO Private Car commission grid.

    Expected table layout:
        Column 1: GWP slab
        Columns 2-4: Package rates
        Columns 5-7: SAOD rates

    The first four rows contain hierarchical headers.
    Commission data starts at row index 4.
    """

    INSURER = "HDFC ERGO"
    PRODUCT_LINE = "Private Car"

    # Table columns are zero-indexed.
    COLUMN_MAPPING = {
        1: ("PACKAGE", "PETROL", "NCB_AND_N_NCB"),
        2: ("PACKAGE", "NON_PETROL", "NCB"),
        3: ("PACKAGE", "NON_PETROL", "N_NCB"),
        4: ("SAOD", "PETROL", "NCB_AND_N_NCB"),
        5: ("SAOD", "NON_PETROL", "NCB"),
        6: ("SAOD", "NON_PETROL", "N_NCB"),
    }

    # Data rows are zero-indexed.
    DATA_START_ROW = 4
    EXPECTED_DATA_ROWS = 5
    EXPECTED_COLUMNS = 7

    def parse_table(
        self,
        table: ExtractedTable,
        zone: str,
    ) -> list[CommissionRule]:
        """Parse one commission grid into normalized rules."""

        zone = zone.upper().replace(" ", "_")

        if zone not in {"ZONE_1", "ZONE_2"}:
            raise ValueError(f"Unsupported zone: {zone}")

        if table.column_count != self.EXPECTED_COLUMNS:
            raise ValueError(
                f"{zone}: Expected {self.EXPECTED_COLUMNS} columns, "
                f"found {table.column_count}."
            )

        if len(table.rows) != 9:
            raise ValueError(
                f"{zone}: Expected 9 rows including headers, "
                f"found {len(table.rows)}."
            )

        rules = []

        data_rows = table.rows[self.DATA_START_ROW:]

        if len(data_rows) != self.EXPECTED_DATA_ROWS:
            raise ValueError(
                f"{zone}: Expected {self.EXPECTED_DATA_ROWS} "
                f"commission rows, found {len(data_rows)}."
            )

        for row_index, row in enumerate(
            data_rows,
            start=self.DATA_START_ROW,
        ):
            if len(row) != self.EXPECTED_COLUMNS:
                raise ValueError(
                    f"{zone}, row {row_index + 1}: "
                    f"Expected 7 cells, found {len(row)}."
                )

            gwp_slab = self._required_text(
                row[0],
                f"{zone}, row {row_index + 1}, GWP slab",
            )

            for column_index, dimensions in self.COLUMN_MAPPING.items():
                raw_rate = row[column_index]

                commission_rate = self._parse_rate(
                    raw_rate,
                    zone=zone,
                    row_number=row_index + 1,
                    column_number=column_index + 1,
                )

                business_type, fuel_type, ncb_type = dimensions

                rules.append(
                    CommissionRule(
                        insurer=self.INSURER,
                        product_line=self.PRODUCT_LINE,
                        zone=zone,
                        business_type=business_type,
                        fuel_type=fuel_type,
                        ncb_type=ncb_type,
                        gwp_slab=gwp_slab,
                        commission_rate=commission_rate,
                        source_page=table.page_number,
                        source_table=table.table_index,
                        source_row=row_index + 1,
                        source_column=column_index + 1,
                    )
                )

        return rules

    def parse_document(
        self,
        tables: list[ExtractedTable],
    ) -> list[CommissionRule]:
        """
        Parse the two HDFC ERGO commission grids.

        In this source document:
            Page 1, Table 1 = Zone 1
            Page 1, Table 2 = Zone 2
        """

        table_lookup = {
            (table.page_number, table.table_index): table
            for table in tables
        }

        required_tables = {
            (1, 1): "ZONE_1",
            (1, 2): "ZONE_2",
        }

        all_rules = []

        for source_location, zone in required_tables.items():
            table = table_lookup.get(source_location)

            if table is None:
                raise ValueError(
                    f"Missing expected commission table at "
                    f"page {source_location[0]}, "
                    f"table {source_location[1]}."
                )

            all_rules.extend(
                self.parse_table(table, zone)
            )

        self.validate(all_rules)

        return all_rules

    @staticmethod
    def _required_text(value: Any, field_name: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError(f"Missing required value: {field_name}")

        return str(value).strip()

    @staticmethod
    def _parse_rate(
        value: Any,
        zone: str,
        row_number: int,
        column_number: int,
    ) -> float:
        """Convert a percentage cell such as '17.50%' to 17.5."""

        if value is None:
            raise ValueError(
                f"Missing commission rate: {zone}, "
                f"row {row_number}, column {column_number}."
            )

        raw_value = str(value).strip().replace(",", "")

        if not raw_value.endswith("%"):
            raise ValueError(
                f"Expected percentage at {zone}, "
                f"row {row_number}, column {column_number}; "
                f"found {value!r}."
            )

        try:
            rate = float(raw_value[:-1].strip())
        except ValueError as exc:
            raise ValueError(
                f"Invalid commission rate {value!r} at {zone}, "
                f"row {row_number}, column {column_number}."
            ) from exc

        if not 0 <= rate <= 100:
            raise ValueError(
                f"Commission rate outside 0-100 range: {rate}."
            )

        return rate

    @staticmethod
    def validate(rules: list[CommissionRule]) -> None:
        """Validate the expected grid dimensions and uniqueness."""

        if len(rules) != 60:
            raise ValueError(
                f"Expected 60 commission rules, found {len(rules)}."
            )

        zones = {rule.zone for rule in rules}

        if zones != {"ZONE_1", "ZONE_2"}:
            raise ValueError(f"Unexpected zones: {zones}")

        unique_keys = {
            (
                rule.zone,
                rule.business_type,
                rule.fuel_type,
                rule.ncb_type,
                rule.gwp_slab,
            )
            for rule in rules
        }

        if len(unique_keys) != len(rules):
            raise ValueError("Duplicate commission rule combinations found.")

        for zone in zones:
            zone_rules = [
                rule for rule in rules
                if rule.zone == zone
            ]

            if len(zone_rules) != 30:
                raise ValueError(
                    f"{zone}: Expected 30 rules, "
                    f"found {len(zone_rules)}."
                )
