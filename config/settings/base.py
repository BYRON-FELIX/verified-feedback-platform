"""Base Django settings for the Verified Consumer Feedback Platform."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# Core
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key-change-me")
DEBUG = True #env("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Apps
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.common.apps.CommonConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.geo.apps.GeoConfig",
    "apps.reviewers.apps.ReviewersConfig",
    "apps.businesses.apps.BusinessesConfig",
    "apps.campaigns.apps.CampaignsConfig",
    "apps.wallets.apps.WalletsConfig",
    "apps.submissions.apps.SubmissionsConfig",
    "apps.withdrawals.apps.WithdrawalsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.payments.apps.PaymentsConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database — dev uses SQLite; prod overrides to Postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Auth
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# i18n
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# Static / media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
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
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Verified Consumer Feedback Platform API",
    "DESCRIPTION": "Kenya-first verified consumer feedback & market research marketplace.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# CORS
# Keep development permissive only when explicitly enabled; production defaults to a safer configuration.
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOW_CREDENTIALS = True

# Email (console in dev)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@vfplatform.local"

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ------------------------------------------------------------------
# Platform config — currency & fees
# ------------------------------------------------------------------
from decimal import Decimal  # noqa: E402

# Amounts are stored in USD everywhere.
# KSH_PER_USD is used only for M-Pesa transactions and display for Kenyan users.
KSH_PER_USD = Decimal("150.00")

# Display currency for the platform
DISPLAY_CURRENCY = "USD"
DISPLAY_CURRENCY_SYMBOL = "$"

# Platform fee percentage applied on top of a business's campaign budget.
PLATFORM_FEE_PERCENTAGE = Decimal("25.00")

# Withholding tax applied to reviewer withdrawals (in their local currency).
WITHHOLDING_TAX_PERCENTAGE = Decimal("5.00")

# Minimum withdrawal in USD
MIN_WITHDRAWAL_USD = Decimal("100.00")

# Phone verification deposit
SUBMISSION_AUTO_VERIFY = env.bool("SUBMISSION_AUTO_VERIFY", default=True)

# PayHero M-Pesa collection
PAYHERO_BASE_URL = env("PAYHERO_BASE_URL", default="https://backend.payhero.co.ke")
PAYHERO_AUTH_TOKEN = env("PAYHERO_AUTH_TOKEN", default="")
PAYHERO_API_KEY = env("PAYHERO_API_KEY", default="")
PAYHERO_API_SECRET = env("PAYHERO_API_SECRET", default="")
PAYHERO_CHANNEL_ID = env.int("PAYHERO_CHANNEL_ID", default=0)
PAYHERO_CALLBACK_BASE_URL = env("PAYHERO_CALLBACK_BASE_URL", default="")
PAYHERO_TIMEOUT_SECONDS = env.int("PAYHERO_TIMEOUT_SECONDS", default=15)

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}