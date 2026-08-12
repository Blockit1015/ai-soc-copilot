from typing import Protocol
from app.contracts.case_evidence import CaseBinding, DependencyError, EvidenceRef

## 实现Port（接口）定义
class CaseEvidencePort(Protocol):  #定义了外部查案服务的交互标准
    #定义方法签名
    def load_context(
        self,
        investigation_id: str, #输入数据，告诉服务去查哪个调查记录
        correlation_id: str,  #输入数据，把追踪标识传进去
    ) -> tuple[CaseBinding, list[EvidenceRef]] | DependencyError:
        ...
        #返回值有两种结果：
        # 成功: 返回[CaseBinding, list[EvidenceRef]]（案件绑定 + 证据列表）
        # 失败: 返回错误契约
