"""Application configuration.

All sensitive values are read from environment variables.
Never hardcode credentials or secrets in this file.
"""

import os


class BaseConfig:
    """Shared configuration for all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///library.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail (SMTP) settings.
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.example.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")

    # Session cookie security.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = "Lax"

    # Session enforcement timing (seconds).
    SESSION_DURATION_SECONDS = int(os.getenv("SESSION_DURATION_SECONDS", "10800"))  # 3h
    WARN_30_THRESHOLD_SECONDS = int(os.getenv("WARN_30_THRESHOLD_SECONDS", "9000"))  # 2h30m
    WARN_10_THRESHOLD_SECONDS = int(os.getenv("WARN_10_THRESHOLD_SECONDS", "10200"))  # 2h50m

    # Base URL used when generating QR code sign-in links.
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")

    # Default room capacity (overridable per-room in DB).
    DEFAULT_ROOM_CAPACITY = 6


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///test_library.db")
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
