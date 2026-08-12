##这是RED测试##
from fastapi.testclient import TestClient

#定义标准化、格式正确的测试工具：
#用的还是test_investigation_intake.py里的“假数据”（Fixture）
ALERT_FIXTURE = {
    "alert_id": "alert-fixture-001",
    "source": "training-siem",
    "occurred_at": "2026-07-30T01:00:00Z",
    "severity": "high",
    "title": "Repeated failed sign-in in training tenant",
    "asset_id": "asset-fixture-001",
    "raw_ref": "fixture://alerts/alert-fixture-001",
}

#这是一个辅助函数，它封装了POST接收警告接口调用逻辑
#在测试这个新接口之前，系统里必须得先有一条真实存在的调查记录（Investigation）。
#这个函数自动去创建这条记录，并且提取并返回系统生成的investigation_id和传入的correlation_id
def create_existing_investigation(
    client: TestClient,
    *,
    idempotency_key: str,
    correlation_id: str,
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/investigations",
        headers={
            "Idempotency-Key": idempotency_key,
            "X-Correlation-ID": correlation_id,
        },
        json=ALERT_FIXTURE,
    )

    assert response.status_code == 201
    investigation = response.json()
    return investigation["investigation_id"], investigation["correlation_id"]

#定义测试用例（三个场景）：

## 场景一：成功
#调用上面的辅助函数，拿到真实的investigation_id和saved_correlation_id
#使用TestClient向今天的新接口 POST /api/v1/investigations/{id}/context发送请求
#检查返回结果。
def test_existing_investigation_returns_frozen_context_with_saved_correlation_id() -> None:
    from app.main import app

    client = TestClient(app)
    investigation_id, saved_correlation_id = create_existing_investigation(
        client,
        idempotency_key="idem-d03-context-success",
        correlation_id="corr-d03-context-success",
    )

    response = client.post(
        f"/api/v1/investigations/{investigation_id}/context"
    )
#提出冻结契约要求：
#状态码必须是200。
#返回的JSON必须和右边的字典严格相等
#不仅要有固定的假数据，还必须包含准备阶段生成的investigation_id和saved_correlation_id
#它强制要求未来的开发者在写代码时，绝对不能随意更改返回的字段名，也不能遗漏correlation_id的传递
    assert response.status_code == 200
    assert response.json() == {
        "status": "CONTEXT_READY",
        "investigation_id": investigation_id,
        "case_id": "case-demo-001",
        "evidence_refs": ["ev-demo-001"],
        "correlation_id": saved_correlation_id,
    }

## 场景二：未知ID测试——返回404
#且响应不生成 `correlation_id`、`case_id` 或 `evidence_refs`
def test_unknown_investigation_returns_404_without_context_identifiers() -> None:
    from app.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/investigations/inv-unknown-001/context"  #准备一个“不存在的假ID
    )

    assert response.status_code == 404     #验证错误状态码，要求系统必须诚实地返回404
    #验证不捏造数据，当系统查不到数据时，返回的JSON里绝对不能包含这些敏感的业务字段
    payload = response.json()
    assert "correlation_id" not in payload
    assert "case_id" not in payload
    assert "evidence_refs" not in payload

## 场景三：既有investigation在Stub（假审查程序）不可用时返回 503
def test_existing_investigation_returns_503_when_stub_is_unavailable() -> None:
    from app.adapters.case_evidence_stub import case_evidence_stub
    from app.main import app

    client = TestClient(app)
    #调用辅助函数，在系统里创建一条真实存在的调查记录
    investigation_id, saved_correlation_id = create_existing_investigation(
        client,
        idempotency_key="idem-d03-context-unavailable",
        correlation_id="corr-d03-context-unavailable",
    )
    #模拟依赖服务崩溃
    case_evidence_stub.set_mode("unavailable") #在发请求前，把假审查程序（Stub）的开关拨到不可用状态
    #无论测试成功还是失败，测试结束后都会把 Stub 拨回 "available" 状态
    try:
        response = client.post(
            f"/api/v1/investigations/{investigation_id}/context"
        )
    finally:
        case_evidence_stub.set_mode("available")
    #验证是否返回了错误状态码503
    assert response.status_code == 503
    payload = response.json()
    assert payload["error_code"] == "CASE_EVIDENCE_UNAVAILABLE"
    assert payload["message"] == "teaching stub is unavailable"
    #验证是否保留correlation_id，且不捏造数据
    assert payload["correlation_id"] == saved_correlation_id
    assert "case_id" not in payload
    assert "evidence_id" not in payload
    assert "evidence_refs" not in payload


