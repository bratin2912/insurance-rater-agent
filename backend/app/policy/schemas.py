
from enum import StrEnum
from typing import Annotated, Generic, TypeVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
)


T = TypeVar("T")


def parse_percentage(value):
    """Accept numeric percentages or strings such as '35%'."""
    if isinstance(value, str):
        value = value.strip().replace("%", "").strip()
    return float(value) if value is not None else None


Percentage = Annotated[float, BeforeValidator(parse_percentage)]


class PolicyType(StrEnum):
    COMPREHENSIVE = "comprehensive"
    STANDALONE_OD = "standalone_od"
    STANDALONE_TP = "standalone_tp"
    UNKNOWN = "unknown"


class BusinessType(StrEnum):
    NEW_BUSINESS = "new_business"
    RENEWAL = "renewal"
    ROLLOVER = "rollover"
    PORTED = "ported"
    UNKNOWN = "unknown"


class ExtractionStatus(StrEnum):
    EXTRACTED = "extracted"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


class Evidence(BaseModel):
    source_file: str
    page_number: int | None = None
    excerpt: str | None = None
    location: str | None = None


class ExtractedField(BaseModel, Generic[T]):
    value: T | None = None
    status: ExtractionStatus = ExtractionStatus.NOT_FOUND
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: list[Evidence] = Field(default_factory=list)


class PremiumBreakup(BaseModel):
    od_premium: ExtractedField[float]
    tp_premium: ExtractedField[float]

    other_premium_components: ExtractedField[dict[str, float]]

    total_premium: ExtractedField[float]


class PolicyFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insurer: ExtractedField[str]
    previous_insurer: ExtractedField[str]
    business_type: ExtractedField[BusinessType]

    make: ExtractedField[str]
    model: ExtractedField[str]
    fuel: ExtractedField[str]
    rto: ExtractedField[str]
    engine_capacity_cc: ExtractedField[int]
    manufacture_year: ExtractedField[int]
    vehicle_age_years: ExtractedField[float]

    policy_type: ExtractedField[PolicyType]
    ncb_percentage: ExtractedField[Percentage]

    premium: PremiumBreakup
