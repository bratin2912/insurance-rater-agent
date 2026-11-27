
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ingestion.schemas.source import SourceReferenceSchema


class CommissionRuleSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    schema_version: Literal["1.0"] = "1.0"

    insurer: str = Field(min_length=1)
    product_line: str = Field(min_length=1)

    zone: Literal["ZONE_1", "ZONE_2"]
    business_type: Literal["PACKAGE", "SAOD"]
    fuel_type: Literal["PETROL", "NON_PETROL"]

    ncb_type: Literal[
        "NCB_AND_N_NCB",
        "NCB",
        "N_NCB",
    ]

    # Preserve the insurer's original slab label.
    # Do not infer numeric boundaries at this stage.
    gwp_slab: str = Field(min_length=1)

    commission_rate: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
        decimal_places=2,
    )

    source: SourceReferenceSchema
