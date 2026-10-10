from types import SimpleNamespace
from app.services.simulator import assess, shim_request

def vehicle(policy=False):
    return SimpleNamespace(policy_enabled=policy)

def test_unauthorized_access_is_rejected_after_policy_and_not_forwarded():
    result=shim_request(vehicle(True),False)
    assert not result["accepted"] and not result["forwarded"]

def test_initial_demo_shows_weak_policy_then_authorized_call_succeeds():
    assert shim_request(vehicle(False),False)["accepted"]
    assert shim_request(vehicle(True),True)["accepted"]

def test_unknown_checks_stay_unknown_after_remediation():
    statuses={r["check_id"]:r["status"] for r in assess(vehicle(True))["checks"]}
    assert statuses["CONFIG_AUTH"]=="PASS"
    assert statuses["PAIRING_RESTRICTION"]=="UNKNOWN"
    assert statuses["FIRMWARE_INTEGRITY"]=="UNKNOWN"
    assert statuses["TRANSPORT_ENCRYPTION"]=="UNKNOWN"

def test_battery_control_always_blocked():
    result=shim_request(vehicle(False),True,"CONTROL_BATTERY")
    assert not result["accepted"] and not result["forwarded"]
