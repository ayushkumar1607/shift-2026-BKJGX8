from app.core.config import REAL_BMS_WRITES

def authorize_real_write(*, exact_model: bool, firmware_match: bool, documented: bool, validated_adapter: bool, authorized_user: bool, approved: bool, recovery_ready: bool) -> tuple[bool, str]:
    """Central deny-by-default gate. A future adapter must call this before every physical write."""
    if not REAL_BMS_WRITES:
        return False, "REAL_BMS_WRITES=false"
    if not all((exact_model, firmware_match, documented, validated_adapter, authorized_user, approved, recovery_ready)):
        return False, "One or more device, authorization, approval, verification, or recovery requirements are missing."
    return True, "All deployment gates passed; adapter-specific authorization is still required."
