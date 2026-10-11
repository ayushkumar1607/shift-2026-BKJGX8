from .models import AssessmentCheck, DeviceProfile, SecurityAssessment

CHECKS = [
    ("authentication", "Authentication policy", "auth_status", "If this simulated authentication finding is present, verify that an unauthorized request is rejected."),
    ("pairing", "Bluetooth pairing", "pairing_status", "Use a documented, secure pairing configuration; simulator evidence is limited to the profile."),
    ("encryption", "Transport encryption", "encryption_status", "Confirm transport encryption from device documentation or a validated test."),
    ("firmware", "Firmware identification", "firmware_status", "Confirm the exact firmware through a documented identification method."),
    ("credentials", "Credential management", "credential_status", "Rotate the simulator credential and verify the new value while rejecting the previous one."),
]

EXPLANATIONS = {
    "PASS": "The synthetic demo profile reports this check as passing.",
    "FINDING": "The synthetic demo profile contains a security finding for this check.",
    "UNKNOWN": "There is not enough simulated evidence to determine this check.",
    "NOT_TESTED": "This check has not been run.",
    "NOT_APPLICABLE": "This check does not apply to the selected profile.",
}


def build_assessment(db, user_id: str, profile: DeviceProfile, credential_rotated: bool, auth_retested: bool = False, is_retest: bool = False):
    results = []
    for key, title, field, recommendation in CHECKS:
        status = getattr(profile, field)
        if key == "credentials" and credential_rotated and status != "UNKNOWN":
            status = "PASS"
        if key == "authentication" and auth_retested and status == "FINDING":
            status = "PASS"
        severity = "HIGH" if status == "FINDING" and key == "authentication" else "MEDIUM" if status == "FINDING" else "INFO"
        results.append((key, title, status, severity, EXPLANATIONS[status], recommendation))

    assessed = [item for item in results if item[2] in ("PASS", "FINDING")]
    score = round(sum(1 for item in assessed if item[2] == "PASS") / len(assessed) * 100) if assessed else 0
    coverage = round(len(assessed) / len(results) * 100)
    findings = [item for item in assessed if item[2] == "FINDING"]
    if findings:
        overall = "NEEDS ATTENTION"
    elif not assessed:
        overall = "INSUFFICIENT EVIDENCE"
    elif len(assessed) < len(results):
        overall = "PASS WITH UNKNOWN CHECKS"
    else:
        overall = "PASS"

    assessment = SecurityAssessment(user_id=user_id, device_id=profile.id, overall_status=overall, score=score, evidence_coverage=coverage, is_retest=is_retest)
    db.add(assessment)
    db.flush()
    for key, title, status, severity, explanation, recommendation in results:
        db.add(AssessmentCheck(assessment_id=assessment.id, key=key, title=title, status=status, severity=severity, explanation=explanation, recommendation=recommendation))
    db.flush()
    return assessment

