from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ingestion.schemas.source import SourceReferenceSchema


class GeographyMappingSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    schema_version: Literal["1.0"] = "1.0"

    insurer: str = Field(min_length=1)
    product_line: str = Field(min_length=1)

    region: str | None = None
    state: str = Field(min_length=1)
    location: str = Field(min_length=1)

    zone: Literal["ZONE_1", "ZONE_2"]

    mapping_type: Literal[
        "STATE_WIDE",
        "LOCATION",
        "REMAINDER",
    ]

    source: SourceReferenceSchema
