import os
import uuid
from pathlib import Path

TEST_DATABASE = Path("/tmp") / f"evshield-tests-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"
os.environ["SECRET_KEY"] = "test-only-secret-key-that-is-never-used-outside-tests"

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditEvent
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        signed = test_client.post("/api/auth/login", json={"identifier": "judge@evshield.demo", "password": "Demo@1234"})
        assert signed.status_code == 200
        reset = test_client.post("/api/demo/reset", json={"confirm": True})
        assert reset.status_code == 200
        yield test_client


def connect(client, device_id):
    response = client.post(f"/api/devices/{device_id}/connect")
    assert response.status_code == 200
    return response.json()


def rotate(client, device_id, current="Demo@1234", new="Shield@Pass2026", confirm="Shield@Pass2026"):
    return client.post(f"/api/devices/{device_id}/credentials/rotate", json={
        "current_password": current, "new_password": new, "confirm_password": confirm,
    })


def test_five_demo_profiles_are_seeded_with_required_identification_and_rotation(client):
    response = client.get("/api/devices")
    assert response.status_code == 200
    profiles = response.json()["items"]
    assert len(profiles) == 5
    for item in profiles:
        assert item["manufacturer"]
        assert item["model"]
        assert item["firmware"]
        assert item["interface"] == "Bluetooth / BLE"
        assert item["default_credential_status"] == "Demo credential available"
        assert item["credential_rotation_supported"] is True
        assert item["demo_profile"] is True


def test_every_profile_produces_distinct_assessment(client):
    outcomes = {}
    for device_id in [f"EVS-DEMO-{i:03d}" for i in range(1, 6)]:
        connect(client, device_id)
        result = client.post(f"/api/devices/{device_id}/assessments")
        assert result.status_code == 200
        assessment = result.json()
        outcomes[device_id] = (assessment["overall_status"], assessment["score"], assessment["evidence_coverage"])
    assert outcomes["EVS-DEMO-001"] == ("PASS", 100, 100)
    assert outcomes["EVS-DEMO-002"][0] == "NEEDS ATTENTION"
    assert outcomes["EVS-DEMO-003"] == ("PASS WITH UNKNOWN CHECKS", 100, 80)
    assert outcomes["EVS-DEMO-004"] == ("INSUFFICIENT EVIDENCE", 0, 0)
    assert outcomes["EVS-DEMO-005"][0] == "NEEDS ATTENTION"
    assert len(set(outcomes.values())) == 5


@pytest.mark.parametrize("device_id", [f"EVS-DEMO-{i:03d}" for i in range(1, 6)])
def test_all_profiles_support_rotation_and_old_password_is_rejected(client, device_id):
    connect(client, device_id)
    response = rotate(client, device_id)
    assert response.status_code == 200
    payload = response.json()
    assert payload["device_id"] == device_id
    assert payload["verification_status"] == "VERIFIED"
    assert payload["new_credential_authentication"] == "PASS"
    assert payload["previous_credential_authentication"] == "REJECTED"
    credential_status = client.get(f"/api/devices/{device_id}/credential-status").json()
    assert credential_status["rotated"] is True
    assert credential_status["current_demo_credential_available"] is False
    assert "Shield@Pass2026" not in response.text
    assert "Demo@1234" not in response.text
    assert client.post(f"/api/devices/{device_id}/credentials/verify", json={"current_password": "Shield@Pass2026", "previous_password": "Demo@1234"}).status_code == 200
    assert client.post(f"/api/devices/{device_id}/credentials/verify", json={"current_password": "Demo@1234"}).status_code == 401


def test_incorrect_current_password_does_not_change_credential(client):
    device_id = "EVS-DEMO-001"
    connect(client, device_id)
    assert rotate(client, device_id, current="wrong").status_code == 401
    assert client.post(f"/api/devices/{device_id}/credentials/verify", json={"current_password": "Demo@1234"}).status_code == 200
    assert client.post(f"/api/devices/{device_id}/credentials/verify", json={"current_password": "Shield@Pass2026"}).status_code == 401


def test_password_mismatch_is_rejected_before_mutation(client):
    device_id = "EVS-DEMO-001"
    connect(client, device_id)
    response = rotate(client, device_id, confirm="Other@Pass2026")
    assert response.status_code == 422
    assert client.post(f"/api/devices/{device_id}/credentials/verify", json={"current_password": "Demo@1234"}).status_code == 200


def test_rotation_history_contains_no_plaintext_credentials(client):
    device_id = "EVS-DEMO-001"
    connect(client, device_id)
    rotate(client, device_id)
    response = client.get(f"/api/devices/{device_id}/credentials/history")
    assert response.status_code == 200
    assert "Demo@1234" not in response.text
    assert "Shield@Pass2026" not in response.text
    assert response.json()["items"][0]["verification_status"] == "VERIFIED"
    assert response.json()["items"][0]["state_history"] == ["READY", "AUTHENTICATED", "CHANGE_REQUESTED", "CHANGE_APPLIED", "VERIFICATION_PENDING", "VERIFIED"]


