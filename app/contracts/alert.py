from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, StrictStr, validator

#这里定义了一个告警的标准格式，叫 StandardAlert。它有几个字段：
# alert_id: 告警的唯一ID
# source: 告警的来源
# occurred_at: 告警发生的时间
# severity: 告警的严重级别LOW, MEDIUM, HIGH, CRITICAL）。
# title: 告警的标题
# asset_id: 告警关联的资产ID
# raw_ref: 告警的原始参考

### 当发来请求时，FastAPI会拿此文件里的标准格式规则去“核对”发来的数据，如果不符合，就会触发422错误 ###

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
