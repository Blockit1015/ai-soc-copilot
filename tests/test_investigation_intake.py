from fastapi.testclient import TestClient


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

    client = TestClient(app)

    response = client.post(
        "/api/v1/investigations",
        headers={
            "Idempotency-Key": "idem-test-first-alert",
            "X-Correlation-ID": "corr-test-first-alert",
        },
        json=ALERT_FIXTURE,
    )

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
