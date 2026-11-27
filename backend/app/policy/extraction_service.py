
import json
import re
from pathlib import Path

from pydantic import ValidationError

from app.ai.llm.gemini_client import GeminiClient, get_gemini_client
from app.ingestion.loaders.pdf_loader import PDFDocument
from app.policy.schemas import PolicyFacts


class PolicyExtractionError(Exception):
    """Raised when policy fact extraction fails."""


class PolicyExtractionService:
    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self.gemini = gemini_client or get_gemini_client()

    def extract(
        self,
        document: PDFDocument,
        source_file: str,
    ) -> PolicyFacts:
        if not document.pages:
            raise PolicyExtractionError("PDF contains no pages.")

        page_texts = {
            page.page_number: page.text
            for page in document.pages
        }

        if not any(text.strip() for text in page_texts.values()):
            raise PolicyExtractionError(
                "No readable text found in the PDF."
            )

        filename = Path(source_file).name

        prompt = self._build_prompt(
            page_texts=page_texts,
            source_file=filename,
        )

        try:
            response_text = self.gemini.generate_json(prompt)
            payload = json.loads(response_text)
            facts = PolicyFacts.model_validate(payload)

        except json.JSONDecodeError as exc:
            raise PolicyExtractionError(
                "Gemini returned invalid JSON."
            ) from exc

        except ValidationError as exc:
            raise PolicyExtractionError(
                f"Policy facts failed schema validation: {exc}"
            ) from exc

        self._validate_evidence(
            facts=facts,
            page_texts=page_texts,
            source_file=filename,
        )

        return facts

    @staticmethod
    def _build_prompt(
        page_texts: dict[int, str],
        source_file: str,
    ) -> str:
        pages = []

        for page_number, text in page_texts.items():
            pages.append(
                f"\n--- PAGE {page_number} ---\n{text}"
            )

        document_text = "\n".join(pages)

        return f"""
You are an insurance policy data extraction system.

Your task is to extract structured facts from the supplied
motor insurance policy.

SOURCE FILE: {source_file}

IMPORTANT EXTRACTION RULES:

1. Use only information explicitly supported by the document.
2. Never guess or infer missing values.
3. Use null when a value cannot be established.
4. Every field must contain:
   - value
   - status
   - confidence
   - evidence
5. Allowed statuses:
   - extracted
   - ambiguous
   - not_found
6. Every extracted or ambiguous value must have at least
   one evidence reference.
7. Evidence excerpts must be short, verbatim text copied
   from the document.
8. Evidence must contain the actual page number.
9. Do not confuse basic OD premium with net OD premium.
10. Extract basic OD and basic TP premiums separately.
11. Extract NCB as a numeric percentage.
    Example: 35.0, NOT "35%".
12. Do not infer fuel type from the vehicle make or model.
13. Do not infer business type merely because current and
    previous insurers are different.
14. If current insurer and previous insurer are explicitly
    the same, classify business_type as renewal.
15. If business type cannot be established:
    value = null
    status = not_found
    confidence = null
    evidence = []
16. A comprehensive policy includes OD and TP.
17. A standalone TP policy has OD as not applicable.
    Do not represent OD as zero.
18. Do not calculate commission rates or premium amounts.
19. Do not derive vehicle age unless the relevant dates
    are explicitly available and the calculation is clear.

PREMIUM EXTRACTION RULES:

- od_premium: basic OD premium, when explicitly available.
- tp_premium: basic TP premium, when explicitly available.
- other_premium_components: other identifiable premium
  components, represented as a dictionary of component
  names and numeric INR amounts.
- total_premium: total policy premium, when explicitly available.

Do not substitute net OD premium for basic OD premium.
Do not substitute net liability premium for basic TP premium.
Do not combine different premium components.

OUTPUT FORMAT:

Return ONLY valid JSON matching the existing PolicyFacts
Pydantic schema.

Every regular field must follow this structure:

{{
    "value": "example",
    "status": "extracted",
    "confidence": 0.98,
    "evidence": [
        {{
            "source_file": "{source_file}",
            "page_number": 1,
            "excerpt": "Exact text copied from the document",
            "location": "Policy schedule"
        }}
    ]
}}

For a numeric percentage, return a number:

{{
    "value": 35.0,
    "status": "extracted",
    "confidence": 0.98,
    "evidence": [...]
}}

For a field that cannot be established:

{{
    "value": null,
    "status": "not_found",
    "confidence": null,
    "evidence": []
}}

For other_premium_components, use this structure:

{{
    "value": {{
        "LL to Paid Driver": 50.0,
        "LL for Employees": 350.0
    }},
    "status": "extracted",
    "confidence": 0.95,
    "evidence": [...]
}}

If no other components are explicitly identified, use:

{{
    "value": {{}},
    "status": "not_found",
    "confidence": null,
    "evidence": []
}}

SCHEMA FIELDS:

insurer
previous_insurer
business_type
make
model
fuel
rto
engine_capacity_cc
manufacture_year
vehicle_age_years
policy_type
ncb_percentage

premium:
    od_premium
    tp_premium
    other_premium_components
    total_premium

Allowed business_type values:
new_business, renewal, rollover, ported, unknown.

Allowed policy_type values:
comprehensive, standalone_od, standalone_tp, unknown.

Allowed extraction status values:
extracted, ambiguous, not_found.

For policy_type, use unknown with status not_found if it
cannot be established.

For business_type, use null with status not_found if it
cannot be established.

For a standalone TP policy, do not assign an OD premium
of zero. Use the schema's not-found representation for
the OD premium until applicability is represented
explicitly in the schema.

DOCUMENT CONTENT:

{document_text}
"""

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(
            r"\s+",
            " ",
            value,
        ).strip().casefold()

    def _validate_evidence(
        self,
        facts: PolicyFacts,
        page_texts: dict[int, str],
        source_file: str,
    ) -> None:
        for field_name, field in facts:
            if field_name == "premium":
                for nested_name, nested_field in field:
                    self._check_field_evidence(
                        field_name=f"premium.{nested_name}",
                        field=nested_field,
                        page_texts=page_texts,
                        source_file=source_file,
                    )
            else:
                self._check_field_evidence(
                    field_name=field_name,
                    field=field,
                    page_texts=page_texts,
                    source_file=source_file,
                )

    def _check_field_evidence(
        self,
        field_name: str,
        field,
        page_texts: dict[int, str],
        source_file: str,
    ) -> None:
        status = field.status.value

        if status == "not_found":
            if field.value is not None and field.value != {}:
                raise PolicyExtractionError(
                    f"{field_name}: not_found field has a value."
                )

            if field.evidence:
                raise PolicyExtractionError(
                    f"{field_name}: not_found field has evidence."
                )

            return

        if field.value is None:
            raise PolicyExtractionError(
                f"{field_name}: extracted/ambiguous field "
                "has no value."
            )

        if not field.evidence:
            raise PolicyExtractionError(
                f"{field_name}: missing evidence."
            )

        for evidence in field.evidence:
            if evidence.source_file != source_file:
                raise PolicyExtractionError(
                    f"{field_name}: incorrect source filename."
                )

            page_text = page_texts.get(evidence.page_number)

            if page_text is None:
                raise PolicyExtractionError(
                    f"{field_name}: invalid evidence page "
                    f"{evidence.page_number}."
                )

            if not evidence.excerpt:
                raise PolicyExtractionError(
                    f"{field_name}: empty evidence excerpt."
                )

            normalized_excerpt = self._normalize_text(
                evidence.excerpt
            )
            normalized_page = self._normalize_text(page_text)
            
            if normalized_excerpt not in normalized_page:
                raise PolicyExtractionError(
                    f"{field_name}: evidence excerpt could not be verified.\n"
                    f"Page: {evidence.page_number}\n"
                    f"Excerpt returned by Gemini: {evidence.excerpt!r}\n"
                    f"Normalized excerpt: {normalized_excerpt!r}"
                )
            