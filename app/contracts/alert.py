from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, StrictStr, validator


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StandardAlert(BaseModel):
    alert_id: StrictStr = Field(..., min_length=1)
    source: StrictStr = Field(..., min_length=1)
    occurred_at: datetime
    severity: Severity
    title: StrictStr = Field(..., min_length=1)
    asset_id: StrictStr = Field(..., min_length=1)
    raw_ref: StrictStr = Field(..., min_length=1)

    @validator("alert_id", "source", "title", "asset_id", "raw_ref")
    def required_strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @validator("raw_ref")
    def raw_ref_must_use_training_fixture(cls, value: str) -> str:
        if not value.startswith("fixture://"):
            raise ValueError("must use a fixture:// training reference")
        return value
