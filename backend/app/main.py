import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .assessment import build_assessment
from .config import COOKIE_NAME, COOKIE_SECURE, CORS_ORIGINS, DEMO_AUTH_MODE, REAL_BMS_WRITES
from .database import get_db
from .models import (AuditEvent, CredentialRotation, CredentialState, DeviceProfile, DeviceSession, SecurityAssessment, User, now_utc)
from .schemas import (
    AssessmentListOut, AssessmentOut, AssessmentRetestOut, AuthResult, ConnectionOut,
    CredentialStatusOut, DeviceListOut, DeviceOut, ForgotPasswordOut, IdentificationOut,
    LoginRequest, MessageOut, RotateRequest, RotationHistoryOut, RotationResultOut,
    SessionOut, SignupRequest, UserResponse, VerificationResultOut, VerifyRequest,
)
from .security import create_access_token, hash_password, read_access_token, verify_password
from .seed import DEMO_CREDENTIAL, ensure_user_credentials, reset_user_demo, seed_demo_database

@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_demo_database()
    yield


app = FastAPI(title="EV Shield API", version="1.0.0", description="Simulation-only EV BMS security assessment and credential rotation demo.", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

_login_attempts: dict[str, list[float]] = {}


def _user_response(user: User):
    return {"id": user.id, "full_name": user.full_name, "email": user.email, "phone": user.phone, "demo_auth_mode": DEMO_AUTH_MODE}


def _set_session_cookie(response: Response, user_id: str):
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user_id),
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=12 * 60 * 60,
        path="/",
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    user_id = read_access_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    return user


def get_profile(db: Session, device_id: str) -> DeviceProfile:
    profile = db.get(DeviceProfile, device_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Demo device not found.")
    return profile


def require_active_session(db: Session, user_id: str, device_id: str):
    connected = db.scalar(select(DeviceSession).where(DeviceSession.user_id == user_id, DeviceSession.device_id == device_id, DeviceSession.active.is_(True)))
    if not connected:
        raise HTTPException(status_code=409, detail="Connect this demo profile before using its assessment or credentials.")
    return connected


def get_credential(db: Session, user: User, device_id: str) -> CredentialState:
    state = db.scalar(select(CredentialState).where(CredentialState.user_id == user.id, CredentialState.device_id == device_id))
    if state is None:
        state = CredentialState(user_id=user.id, device_id=device_id, password_hash=hash_password(DEMO_CREDENTIAL))
        db.add(state)
        db.flush()
    return state


def _audit(db, user_id, device_id, operation, success, verification_result=None, event_id=None):
    values = {"user_id": user_id, "device_id": device_id, "operation": operation, "success": success, "verification_result": verification_result}
    if event_id is not None:
        values["event_id"] = event_id
    db.add(AuditEvent(**values))


def _device_dict(profile: DeviceProfile, session: DeviceSession | None = None):
    return {
        "id": profile.id,
        "name": profile.name,
        "manufacturer": profile.manufacturer,
        "model": profile.model,
        "firmware": profile.firmware,
        "interface": profile.interface,
        "device_identifier": profile.id,
        "documentation_status": profile.documentation_status,
        "default_credential_status": profile.default_credential_status,
        "authentication_status": profile.auth_status,
        "pairing_status": profile.pairing_status,
        "encryption_status": profile.encryption_status,
        "firmware_status": profile.firmware_status,
        "credential_status": profile.credential_status,
        "summary": profile.summary,
        "credential_rotation_supported": bool(profile.credential_rotation_supported),
        "demo_profile": True,
        "connection_status": "CONNECTED" if session and session.active else "AVAILABLE",
    }


def _assessment_dict(db: Session, assessment: SecurityAssessment):
    profile = db.get(DeviceProfile, assessment.device_id)
    return {
        "id": assessment.id,
        "device_id": assessment.device_id,
        "device_name": profile.name if profile else "Demo device",
        "overall_status": assessment.overall_status,
        "score": assessment.score,
        "evidence_coverage": assessment.evidence_coverage,
        "is_retest": assessment.is_retest,
        "created_at": assessment.created_at,
        "checks": [
            {"key": check.key, "title": check.title, "status": check.status, "severity": check.severity, "explanation": check.explanation, "recommendation": check.recommendation}
            for check in assessment.checks
        ],
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "simulator": True}


@app.get("/api/capabilities")
def capabilities():
    return {
        "demo_auth_mode": DEMO_AUTH_MODE,
        "real_bms_writes": REAL_BMS_WRITES,
        "real_bluetooth_supported": True,
        "physical_write_status": "NO VALIDATED HARDWARE ADAPTER — SIMULATION ONLY",
        "otp_provider_configured": False,
    }


@app.post("/api/auth/signup", status_code=201, response_model=AuthResult)
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower() if payload.email else None
    phone = payload.phone
    user = User(full_name=payload.full_name.strip(), email=email, phone=phone, password_hash=hash_password(payload.password), terms_accepted=True)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account already exists with that email or phone number.")
    ensure_user_credentials(db, user)
    _set_session_cookie(response, user.id)
    return {"user": _user_response(user), "message": "Account created. DEMO AUTH MODE: no email or SMS OTP was sent."}


def _login_key(request: Request, identifier: str):
    key = f"{request.client.host if request.client else 'local'}:{identifier.lower()}"
    now = time.monotonic()
    attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < 900]
    if len(attempts) >= 8:
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")
    _login_attempts[key] = attempts
    return key


