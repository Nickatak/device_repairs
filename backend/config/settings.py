"""
Django settings for the device-repair working log.

Single-user, no-auth MVP: back-of-house is the Django admin. Patterns (env-driven
config, DATABASE_URL parsing, prod-hardening guard, logging) borrowed from bill_n_chill.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# backend/ — manage.py lives here.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# HTTPS-only hardening, gated on its own flag: dock01 runs DEBUG=False on
# plain-HTTP LAN, where Secure cookies would silently break admin logins and
# HSTS would poison the hostname. Set DJANGO_HTTPS=true only behind real TLS.
if os.getenv("DJANGO_HTTPS", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Fail fast if dangerous dev defaults slipped into production.
    _prod_checks = []
    if SECRET_KEY == "django-insecure-dev-only-change-me":
        _prod_checks.append("DJANGO_SECRET_KEY is still the insecure default")
    if ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
        _prod_checks.append("DJANGO_ALLOWED_HOSTS is still the dev default")
    if _prod_checks:
        raise ImproperlyConfigured(
            "Production startup blocked:\n  - " + "\n  - ".join(_prod_checks)
        )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",  # wired for the later API; no endpoints in the admin-only MVP.
    "repairs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def database_config_from_url(database_url: str) -> dict:
    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "127.0.0.1",
            "PORT": str(parsed.port or 5432),
        }

    if scheme == "sqlite":
        sqlite_path = parsed.path or "/db.sqlite3"
        if sqlite_path.startswith("/"):
            sqlite_path = sqlite_path[1:]
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / sqlite_path,
        }

    raise ValueError(f"Unsupported DATABASE_URL scheme: {scheme}")


def load_database_config() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_config_from_url(database_url)

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "device_repair"),
        "USER": os.getenv("POSTGRES_USER", "repair"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "repair_password"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }


DATABASES = {"default": load_database_config()}

# No auth surface in the MVP, but keep the validators wired for when accounts land.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic target; served by urls.py in prod

# User-uploaded repair/step photos (the Media model).
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging — console always; file when a writable LOG_DIR exists.
_default_log_dir = BASE_DIR.parent / "logs"
LOG_DIR = Path(os.getenv("LOG_DIR", str(_default_log_dir)))
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    LOG_DIR = BASE_DIR.parent / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG" if DEBUG else "INFO",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "app.log",
            "formatter": "standard",
            "level": "INFO",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "repairs": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
    "root": {"handlers": ["console", "file"], "level": "WARNING"},
}
