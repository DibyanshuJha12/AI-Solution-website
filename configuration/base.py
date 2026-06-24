from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from sqlalchemy.engine import URL

from .env import ROOT_DIR, env_flag, env_int


def sqlite_database_path() -> Path:
    configured = os.getenv("SQLITE_DATABASE_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser()
    else:
        path = ROOT_DIR / "instance" / "ai_solution_local.db"
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path.resolve()


def sqlite_database_uri() -> str:
    return f"sqlite:///{sqlite_database_path().as_posix()}"


def postgres_env_is_configured() -> bool:
    if os.getenv("DATABASE_URL", "").strip():
        return True
    return any(os.getenv(name, "").strip() for name in {"POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"})


def default_database_uri():
    explicit_database_url = os.getenv("DATABASE_URL", "").strip()
    if explicit_database_url:
        return explicit_database_url
    if postgres_env_is_configured():
        return URL.create(
            "postgresql+psycopg",
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=env_int("POSTGRES_PORT", 5432),
            database=os.getenv("POSTGRES_DB", "AI solution"),
        )
    return sqlite_database_uri()


def default_engine_options(database_uri) -> dict:
    driver = getattr(database_uri, "drivername", str(database_uri))
    if str(driver).startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
        }
    return {
        "pool_pre_ping": True,
        "pool_size": env_int("DB_POOL_SIZE", 5),
        "max_overflow": env_int("DB_MAX_OVERFLOW", 10),
    }


class BaseConfig:
    BASE_DIR = ROOT_DIR
    APP_ENV = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).strip().lower()
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    DEBUG = False
    TESTING = False

    SQLITE_DATABASE_PATH = sqlite_database_path()
    SQLITE_DATABASE_URI = sqlite_database_uri()
    DATABASE_FALLBACK_TO_SQLITE = env_flag("DATABASE_FALLBACK_TO_SQLITE", True)
    DATABASE_CONNECT_TIMEOUT_SECONDS = env_int("DATABASE_CONNECT_TIMEOUT_SECONDS", 4)
    SQLALCHEMY_DATABASE_URI = default_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = default_engine_options(SQLALCHEMY_DATABASE_URI)

    ADMIN_ROUTE_PREFIX = os.getenv("ADMIN_ROUTE_PREFIX", "/secure-admin").rstrip("/")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@aisolutionsglobal.co.uk")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")
    EMAIL_SERVICE_MODE = os.getenv("EMAIL_SERVICE_MODE", "placeholder")
    EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "AI SOLUTION")
    EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", ADMIN_EMAIL)
    EMAIL_REPLY_TO_ADDRESS = os.getenv("EMAIL_REPLY_TO_ADDRESS", ADMIN_EMAIL)
    EMAIL_NOTIFICATION_TO = os.getenv("EMAIL_NOTIFICATION_TO", ADMIN_EMAIL)
    EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    EMAIL_SMTP_PORT = env_int("EMAIL_SMTP_PORT", 587)
    EMAIL_SMTP_USERNAME = os.getenv("EMAIL_SMTP_USERNAME", EMAIL_FROM_ADDRESS)
    EMAIL_SMTP_PASSWORD = os.getenv("EMAIL_SMTP_PASSWORD", "")
    EMAIL_SMTP_USE_TLS = env_flag("EMAIL_SMTP_USE_TLS", True)
    EMAIL_SMTP_USE_SSL = env_flag("EMAIL_SMTP_USE_SSL", False)
    EMAIL_SMTP_TIMEOUT_SECONDS = env_int("EMAIL_SMTP_TIMEOUT_SECONDS", 20)
    INQUIRY_DUPLICATE_WINDOW_SECONDS = env_int("INQUIRY_DUPLICATE_WINDOW_SECONDS", 600)
    FEEDBACK_DUPLICATE_WINDOW_SECONDS = env_int("FEEDBACK_DUPLICATE_WINDOW_SECONDS", 600)

    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")
    RECAPTCHA_MIN_SCORE = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.4"))
    ALLOW_INSECURE_DEV_CAPTCHA = env_flag("ALLOW_INSECURE_DEV_CAPTCHA", False)

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    CHATBOT_REQUEST_TIMEOUT_SECONDS = env_int("CHATBOT_REQUEST_TIMEOUT_SECONDS", 18)
    CHATBOT_MAX_HISTORY_ITEMS = env_int("CHATBOT_MAX_HISTORY_ITEMS", 12)
    CHATBOT_RATE_LIMIT_COUNT = env_int("CHATBOT_RATE_LIMIT_COUNT", 12)
    CHATBOT_RATE_LIMIT_WINDOW_SECONDS = env_int("CHATBOT_RATE_LIMIT_WINDOW_SECONDS", 60)
    CHATBOT_DUPLICATE_WINDOW_SECONDS = env_int("CHATBOT_DUPLICATE_WINDOW_SECONDS", 4)
    CHATBOT_MAX_OUTPUT_TOKENS = env_int("CHATBOT_MAX_OUTPUT_TOKENS", 350)
    CHATBOT_GEMINI_RETRY_COUNT = env_int("CHATBOT_GEMINI_RETRY_COUNT", 2)

    UPLOAD_FOLDER = BASE_DIR / "uploads" / "resumes"
    MEDIA_UPLOAD_FOLDER = BASE_DIR / "uploads" / "media"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
    ALLOWED_MEDIA_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_flag("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "ai_solution_session")
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    SESSION_REFRESH_EACH_REQUEST = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 6
    COOKIE_PREFERENCE_NAME = os.getenv("COOKIE_PREFERENCE_NAME", "ai_solution_cookie_preference")
    COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365
    EXPOSE_RESET_LINKS_IN_DEBUG = env_flag("EXPOSE_RESET_LINKS_IN_DEBUG", False)

    CONTENT_SECURITY_POLICY = (
        "default-src 'self'; "
        "img-src 'self' data: https://images.unsplash.com https://cdn.pixabay.com; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' https://unpkg.com https://cdn.jsdelivr.net https://www.google.com https://www.gstatic.com; "
        "frame-src 'self' https://www.youtube.com https://www.google.com; "
        "connect-src 'self' https://generativelanguage.googleapis.com https://www.google.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
