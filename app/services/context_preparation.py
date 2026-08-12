import copy
from app.adapters.case_evidence_stub import case_evidence_stub
from app.contracts.case_evidence import (
    CaseBinding,
    ContextResult,
    DependencyError,
    EvidenceRef,
)
from app.ports.case_evidence import CaseEvidencePort
from app.services.idempotency import InMemoryIdempotencyStore, idempotency_store

##这是API路由和底层数据/外部服务之间的桥梁

#这是为了处理未知ID返回404的场景而准备的
# 当业务层发现查不到Investigation时，抛出这个异常
# API路由层捕获到它后，就会返回404
class InvestigationNotFoundError(Exception):
    pass

#通过构造函数接收数据
class ContextPreparationService:
    def __init__(
        self,
        investigation_store: InMemoryIdempotencyStore,
        case_evidence_port: CaseEvidencePort,
    ) -> None:
        self._investigation_store = investigation_store
        self._case_evidence_port = case_evidence_port
        #case_bindings和_evidence_refs是两个字典
        #要求成功后才保存case与引用
        #这两个字典就是用来在内存中保存成功结果的仓库
        self._case_bindings: dict[str, CaseBinding] = {}
        self._evidence_refs: dict[str, list[EvidenceRef]] = {}

## 这是整个服务的主入口
# 输入是 investigation_id
# 输出要么是成功的 ContextResult，要么是失败的 DependencyError
    def prepare_context(
        self,
        investigation_id: str,
    ) -> ContextResult | DependencyError:
        # 先去内存数据库里查investigation
        investigation = self._investigation_store.get_by_investigation_id(
            investigation_id
        )
        # 如果查不到，直接抛出异常，不会往下执行调用 Stub
        if investigation is None:
            raise InvestigationNotFoundError()
        # 如果查到了，立刻从数据库记录中提取出correlation_id 为后续使用做准备
        correlation_id = investigation["correlation_id"]
        # 确认 Investigation 存在后，才会调用 Port（Stub）
        port_result = self._case_evidence_port.load_context(
            investigation_id=investigation_id,
            correlation_id=correlation_id,
        )
        # 如果 Stub 返回了 DependencyError，业务层直接把错误对象原封不动地返回给上层
        if isinstance(port_result, DependencyError):
            return port_result
        # 走到这里说明外部服务可用，将数据存入内部字典
        # 将数据组装成测试期望的冻结契约ContextResult，并保留已保存的correlation_id
        case_binding, evidence_refs = port_result
        self._case_bindings[investigation_id] = copy.deepcopy(case_binding)
        self._evidence_refs[investigation_id] = copy.deepcopy(evidence_refs)
        return ContextResult(
            investigation_id=investigation_id,
            case_id=case_binding.case_id,
            evidence_refs=[ref.evidence_id for ref in evidence_refs],
            correlation_id=correlation_id,
        )


context_preparation_service = ContextPreparationService(
    investigation_store=idempotency_store,
    case_evidence_port=case_evidence_stub,
)
