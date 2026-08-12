from datetime import datetime
from typing import Literal
from pydantic import BaseModel, StrictStr

## 实现 Contract（数据契约）

# 1.定义CaseBinding（案件绑定契约）
# 严格符合(case_id, investigation_id, status='open')
class CaseBinding(BaseModel):
    case_id: StrictStr
    investigation_id: StrictStr
    status: Literal["open"] = "open"
# 禁止任何未定义的多余字段
    class Config:
        extra = "forbid"

# 2.定义EvidenceRef（证据引用契约）
# 严格符合(evidence_id, source_type='synthetic_alert', source_id, captured_at, content_hash)
class EvidenceRef(BaseModel):
    evidence_id: StrictStr
    source_type: Literal["synthetic_alert"] = "synthetic_alert"
    source_id: StrictStr
    captured_at: datetime
    content_hash: StrictStr
    class Config:
        extra = "forbid"

# 3.定义ContextResult（成功响应契约）
# 严格符合(status='CONTEXT_READY', investigation_id, case_id, evidence_refs, correlation_id)
class ContextResult(BaseModel):
    status: Literal["CONTEXT_READY"] = "CONTEXT_READY"
    investigation_id: StrictStr
    case_id: StrictStr
    evidence_refs: list[StrictStr]
    correlation_id: StrictStr
    class Config:
        extra = "forbid"

# 4.定义DependencyError（依赖错误契约）
# 严格符合(error_code='CASE_EVIDENCE_UNAVAILABLE', message, correlation_id)
class DependencyError(BaseModel):
    error_code: Literal["CASE_EVIDENCE_UNAVAILABLE"] = (
        "CASE_EVIDENCE_UNAVAILABLE"
    )
    message: StrictStr
    correlation_id: StrictStr
    class Config:
        extra = "forbid"
