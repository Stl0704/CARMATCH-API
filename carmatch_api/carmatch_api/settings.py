"""
Django settings for carmatch_api project.
"""

from pathlib import Path
import os
import json
import ast
from dotenv import load_dotenv

# ---------------------------------------------------------
# Rutas base
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent   # CARMATCH-API/carmatch_api
REPO_DIR = BASE_DIR.parent                          # CARMATCH-API

# Carga variables de entorno desde .env (dos ubicaciones posibles)
load_dotenv(BASE_DIR / ".env",  override=True)      # junto a manage.py
load_dotenv(REPO_DIR / ".env",  override=True)      # raíz del repo

# ---------------------------------------------------------
# Seguridad / Debug
# ---------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-prod")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if os.getenv("DJANGO_ALLOWED_HOSTS") else []

# ---------------------------------------------------------
# Apps
# ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # Tu app
    "core",
]

# ---------------------------------------------------------
# Middleware
# ---------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------
# DRF / Esquema
# ---------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        # Descomenta para navegador DRF en dev:
        # "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "carmatch-api",
    "DESCRIPTION": "API de CarMatch",
    "VERSION": "1.0.0",
}

# ---------------------------------------------------------
# CORS / CSRF
# ---------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True  # En producción: limitar a tus dominios
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# ---------------------------------------------------------
# URLs raíz / WSGI
# ---------------------------------------------------------
ROOT_URLCONF = "carmatch_api.urls"
WSGI_APPLICATION = "carmatch_api.wsgi.application"

# ---------------------------------------------------------
# Templates
# ---------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # /carmatch_api/templates
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

# ---------------------------------------------------------
# BD
# ---------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "carmatch_db"),
        "USER": os.getenv("DB_USER", "carmatch_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 5},
    }
}

# ---------------------------------------------------------
# Password validators
# ---------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------
# i18n
# ---------------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------
# Static
# ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = os.getenv("DJANGO_STATIC_ROOT", "") or None  # en prod puedes setear un path
# Si usas /core/static para tus JS, Django lo encontrará por APP_DIRS=True
# (opcional) si quieres rutas adicionales:
# STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================================================
#                 N8N - Public API
# =========================================================
N8N_API_URL   = os.getenv("N8N_API_URL", "")                # p.ej. http://localhost:5678/api/v1
N8N_API_KEY   = os.getenv("N8N_API_KEY", "")                # JWT de Settings > Public API
N8N_BASE_URL  = os.getenv("N8N_BASE_URL", "")               # p.ej. http://localhost:5678
N8N_PROJECT_ID = os.getenv("N8N_PROJECT_ID", "")            # ID del proyecto (Settings > Projects)

# Modo "single" (puede ir vacío; se usa si defines endpoints single)
N8N_WORKFLOW_ID = os.getenv("N8N_WORKFLOW_ID", "")

# Lista de flujos a administrar (IDs visibles en la URL del editor)
N8N_FLOW_IDS = [s.strip() for s in os.getenv("N8N_FLOW_IDS", "").split(",") if s.strip()]

# Mapa de webhooks por ID (ejecutar ahora)
_raw_webhooks = os.getenv("N8N_WEBHOOKS", "{}").strip()
try:
    N8N_WEBHOOKS = json.loads(_raw_webhooks)
except json.JSONDecodeError:
    try:
        N8N_WEBHOOKS = ast.literal_eval(_raw_webhooks)
    except Exception:
        N8N_WEBHOOKS = {}

# (compat) webhook único
N8N_WEBHOOK_URL   = os.getenv("N8N_WEBHOOK_URL", "")
N8N_WEBHOOK_TOKEN = os.getenv("N8N_WEBHOOK_TOKEN", "")

# ---------------------------------------------------------
# Logging (útil para ver por qué /api/n8n/flows/ devuelve vacío)
# ---------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        # Muestra errores/diagnóstico desde core.n8n_api
        "core.n8n_api": {"handlers": ["console"], "level": "DEBUG"},
        # Requests en WARNING (sube a DEBUG si quieres más verboso)
        "requests": {"handlers": ["console"], "level": "WARNING"},
        "django.request": {"handlers": ["console"], "level": "WARNING"},
    },
}
