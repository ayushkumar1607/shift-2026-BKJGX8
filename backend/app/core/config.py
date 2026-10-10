import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./evshield.db")
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
REAL_BMS_WRITES = os.getenv("REAL_BMS_WRITES", "false").lower() == "true"
OTP_MODE = os.getenv("OTP_MODE", "development")
