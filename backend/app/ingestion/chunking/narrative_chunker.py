
from dataclasses import dataclass
from typing import Any


@dataclass
class NarrativeChunk:
    chunk_id: str
    content: str
    metadata: dict[str, Any]


class NarrativeChunker:
    """
    Converts extracted business rules into searchable narrative chunks.

    For this HDFC PDF, each business rule is short and self-contained.
    Therefore, one rule per chunk is more useful than splitting it
    into arbitrary token windows.
    """

    def chunk_business_rules(
        self,
        records: list[dict[str, Any]],
        document_id: str,
        effective_from: str,
    ) -> list[NarrativeChunk]:

        chunks: list[NarrativeChunk] = []

        for record in records:
            rule_code = record["rule_code"]

            content = "\n".join(
                [
                    f"Insurer: {record['insurer']}",
                    f"Product: {record['product_line']}",
                    f"Business rule: {record['description']}",
                    f"Rule category: {record['category']}",
                    f"Original source text: {record['source_text']}",
                ]
            )

            source = record.get("source", {})

            metadata = {
                "document_id": document_id,
                "insurer": record["insurer"],
                "product_line": record["product_line"],
                "effective_from": effective_from,
                "document_type": "commission_grid",
                "chunk_type": "business_rule",
                "rule_code": rule_code,
                "category": record["category"],
                "source_page": source["page"],
            }

            if source.get("table") is not None:
                metadata["source_table"] = source["table"]

            chunk_id = (
                f"{document_id}_"
                f"{rule_code.lower()}"
            )

            chunks.append(
                NarrativeChunk(
                    chunk_id=chunk_id,
                    content=content,
                    metadata=metadata,
                )
            )

        return chunks