@app.post("/api/auth/login", response_model=AuthResult)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    attempt_key = _login_key(request, identifier)
    if identifier.startswith("+"):
        user = db.scalar(select(User).where(User.phone == identifier))
    else:
        user = db.scalar(select(User).where(User.email == identifier.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        _login_attempts.setdefault(attempt_key, []).append(time.monotonic())
        raise HTTPException(status_code=401, detail="The sign-in details were not recognized.")
    _login_attempts.pop(attempt_key, None)
    ensure_user_credentials(db, user)
    _set_session_cookie(response, user.id)
    return {"user": _user_response(user), "message": "Signed in. Demo operations remain simulation-only."}


@app.post("/api/auth/verify-otp", response_model=MessageOut)
def verify_otp():
    raise HTTPException(status_code=501, detail="No email or SMS provider is configured. DEMO AUTH MODE does not send or verify OTPs.")


@app.post("/api/auth/forgot-password", response_model=ForgotPasswordOut)
def forgot_password():
    return {"delivery_configured": False, "message": "DEMO AUTH MODE: no reset email or SMS was sent. Configure an identity provider to enable account recovery."}


@app.get("/api/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_response(user)


@app.post("/api/auth/logout", response_model=MessageOut)
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=COOKIE_SECURE, samesite="lax")
    return {"message": "Signed out."}


@app.get("/api/session", response_model=SessionOut)
def active_session(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connection = db.scalar(select(DeviceSession).where(DeviceSession.user_id == user.id, DeviceSession.active.is_(True)))
    if not connection:
        return {"device": None, "connection_status": "DISCONNECTED", "operation_mode": "SIMULATION"}
    profile = get_profile(db, connection.device_id)
    return {"device": _device_dict(profile, connection), "connection_status": "CONNECTED", "operation_mode": "SIMULATION", "connected_at": connection.connected_at}


@app.get("/api/devices", response_model=DeviceListOut)
def devices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profiles = db.scalars(select(DeviceProfile).order_by(DeviceProfile.id)).all()
    sessions = {item.device_id: item for item in db.scalars(select(DeviceSession).where(DeviceSession.user_id == user.id)).all()}
    return {"items": [_device_dict(profile, sessions.get(profile.id)) for profile in profiles], "operation_mode": "SIMULATION"}


@app.get("/api/devices/{device_id}", response_model=DeviceOut)
def device_details(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, device_id)
    connection = db.scalar(select(DeviceSession).where(DeviceSession.user_id == user.id, DeviceSession.device_id == device_id, DeviceSession.active.is_(True)))
    return _device_dict(profile, connection)


@app.get("/api/devices/{device_id}/identification", response_model=IdentificationOut)
def identification(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, device_id)
    require_active_session(db, user.id, device_id)
    credential = db.scalar(select(CredentialState).where(CredentialState.user_id == user.id, CredentialState.device_id == device_id))
    last_assessment = db.scalar(select(SecurityAssessment).where(SecurityAssessment.user_id == user.id, SecurityAssessment.device_id == device_id).order_by(SecurityAssessment.created_at.desc()))
    return {
        "manufacturer": profile.manufacturer,
        "model": profile.model,
        "firmware": profile.firmware,
        "interface": profile.interface,
        "device_identifier": profile.id,
        "documentation_status": profile.documentation_status,
        "credential_change_support": "SUPPORTED IN SIMULATION" if profile.credential_rotation_supported else "UNAVAILABLE",
        "identification_status": "IDENTIFIED — DEMO PROFILE",
        "identification_confidence": "SYNTHETIC PROFILE",
        "data_source": "Synthetic Demo Registry",
        "authentication_status": profile.auth_status,
        "encryption_status": profile.encryption_status,
        "pairing_status": profile.pairing_status,
        "credential_rotation_status": "ROTATED" if credential and credential.rotated else "READY",
        "last_assessment_at": last_assessment.created_at if last_assessment else None,
    }


@app.post("/api/devices/{device_id}/connect", response_model=ConnectionOut)
def connect_device(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, device_id)
    if not profile.is_demo:
        raise HTTPException(status_code=403, detail="Physical-device simulator commands are disabled.")
    db.query(DeviceSession).filter(DeviceSession.user_id == user.id).update({"active": False})
    connection = db.scalar(select(DeviceSession).where(DeviceSession.user_id == user.id, DeviceSession.device_id == device_id))
    if connection is None:
        connection = DeviceSession(user_id=user.id, device_id=device_id, mode="SIMULATION", active=True)
        db.add(connection)
    else:
        connection.active = True
        connection.connected_at = now_utc()
        connection.mode = "SIMULATION"
    ensure_user_credentials(db, user)
    _audit(db, user.id, device_id, "simulated_connect", True, "CONNECTED")
    db.commit()
    credential = db.scalar(select(CredentialState).where(CredentialState.user_id == user.id, CredentialState.device_id == device_id))
    last_assessment = db.scalar(select(SecurityAssessment).where(SecurityAssessment.user_id == user.id, SecurityAssessment.device_id == device_id).order_by(SecurityAssessment.created_at.desc()))
    return {"device": _device_dict(profile, connection), "connection_status": "CONNECTED", "operation_mode": "SIMULATION", "identification": {
        "manufacturer": profile.manufacturer, "model": profile.model, "firmware": profile.firmware, "interface": profile.interface,
        "device_identifier": profile.id, "documentation_status": profile.documentation_status, "default_credential_status": profile.default_credential_status,
        "credential_change_support": "SUPPORTED IN SIMULATION", "identification_status": "IDENTIFIED — DEMO PROFILE", "data_source": "Synthetic Demo Registry",
        "authentication_status": profile.auth_status, "encryption_status": profile.encryption_status, "pairing_status": profile.pairing_status,
        "credential_rotation_status": "ROTATED" if credential and credential.rotated else "READY", "last_assessment_at": last_assessment.created_at if last_assessment else None,
    }}


@app.post("/api/devices/{device_id}/assessments", response_model=AssessmentOut)
def run_assessment(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, device_id)
    require_active_session(db, user.id, device_id)
    credential = get_credential(db, user, device_id)
    assessment = build_assessment(db, user.id, profile, credential.rotated, auth_retested=credential.rotated and profile.auth_status == "FINDING")
    _audit(db, user.id, device_id, "security_assessment", True, assessment.overall_status)
    db.commit()
    db.refresh(assessment)
    return _assessment_dict(db, assessment)


@app.get("/api/devices/{device_id}/assessments", response_model=AssessmentListOut)
def assessment_history(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_profile(db, device_id)
    require_active_session(db, user.id, device_id)
    entries = db.scalars(select(SecurityAssessment).options(joinedload(SecurityAssessment.checks)).where(SecurityAssessment.user_id == user.id, SecurityAssessment.device_id == device_id).order_by(SecurityAssessment.created_at.desc())).unique().all()
    return {"items": [_assessment_dict(db, item) for item in entries]}


@app.post("/api/devices/{device_id}/assessments/{assessment_id}/retest", response_model=AssessmentRetestOut)
def retest_assessment(device_id: str, assessment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, device_id)
    require_active_session(db, user.id, device_id)
    previous = db.scalar(select(SecurityAssessment).where(SecurityAssessment.id == assessment_id, SecurityAssessment.device_id == device_id, SecurityAssessment.user_id == user.id))
    if previous is None:
        raise HTTPException(status_code=404, detail="Assessment not found for this account and device.")
    credential = get_credential(db, user, device_id)
    assessment = build_assessment(db, user.id, profile, credential.rotated, auth_retested=credential.rotated and profile.auth_status == "FINDING", is_retest=True)
    _audit(db, user.id, device_id, "assessment_retest", True, assessment.overall_status)
    db.commit()
    db.refresh(assessment)
    return {"previous_assessment_id": previous.id, "assessment": _assessment_dict(db, assessment), "comparison": {"previous_status": previous.overall_status, "current_status": assessment.overall_status}}


@app.get("/api/devices/{device_id}/credential-status", response_model=CredentialStatusOut)
def credential_status(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, device_id)
    require_active_session(db, user.id, device_id)
    state = get_credential(db, user, device_id)
    count = db.query(CredentialRotation).filter_by(user_id=user.id, device_id=device_id).count()
    db.commit()
    return {
        "device_id": device_id,
        "device_name": profile.name,
        "rotation_supported": bool(profile.credential_rotation_supported),
        "operation_mode": "SIMULATION",
        "current_demo_credential_available": not state.rotated,
        "rotated": state.rotated,
        "last_rotation_at": state.last_rotation_at,
        "last_verification_status": state.last_verification_status,
        "rotation_count": count,
        "last_rotation": db.query(CredentialRotation).filter_by(user_id=user.id, device_id=device_id).order_by(CredentialRotation.created_at.desc()).first().event_id if count else None,
    }


@app.get("/api/devices/{device_id}/credentials/history", response_model=RotationHistoryOut)
def credential_history(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_profile(db, device_id)
    require_active_session(db, user.id, device_id)
    entries = db.scalars(select(CredentialRotation).where(CredentialRotation.user_id == user.id, CredentialRotation.device_id == device_id).order_by(CredentialRotation.created_at.desc())).all()
    return {"items": [{"event_id": item.event_id, "state": item.state, "state_history": item.state_history, "verification_status": item.verification_status, "new_password_accepted": item.new_password_accepted, "old_password_rejected": item.old_password_rejected, "created_at": item.created_at} for item in entries]}


@app.post("/api/devices/{device_id}/credentials/rotate", response_model=RotationResultOut)
def rotate_credential(device_id: str, payload: RotateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, device_id)
    require_active_session(db, user.id, device_id)
    if not profile.is_demo or not profile.credential_rotation_supported:
        raise HTTPException(status_code=403, detail="This device has no validated credential adapter. Simulation only.")
    state = get_credential(db, user, device_id)
    if not verify_password(payload.current_password, state.password_hash):
        _audit(db, user.id, device_id, "credential_rotation", False, "CURRENT_CREDENTIAL_REJECTED")
        db.commit()
        raise HTTPException(status_code=401, detail="The current demo password is incorrect.")

    if state.previous_password_hash and verify_password(payload.new_password, state.previous_password_hash):
        raise HTTPException(status_code=409, detail="The immediately previous password cannot be reused.")

    state_machine = ["READY", "AUTHENTICATED", "CHANGE_REQUESTED"]
    next_hash = hash_password(payload.new_password)
    state_machine.extend(["CHANGE_APPLIED", "VERIFICATION_PENDING"])
    new_accepted = verify_password(payload.new_password, next_hash)
    old_rejected = not verify_password(payload.current_password, next_hash)
    if not new_accepted or not old_rejected:
        _audit(db, user.id, device_id, "credential_rotation", False, "VERIFICATION_FAILED")
        db.commit()
        raise HTTPException(status_code=500, detail="Credential verification did not complete. The current credential was preserved.")

    state_machine.append("VERIFIED")
    event_id = str(uuid4())
    now = now_utc()
    state.previous_password_hash = state.password_hash
    state.password_hash = next_hash
    state.rotated = True
    state.last_rotation_at = now
    state.last_verification_status = "VERIFIED"
    rotation = CredentialRotation(user_id=user.id, device_id=device_id, event_id=event_id, state="VERIFIED", state_history=state_machine, verification_status="VERIFIED", new_password_accepted=True, old_password_rejected=True, created_at=now)
    db.add(rotation)
    _audit(db, user.id, device_id, "credential_rotation", True, "VERIFIED", event_id=event_id)
    db.commit()
    return {
        "device_id": device_id,
        "device_name": profile.name,
        "credential_update": "SUCCESS",
        "new_credential_authentication": "PASS",
        "previous_credential_authentication": "REJECTED",
        "verification_status": "VERIFIED",
        "operation_mode": "SIMULATION",
        "verification_timestamp": now,
        "event_id": event_id,
        "state_machine": state_machine,
    }


@app.post("/api/devices/{device_id}/credentials/verify", response_model=VerificationResultOut)
def verify_credential(device_id: str, payload: VerifyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, device_id)
    require_active_session(db, user.id, device_id)
    state = get_credential(db, user, device_id)
    if not verify_password(payload.current_password, state.password_hash):
        state.last_verification_status = "FAILED"
        _audit(db, user.id, device_id, "credential_verification", False, "CURRENT_CREDENTIAL_REJECTED")
        db.commit()
        raise HTTPException(status_code=401, detail="The supplied current password was rejected.")
    old_rejected = None
    if payload.previous_password is not None:
        old_rejected = not verify_password(payload.previous_password, state.password_hash)
        if not old_rejected:
            state.last_verification_status = "FAILED"
            _audit(db, user.id, device_id, "credential_verification", False, "PREVIOUS_CREDENTIAL_ACCEPTED")
            db.commit()
            raise HTTPException(status_code=409, detail="The previous password still authenticates. Verification failed.")
    state.last_verification_status = "VERIFIED"
    _audit(db, user.id, device_id, "credential_verification", True, "VERIFIED")
    db.commit()
    latest = db.scalar(select(CredentialRotation).where(CredentialRotation.user_id == user.id, CredentialRotation.device_id == device_id).order_by(CredentialRotation.created_at.desc()))
    return {
        "device_id": device_id,
        "device_name": profile.name,
        "new_credential_authentication": "PASS",
        "previous_credential_authentication": "REJECTED" if old_rejected is not None else "NOT_TESTED",
        "verification_status": "VERIFIED",
        "operation_mode": "SIMULATION",
        "verification_timestamp": now_utc(),
        "event_id": latest.event_id if latest else None,
    }


@app.post("/api/demo/reset", response_model=MessageOut)
def reset_demo(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="Confirm that you want to reset this account's synthetic demo data.")
    reset_user_demo(db, user)
    db.query(DeviceSession).filter_by(user_id=user.id).update({"active": False})
    db.commit()
    return {"message": "Synthetic demo data restored for this account. Physical hardware was not contacted."}

