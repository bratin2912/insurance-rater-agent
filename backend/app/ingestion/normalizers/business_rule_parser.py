
import re
from dataclasses import asdict, dataclass
from typing import Any

from app.ingestion.loaders.pdf_loader import PDFDocument


@dataclass
class BusinessRule:
    insurer: str
    product_line: str
    rule_code: str
    category: str
    description: str
    source_text: str
    source_page: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BusinessRuleParser:
    """
    Extract known business rules from the HDFC ERGO
    Private Car commission PDF.

    This parser preserves the original extracted wording.
    It does not infer additional conditions.
    """

    INSURER = "HDFC ERGO"
    PRODUCT_LINE = "Private Car"

    RULE_PATTERNS = [
        {
            "rule_code": "GWP_SLAB_BASIS",
            "category": "SLAB_CALCULATION",
            "pattern": (
                r"Slab will be calculated basis "
                r"comprehensive\s*\+\s*SAOD GWP "
                r"on PVT CAR "
                r"\(SATP premium is excluded for slab achievement\)"
            ),
        },
        {
            "rule_code": "SATP_PREMIUM_EXCLUSION",
            "category": "PREMIUM_EXCLUSION",
            "pattern": (
                r"SATP premium is excluded for slab achievement"
            ),
        },
        {
            "rule_code": "NON_PETROL_FUEL_CLASSIFICATION",
            "category": "FUEL_CLASSIFICATION",
            "pattern": (
                r"Non Petrol includes Diesel,\s*CNG,\s*LPG"
            ),
        },
        {
            "rule_code": "NEW_BUSINESS_NCB",
            "category": "NCB_CLASSIFICATION",
            "pattern": (
                r"New Business will be considered as NCB"
            ),
        },
        {
            "rule_code": "EV_HYBRID_PETROL_GRID",
            "category": "FUEL_CLASSIFICATION",
            "pattern": (
                r"EV and Hybrid is to be considered in Petrol Grid"
            ),
        },
    ]

    def parse_document(
        self,
        document: PDFDocument,
    ) -> list[BusinessRule]:
        """Extract supported business rules from PDF pages."""

        extracted_rules = []

        for page in document.pages:
            normalized_text = self._normalize_text(page.text)

            for definition in self.RULE_PATTERNS:
                match = re.search(
                    definition["pattern"],
                    normalized_text,
                    flags=re.IGNORECASE,
                )

                if not match:
                    continue

                source_text = match.group(0)

                extracted_rules.append(
                    BusinessRule(
                        insurer=self.INSURER,
                        product_line=self.PRODUCT_LINE,
                        rule_code=definition["rule_code"],
                        category=definition["category"],
                        description=source_text,
                        source_text=source_text,
                        source_page=page.page_number,
                    )
                )

        self.validate(extracted_rules)

        return extracted_rules

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize whitespace without changing rule meaning."""

        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def validate(rules: list[BusinessRule]) -> None:
        expected_codes = {
            "GWP_SLAB_BASIS",
            "SATP_PREMIUM_EXCLUSION",
            "NON_PETROL_FUEL_CLASSIFICATION",
            "NEW_BUSINESS_NCB",
            "EV_HYBRID_PETROL_GRID",
        }

        actual_codes = {
            rule.rule_code for rule in rules
        }

        missing = expected_codes - actual_codes
        duplicates = len(rules) != len(actual_codes)

        if missing:
            raise ValueError(
                f"Missing expected business rules: {sorted(missing)}"
            )

        if duplicates:
            raise ValueError(
                "Duplicate business rules detected."
            )

        if actual_codes != expected_codes:
            raise ValueError(
                "Unexpected business-rule set detected."
            )
