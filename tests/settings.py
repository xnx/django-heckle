"""Settings for the package's own tests, independent of any site."""

from pathlib import Path

import django

SECRET_KEY = "heckle-tests"
DEBUG = False
USE_TZ = True
ALLOWED_HOSTS = ["testserver"]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "heckle",
    "tests",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "tests.urls"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [Path(__file__).parent / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
STATIC_URL = "/static/"
MANAGERS = [("Moderator", "moderator@example.com")]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
HECKLE_MIN_SECONDS = 0

# Django 6.1 replaces EMAIL_BACKEND with MAILERS (the test runner makes each mailer
# keep its messages in memory); before 6.1, the test runner sets EMAIL_BACKEND.
if django.VERSION >= (6, 1):
    MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
