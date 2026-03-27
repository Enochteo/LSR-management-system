"""Configuration scaffold.

Use environment variables or `.env` values for all secrets.
Do not hardcode credentials in source control.
"""

import os


class BaseConfig:
	"""Base configuration shared by all environments.

	TODO (Phase 0):
	- Move all sensitive values to environment variables.
	- Add separate SMTP settings for different environments.
	- Add optional Redis/Celery settings if queue-based scheduling is used.
	"""

	SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
	SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///library.db")
	SQLALCHEMY_TRACK_MODIFICATIONS = False

	# Mail scaffold values (Phase 4).
	MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.example.com")
	MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
	MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
	MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
	MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
	MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")

	# Session/security toggles.
	SESSION_COOKIE_HTTPONLY = True
	SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"


class DevelopmentConfig(BaseConfig):
	"""Development defaults for local implementation."""

	DEBUG = True


class TestingConfig(BaseConfig):
	"""Testing defaults (switch to test DB when writing tests)."""

	TESTING = True
	SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///test_library.db")


class ProductionConfig(BaseConfig):
	"""Production defaults (harden security-related flags)."""

	DEBUG = False
