
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ingestion.schemas.source import SourceReferenceSchema


class BusinessRuleSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    schema_version: Literal["1.0"] = "1.0"

    insurer: str = Field(min_length=1)
    product_line: str = Field(min_length=1)

    rule_code: str = Field(min_length=1)
    category: str = Field(min_length=1)

    description: str = Field(min_length=1)
    source_text: str = Field(min_length=1)

    source: SourceReferenceSchema
