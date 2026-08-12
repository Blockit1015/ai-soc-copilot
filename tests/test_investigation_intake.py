from fastapi.testclient import TestClient

#测试代码：用代码自动模拟外部系统，向系统发送各种各样的请求（正常的、重复的、错误的）
#它的作用是：每次修改了代码，只要运行这个代码，系统就会自动检测告警接收功能是否还正常工作，是一个自动化的验收测试 


#准备“假数据”（Fixture）：在内存里准备了一个写死的假告警包裹，不管测试跑多少次，用的都是这一份一模一样的数据
ALERT_FIXTURE = {
    "alert_id": "alert-fixture-001",
    "source": "training-siem",
    "occurred_at": "2026-07-30T01:00:00Z",
    "severity": "high",
    "title": "Repeated failed sign-in in training tenant",
    "asset_id": "asset-fixture-001",
    "raw_ref": "fixture://alerts/alert-fixture-001",
}


def test_first_valid_alert_is_received_with_explicit_correlation_id() -> None:
    from app.main import app

    client = TestClient(app)  #测试工具（TestClient），假装是一个外部系统

#准备“请求头”并发送请求：测试工具（TestClient）假装成一个外部系统，向我们的 /api/v1/investigations 告警接收接口发送了一个POST请求
#它把假数据ALERT_FIXTURE放在json里
#它把两个Key放在headers里（快递单号和追踪手环）
    response = client.post(
        "/api/v1/investigations",
        headers={
            "Idempotency-Key": "idem-test-first-alert",    #快递单号
            "X-Correlation-ID": "corr-test-first-alert",   #追踪标识
        },
        json=ALERT_FIXTURE,
    )

#检查返回结果（断言）
    assert response.status_code == 201
    payload = response.json()
    assert payload["investigation_id"].startswith("inv_")
    assert payload["alert_id"] == ALERT_FIXTURE["alert_id"]
    assert payload["status"] == "received"
    assert payload["correlation_id"] == "corr-test-first-alert"
    assert payload["duplicate"] is False


def test_safe_replay_reuses_original_investigation_and_correlation_ids() -> None:
    from app.main import app

    client = TestClient(app)
    headers = {
        "Idempotency-Key": "idem-test-safe-replay",
        "X-Correlation-ID": "corr-test-safe-replay",
    }

    first_response = client.post(
        "/api/v1/investigations",
        headers=headers,
        json=ALERT_FIXTURE,
    )
    replay_response = client.post(
        "/api/v1/investigations",
        headers={
            "Idempotency-Key": "idem-test-safe-replay",
            "X-Correlation-ID": "corr-test-replay-must-not-replace-original",
        },
        json=ALERT_FIXTURE,
    )

    assert first_response.status_code == 201
    assert replay_response.status_code == 200
    first_payload = first_response.json()
    replay_payload = replay_response.json()
    assert first_payload["duplicate"] is False
    assert replay_payload["duplicate"] is True
    assert replay_payload["investigation_id"] == first_payload["investigation_id"]
    assert replay_payload["correlation_id"] == first_payload["correlation_id"]


def test_reusing_key_with_different_alert_payload_is_rejected_without_replacing_record() -> None:
    from app.main import app

    client = TestClient(app)
    headers = {
        "Idempotency-Key": "idem-test-conflict",
        "X-Correlation-ID": "corr-test-conflict",
    }
    conflicting_alert = {**ALERT_FIXTURE, "severity": "critical"}

    first_response = client.post(
        "/api/v1/investigations",
        headers=headers,
        json=ALERT_FIXTURE,
    )
    conflict_response = client.post(
        "/api/v1/investigations",
        headers=headers,
        json=conflicting_alert,
    )
    original_replay_response = client.post(
        "/api/v1/investigations",
        headers=headers,
        json=ALERT_FIXTURE,
    )

    assert first_response.status_code == 201
    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert conflict_response.json()["detail"]["message"] == (
        "Idempotency-Key was already used with a different payload"
    )
    assert original_replay_response.status_code == 200
    assert (
        original_replay_response.json()["investigation_id"]
        == first_response.json()["investigation_id"]
    )


def test_alert_with_invalid_severity_is_rejected() -> None:
    from app.main import app

    client = TestClient(app)
    invalid_alert = {**ALERT_FIXTURE, "severity": "urgent"}

    response = client.post(
        "/api/v1/investigations",
        headers={"Idempotency-Key": "idem-test-invalid-severity"},
        json=invalid_alert,
    )

    assert response.status_code == 422


def test_alert_missing_required_raw_reference_is_rejected() -> None:
    from app.main import app

    client = TestClient(app)
    incomplete_alert = {
        field: value for field, value in ALERT_FIXTURE.items() if field != "raw_ref"
    }

    response = client.post(
        "/api/v1/investigations",
        headers={"Idempotency-Key": "idem-test-missing-field"},
        json=incomplete_alert,
    )

    assert response.status_code == 422


def test_alert_without_idempotency_key_is_rejected() -> None:
    from app.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/investigations",
        json=ALERT_FIXTURE,
    )

    assert response.status_code == 422
