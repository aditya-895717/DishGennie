"""
Django settings for DishGennie.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Detect hosted environments
IS_VERCEL = bool(os.environ.get("VERCEL"))
IS_RENDER = bool(os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_HOSTNAME"))
IS_HOSTED = IS_VERCEL or IS_RENDER or bool(os.environ.get("DATABASE_URL"))

# Only load .env file for local development
if not IS_HOSTED:
    load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=None):
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


def env_int(name, default=0):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# Security
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-local-dev-key-change-me")
DEBUG = env_bool("DEBUG", default=False)

# The production domain is always trusted, whether or not ALLOWED_HOSTS is
# set in the environment — a missing env var must not take the live site down.
PRIMARY_HOST = "dishgennie.adityadubey.co.in"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
for _required_host in (PRIMARY_HOST, "localhost", "127.0.0.1"):
    if _required_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_required_host)

RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
# Allow any *.vercel.app subdomain (covers preview + production deploys)
if ".vercel.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".vercel.app")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
if f"https://{PRIMARY_HOST}" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(f"https://{PRIMARY_HOST}")
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
# Trust all Vercel subdomains for CSRF
if "https://*.vercel.app" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    # Local apps
    "apps.accounts",
    "apps.services",
    "apps.bookings",
    "apps.payments",
    "apps.reviews",
    "apps.notifications",
    "apps.tracking",
    "apps.support",
    "apps.analytics",
    "apps.filestore",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.accounts.middleware.NoCacheAfterLogoutMiddleware",
]

ROOT_URLCONF = "dishgennie.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "dishgennie.wsgi.application"

# Database
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{(BASE_DIR / 'db.sqlite3').as_posix()}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Custom User Model
AUTH_USER_MODEL = "accounts.CustomUser"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Manifest storage makes every {% static %} tag raise if collectstatic has
# not produced staticfiles.json — which turns one missing build step into a
# 500 on every single page. Use it only when the manifest is actually there
# (and while generating it), so a build hiccup degrades to unstyled rather
# than down.
_MANIFEST_EXISTS = (STATIC_ROOT / "staticfiles.json").exists()
_COLLECTING_STATIC = "collectstatic" in sys.argv
_STATICFILES_BACKEND = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
    if (_MANIFEST_EXISTS or _COLLECTING_STATIC)
    else "whitenoise.storage.CompressedStaticFilesStorage"
)

# Uploaded media lives in Postgres (apps.filestore), not on disk: Vercel's
# serverless filesystem is read-only and /tmp does not survive between
# invocations, so a FileSystemStorage default would fail on the first maid
# registration. Served back by apps.filestore.views.serve_media at MEDIA_URL.
STORAGES = {
    "default": {
        "BACKEND": "apps.filestore.storage.DatabaseStorage",
    },
    "staticfiles": {
        "BACKEND": _STATICFILES_BACKEND,
    },
}

# Lets WhiteNoise fall back to the source assets when STATIC_ROOT is empty.
WHITENOISE_USE_FINDERS = True

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # unused by DatabaseStorage; kept for tooling
FILESTORE_MAX_UPLOAD_BYTES = env_int("FILESTORE_MAX_UPLOAD_BYTES", 8 * 1024 * 1024)

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
)
# Allow any *.vercel.app subdomain via regex
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOW_CREDENTIALS = True

# Razorpay
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

# Login / Logout redirects
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/accounts/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Django Messages: use session storage for reliability
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Email — all transactional mail goes via Brevo SDK.
# dummy backend silences any stray send_mail() calls (avoids SMTP ConnectionRefusedError).
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "DishGennie <noreply@dishgennie.com>",
)

# Brevo SDK
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")

# Admin notifications (new registrations, etc.) are sent here.
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "info@adityadubey.co.in")

# `manage.py test` only — patches the Brevo SDK call for the whole run so no
# test can ever hit the live API. Has no effect outside the test runner.
TEST_RUNNER = "dishgennie.test_runner.NoBrevoTestRunner"

# ─── Session configuration ────────────────────────────────────────────
# On Vercel (serverless, read-only filesystem) we MUST use cookie-based
# sessions.  SQLite cannot be written to, so the default DB-backed
# sessions will crash with a 500 on every POST that touches the session.
# Cookie sessions were originally forced on Vercel because the default
# DB-backed sessions would have tried to write to SQLite on a read-only
# filesystem. With DATABASE_URL pointing at Neon that no longer applies, and
# DB sessions are the better choice: signed cookies are signed but *not*
# encrypted, and the in-flight registration payload parked in the session
# includes the user's chosen password. Cookies remain the fallback for the
# one case that still can't write — SQLite on Vercel.
_DB_IS_SQLITE = "sqlite" in DATABASES["default"].get("ENGINE", "")
if IS_VERCEL and _DB_IS_SQLITE:
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
else:
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", default=False)

# ─── Logging ──────────────────────────────────────────────────────────
# Ensure errors are printed to stdout/stderr so they appear in
# Vercel Function Logs (and Render logs, local console, etc.)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
