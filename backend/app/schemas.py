import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def password_policy(value: str) -> str:
    if len(value) < 10 or len(value) > 128:
        raise ValueError("Use 10–128 characters.")
    if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"\d", value) or not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Include an uppercase letter, lowercase letter, number, and symbol.")
    return value


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    password: str
    confirm_password: str
    terms_accepted: bool

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        if value is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value.strip()):
            raise ValueError("Enter a valid email address.")
        return value.strip().lower() if value else None

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value):
        if value is not None:
            value = re.sub(r"[\s()-]", "", value.strip())
            if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
                raise ValueError("Include country code, for example +14155550123.")
        return value

    @field_validator("password")
    @classmethod
    def valid_password(cls, value):
        return password_policy(value)

    @model_validator(mode="after")
    def validate_signup(self):
        if not self.email and not self.phone:
            raise ValueError("Add an email address or a phone number with country code.")
        if not self.terms_accepted:
            raise ValueError("Accept the terms and privacy notice to continue.")
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value):
        value = value.strip()
        return re.sub(r"[\s()-]", "", value) if value.startswith("+") else value


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str | None
    phone: str | None
    demo_auth_mode: bool


class AuthResult(BaseModel):
    user: UserResponse
    message: str


class RotateRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def valid_new_password(cls, value):
        return password_policy(value)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match.")
        if self.new_password == self.current_password:
            raise ValueError("Choose a password different from the current password.")
        return self


class VerifyRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    previous_password: str | None = Field(default=None, max_length=128)


class DeviceOut(BaseModel):
    id: str
    name: str
    manufacturer: str
    model: str
    firmware: str
    interface: str
    device_identifier: str
    documentation_status: str
    default_credential_status: str
    authentication_status: str
    pairing_status: str
    encryption_status: str
    firmware_status: str
    credential_status: str
    summary: str
    credential_rotation_supported: bool
    demo_profile: bool = True
    connection_status: str = "AVAILABLE"


class DeviceListOut(BaseModel):
    items: list[DeviceOut]
    operation_mode: Literal["SIMULATION"]


class IdentificationOut(BaseModel):
    manufacturer: str
    model: str
    firmware: str
    interface: str
    device_identifier: str
    documentation_status: str
    default_credential_status: str
    credential_change_support: str
    identification_status: str
    identification_confidence: str | None = None
    data_source: str
    authentication_status: str | None = None
    encryption_status: str | None = None
    pairing_status: str | None = None
    credential_rotation_status: str | None = None
    last_assessment_at: datetime | None = None


class ConnectionOut(BaseModel):
    device: DeviceOut
    connection_status: str
    operation_mode: Literal["SIMULATION"]
    identification: IdentificationOut


class CheckOut(BaseModel):
    key: str
    title: str
    status: str
    severity: str
    explanation: str
    recommendation: str


class AssessmentOut(BaseModel):
    id: str
    device_id: str
    device_name: str
    overall_status: str
    score: int
    evidence_coverage: int
    is_retest: bool
    created_at: datetime
    checks: list[CheckOut]


class AssessmentListOut(BaseModel):
    items: list[AssessmentOut]


class AssessmentRetestOut(BaseModel):
    previous_assessment_id: str
    assessment: AssessmentOut
    comparison: dict[str, str]


class CredentialStatusOut(BaseModel):
    device_id: str
    device_name: str
    rotation_supported: bool
    operation_mode: Literal["SIMULATION"]
    current_demo_credential_available: bool
    rotated: bool
    last_rotation_at: datetime | None
    last_verification_status: str
    rotation_count: int
    last_rotation: str | None = None


class RotationOut(BaseModel):
    event_id: str
    state: str
    state_history: list[str]
    verification_status: str
    new_password_accepted: bool
    old_password_rejected: bool
    created_at: datetime


class RotationHistoryOut(BaseModel):
    items: list[RotationOut]


class RotationResultOut(BaseModel):
    device_id: str
    device_name: str
    credential_update: str
    new_credential_authentication: str
    previous_credential_authentication: str
    verification_status: str
    operation_mode: Literal["SIMULATION"]
    verification_timestamp: datetime
    event_id: str
    state_machine: list[str]


class VerificationResultOut(BaseModel):
    device_id: str
    device_name: str
    new_credential_authentication: str
    previous_credential_authentication: str
    verification_status: str
    operation_mode: Literal["SIMULATION"]
    verification_timestamp: datetime
    event_id: str | None


class SessionOut(BaseModel):
    device: DeviceOut | None
    connection_status: str
    operation_mode: Literal["SIMULATION"]


class MessageOut(BaseModel):
    message: str


class ForgotPasswordOut(BaseModel):
    delivery_configured: bool
    message: str

