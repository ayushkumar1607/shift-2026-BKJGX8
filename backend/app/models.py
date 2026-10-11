from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_utc():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class DeviceProfile(Base):
    __tablename__ = "device_profiles"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    manufacturer: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(100))
    firmware: Mapped[str] = mapped_column(String(40))
    interface: Mapped[str] = mapped_column(String(60))
    documentation_status: Mapped[str] = mapped_column(String(180))
    default_credential_status: Mapped[str] = mapped_column(String(80), default="Demo credential available")
    auth_status: Mapped[str] = mapped_column(String(24))
    pairing_status: Mapped[str] = mapped_column(String(24))
    encryption_status: Mapped[str] = mapped_column(String(24))
    firmware_status: Mapped[str] = mapped_column(String(24))
    credential_status: Mapped[str] = mapped_column(String(24))
    summary: Mapped[str] = mapped_column(Text)
    credential_rotation_supported: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class DeviceSession(Base):
    __tablename__ = "device_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("device_profiles.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(20), default="SIMULATION")
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("user_id", "device_id", name="uq_session_user_device"),)


class SecurityAssessment(Base):
    __tablename__ = "security_assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("device_profiles.id", ondelete="CASCADE"), index=True)
    overall_status: Mapped[str] = mapped_column(String(40))
    score: Mapped[int] = mapped_column(Integer)
    evidence_coverage: Mapped[int] = mapped_column(Integer)
    is_retest: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    checks: Mapped[list["AssessmentCheck"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class AssessmentCheck(Base):
    __tablename__ = "assessment_checks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("security_assessments.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(24))
    explanation: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    assessment: Mapped[SecurityAssessment] = relationship(back_populates="checks")


class CredentialState(Base):
    __tablename__ = "credential_states"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("device_profiles.id", ondelete="CASCADE"), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    previous_password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rotated: Mapped[bool] = mapped_column(Boolean, default=False)
    last_rotation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verification_status: Mapped[str] = mapped_column(String(24), default="NOT_TESTED")
    __table_args__ = (UniqueConstraint("user_id", "device_id", name="uq_credential_user_device"),)


class CredentialRotation(Base):
    __tablename__ = "credential_rotations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("device_profiles.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String(32), default="READY")
    state_history: Mapped[list[str]] = mapped_column(JSON, default=list)
    verification_status: Mapped[str] = mapped_column(String(24), default="PENDING")
    new_password_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    old_password_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("device_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(48))
    success: Mapped[bool] = mapped_column(Boolean)
    verification_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

