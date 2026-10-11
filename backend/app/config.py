import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./evshield.db")
SECRET_KEY = os.getenv("SECRET_KEY", "local-demo-key-change-before-deployment")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 12 * 60
REAL_BMS_WRITES = os.getenv("REAL_BMS_WRITES", "false").lower() == "true"
DEMO_AUTH_MODE = True  # No email or SMS provider is implemented in this demo.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_NAME = "evshield_session"
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]

