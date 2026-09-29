from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_ALL_ORIGINS = False

import dj_database_url

# Database
DATABASES = {
    "default": dj_database_url.config(
        default=env("DATABASE_URL", default="postgresql://verified_feedback_db_user:KBryKfJcSG5mp7gQLFMEvjPwbSLzyqnc@dpg-dap8sjvf3r2c73eearhg-a.oregon-postgres.render.com/verified_feedback_db"),
        conn_max_age=600
    )
}

# Static files
STATIC_ROOT = BASE_DIR / "staticfiles"

MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
] + MIDDLEWARE

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Security
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# HTTPS / Security
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True