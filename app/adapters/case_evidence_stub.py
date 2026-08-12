from datetime import datetime, timezone
from typing import Literal
from app.contracts.case_evidence import CaseBinding, DependencyError, EvidenceRef
from app.ports.case_evidence import CaseEvidencePort

#定义模式类型
StubMode = Literal["available", "unavailable"]

# 继承了CaseEvidencePort，承诺遵守Port接口规矩
class CaseEvidenceStub(CaseEvidencePort):
     # 这就是测试代码里调用的case_evidence_stub.set_mode(unavailable) 方法
    def set_mode(self, mode: StubMode) -> None:
        if mode not in ("available", "unavailable"):
            raise ValueError("mode must be 'available' or 'unavailable'")
        self._mode = mode

    def __init__(self, mode: StubMode = "available") -> None:   # 初始化时默认状态是available
            self.set_mode(mode)

     # 当模式是unavailable时，直接返回一个冻结的对象，并且把传进来的correlation_id原封不动地塞进去
    def load_context(
        self,
        investigation_id: str,
        correlation_id: str,
    ) -> tuple[CaseBinding, list[EvidenceRef]] | DependencyError:
        if self._mode == "unavailable":
            return DependencyError(
                message="teaching stub is unavailable",
                correlation_id=correlation_id,
            )
     #当模式是available时，返回第6节规定的固定假数据的CaseBinding和EvidenceRef对象
        case_binding = CaseBinding(
            case_id="case-demo-001",
            investigation_id=investigation_id,
        )
        evidence_ref = EvidenceRef(
            evidence_id="ev-demo-001",
            source_id="alert-demo-001",
            captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            content_hash=(
                "11111111111111111111111111111111"
                "11111111111111111111111111111111"
            ),
        )
        return case_binding, [evidence_ref]

case_evidence_stub = CaseEvidenceStub()
