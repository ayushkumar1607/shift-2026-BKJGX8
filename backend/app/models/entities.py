from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    role: Mapped[str] = mapped_column(String(40), default="OWNER_DRIVER")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    registration: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(160), default="Unknown")
    organisation: Mapped[str] = mapped_column(String(160), default="")
    bms_profile: Mapped[str] = mapped_column(String(100), default="UNVERIFIED")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    pairing: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    firmware: Mapped[str] = mapped_column(String(100), default="UNKNOWN")
    encryption: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    results: Mapped[dict] = mapped_column(JSON)
    coverage: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    kind: Mapped[str] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="SUBMITTED")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class RotationJob(Base):
    __tablename__ = "rotation_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(40), default="REQUESTED")
    detail: Mapped[str] = mapped_column(Text)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