def test_rotation_result_event_id_points_to_non_secret_audit_event(client):
    device_id = "EVS-DEMO-001"
    connect(client, device_id)
    result = rotate(client, device_id).json()
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.event_id == result["event_id"]))
    assert event is not None
    assert event.operation == "credential_rotation"
    assert event.success is True
    assert event.verification_result == "VERIFIED"


def test_unknown_checks_stay_unknown_when_rotation_does_not_add_evidence(client):
    device_id = "EVS-DEMO-003"
    connect(client, device_id)
    rotate(client, device_id)
    assessment = client.post(f"/api/devices/{device_id}/assessments").json()
    encryption = next(item for item in assessment["checks"] if item["key"] == "encryption")
    assert encryption["status"] == "UNKNOWN"
    assert assessment["overall_status"] == "PASS WITH UNKNOWN CHECKS"


def test_switching_devices_keeps_credential_state_separate(client):
    first = "EVS-DEMO-001"
    second = "EVS-DEMO-002"
    connect(client, first)
    assert rotate(client, first).status_code == 200
    connect(client, second)
    assert client.post(f"/api/devices/{second}/credentials/verify", json={"current_password": "Demo@1234"}).status_code == 200
    assert client.post(f"/api/devices/{second}/credentials/verify", json={"current_password": "Shield@Pass2026"}).status_code == 401
    connect(client, first)
    assert client.post(f"/api/devices/{first}/credentials/verify", json={"current_password": "Shield@Pass2026"}).status_code == 200


def test_unauthenticated_users_cannot_access_protected_api():
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/devices").status_code == 401
        assert anonymous.post("/api/demo/reset", json={"confirm": True}).status_code == 401


def test_signup_and_login_accept_phone_number_with_country_code(client):
    signup = client.post("/api/auth/signup", json={
        "full_name": "Phone Judge", "phone": "+1 (415) 555-0123", "password": "Phone@Pass2026",
        "confirm_password": "Phone@Pass2026", "terms_accepted": True,
    })
    assert signup.status_code == 201
    assert signup.json()["user"]["phone"] == "+14155550123"
    client.post("/api/auth/logout")
    login = client.post("/api/auth/login", json={"identifier": "+1 (415) 555-0123", "password": "Phone@Pass2026"})
    assert login.status_code == 200
    assert login.json()["user"]["phone"] == "+14155550123"


def test_one_user_cannot_read_or_change_another_users_credential(client):
    device_id = "EVS-DEMO-001"
    connect(client, device_id)
    first_user = client.cookies.get("evshield_session")
    signup = client.post("/api/auth/signup", json={
        "full_name": "Second Judge", "email": f"second-{uuid.uuid4().hex[:8]}@example.test", "password": "Second@Pass2026",
        "confirm_password": "Second@Pass2026", "terms_accepted": True,
    })
    assert signup.status_code == 201
    assert client.get(f"/api/devices/{device_id}/credential-status").status_code == 409
    connect(client, device_id)
    assert client.post(f"/api/devices/{device_id}/credentials/verify", json={"current_password": "Demo@1234"}).status_code == 200
    assert client.post(f"/api/devices/{device_id}/credentials/verify", json={"current_password": "Shield@Pass2026"}).status_code == 401
    assert first_user != client.cookies.get("evshield_session")


def test_real_writes_disabled_by_default_and_reset_restores_profiles(client):
    assert client.get("/api/capabilities").json()["real_bms_writes"] is False
    connect(client, "EVS-DEMO-001")
    rotate(client, "EVS-DEMO-001")
    reset = client.post("/api/demo/reset", json={"confirm": True})
    assert reset.status_code == 200
    profiles = client.get("/api/devices").json()["items"]
    assert len(profiles) == 5
    assert all(item["credential_rotation_supported"] for item in profiles)
    assert client.post("/api/devices/EVS-DEMO-001/credentials/verify", json={"current_password": "Demo@1234"}).status_code == 409
    connect(client, "EVS-DEMO-001")
    assert client.post("/api/devices/EVS-DEMO-001/credentials/verify", json={"current_password": "Demo@1234"}).status_code == 200


def test_legacy_authentication_finding_clears_only_after_simulated_retest(client):
    device_id = "EVS-DEMO-002"
    connect(client, device_id)
    before = client.post(f"/api/devices/{device_id}/assessments").json()
    assert next(item for item in before["checks"] if item["key"] == "authentication")["status"] == "FINDING"
    rotate(client, device_id)
    retest = client.post(f"/api/devices/{device_id}/assessments/{before['id']}/retest").json()["assessment"]
    assert next(item for item in retest["checks"] if item["key"] == "authentication")["status"] == "PASS"
    assert next(item for item in retest["checks"] if item["key"] == "pairing")["status"] == "UNKNOWN"


def test_failed_verification_never_returns_success(client):
    device_id = "EVS-DEMO-001"
    connect(client, device_id)
    rotate(client, device_id)
    failed = client.post(f"/api/devices/{device_id}/credentials/verify", json={"current_password": "wrong", "previous_password": "Demo@1234"})
    assert failed.status_code == 401
    assert failed.json().get("verification_status") != "VERIFIED"

