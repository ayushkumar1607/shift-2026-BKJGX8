from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CredentialState, DeviceProfile, User
from .security import hash_password

DEMO_CREDENTIAL = "Demo@1234"

PROFILES = [
    {
        "id": "EVS-DEMO-001", "name": "SecureBMS-S1", "manufacturer": "EV Shield Demo Labs", "model": "SecureBMS-S1", "firmware": "1.4.2", "interface": "Bluetooth / BLE",
        "documentation_status": "Simulated documentation confirms password changing", "default_credential_status": "Demo credential available", "auth_status": "PASS", "pairing_status": "PASS", "encryption_status": "PASS", "firmware_status": "PASS", "credential_status": "PASS",
        "summary": "All simulated checks pass with complete evidence.",
    },
    {
        "id": "EVS-DEMO-002", "name": "LegacyBMS-L1", "manufacturer": "EV Shield Demo Labs", "model": "LegacyBMS-L1", "firmware": "0.9.8", "interface": "Bluetooth / BLE",
        "documentation_status": "Simulated documentation confirms password changing", "default_credential_status": "Demo credential available", "auth_status": "FINDING", "pairing_status": "UNKNOWN", "encryption_status": "UNKNOWN", "firmware_status": "PASS", "credential_status": "FINDING",
        "summary": "Simulated authentication and default credential findings; pairing and encryption evidence is unknown.",
    },
    {
        "id": "EVS-DEMO-003", "name": "LockedBMS-X2", "manufacturer": "EV Shield Demo Labs", "model": "LockedBMS-X2", "firmware": "2.0.0", "interface": "Bluetooth / BLE",
        "documentation_status": "Simulated documentation confirms password changing", "default_credential_status": "Demo credential available", "auth_status": "PASS", "pairing_status": "PASS", "encryption_status": "UNKNOWN", "firmware_status": "PASS", "credential_status": "PASS",
        "summary": "Known checks pass; transport encryption has not been established in this simulation.",
    },
    {
        "id": "EVS-DEMO-004", "name": "UnknownBMS-U0", "manufacturer": "Unidentified Demo Device", "model": "UnknownBMS-U0", "firmware": "Unknown", "interface": "Bluetooth / BLE",
        "documentation_status": "Synthetic demo registry confirms password changing", "default_credential_status": "Demo credential available", "auth_status": "UNKNOWN", "pairing_status": "UNKNOWN", "encryption_status": "UNKNOWN", "firmware_status": "UNKNOWN", "credential_status": "UNKNOWN",
        "summary": "Predefined simulator profile with incomplete identification and security evidence.",
    },
    {
        "id": "EVS-DEMO-005", "name": "PowerCell-B5", "manufacturer": "EV Shield Demo Labs", "model": "PowerCell-B5", "firmware": "3.1.5", "interface": "Bluetooth / BLE",
        "documentation_status": "Simulated documentation confirms password changing", "default_credential_status": "Demo credential available", "auth_status": "PASS", "pairing_status": "FINDING", "encryption_status": "PASS", "firmware_status": "PASS", "credential_status": "PASS",
        "summary": "Simulated pairing finding; all other known checks pass.",
    },
]


def seed_profiles(db: Session):
    existing = {p.id: p for p in db.scalars(select(DeviceProfile)).all()}
    for data in PROFILES:
        profile = existing.get(data["id"])
        if profile is None:
            db.add(DeviceProfile(**data, credential_rotation_supported=True, is_demo=True))
        else:
            for key, value in data.items():
                setattr(profile, key, value)
            profile.credential_rotation_supported = True
            profile.is_demo = True
    db.commit()


def ensure_user_credentials(db: Session, user: User):
    profiles = db.scalars(select(DeviceProfile)).all()
    current = {state.device_id: state for state in db.scalars(select(CredentialState).where(CredentialState.user_id == user.id)).all()}
    for profile in profiles:
        if profile.id not in current:
            db.add(CredentialState(user_id=user.id, device_id=profile.id, password_hash=hash_password(DEMO_CREDENTIAL)))
    db.commit()


def reset_user_demo(db: Session, user: User):
    from .models import AuditEvent, CredentialRotation, SecurityAssessment

    db.query(SecurityAssessment).filter_by(user_id=user.id).delete(synchronize_session=False)
    db.query(CredentialRotation).filter_by(user_id=user.id).delete(synchronize_session=False)
    db.query(AuditEvent).filter_by(user_id=user.id).delete(synchronize_session=False)
    db.query(CredentialState).filter_by(user_id=user.id).delete(synchronize_session=False)
    ensure_user_credentials(db, user)
    db.commit()


def seed_demo_database():
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    from .database import SessionLocal
    from .models import User

    backend_dir = Path(__file__).resolve().parents[1]
    migrations_config = Config(str(backend_dir / "alembic.ini"))
    migrations_config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(migrations_config, "head")
    with SessionLocal() as db:
        seed_profiles(db)
        user = db.scalar(select(User).where(User.email == "judge@evshield.demo"))
        if user is None:
            user = User(full_name="EV Shield Judge", email="judge@evshield.demo", password_hash=hash_password("Demo@1234"), terms_accepted=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        ensure_user_credentials(db, user)


if __name__ == "__main__":
    seed_demo_database()
    print("Seeded five synthetic BMS profiles and the local judge demo account.")

