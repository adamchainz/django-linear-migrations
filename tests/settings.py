from __future__ import annotations

SECRET_KEY = "NOTASECRET"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": True,
    },
}

TIME_ZONE = "UTC"

INSTALLED_APPS = [
    "tests.testapp",
    "django_linear_migrations",
    # Force django_migrations creation by having an app with migrations:
    "django.contrib.contenttypes",
]

USE_TZ = True
