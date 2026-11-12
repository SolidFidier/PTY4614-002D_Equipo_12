import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "cambia-esta-clave-en-produccion")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*" if DEBUG else "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sitio",
    "panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "panel.middleware.PanelEnEspanol",   # el panel siempre se ve en español
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
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
                "django.template.context_processors.i18n",
                "sitio.context.sitio",
                "panel.context.pendientes",   # burbuja de mensajes sin gestionar
            ]
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Base de datos PostgreSQL (ejecuta: python manage.py preparar_bd (usa los scripts de base_de_datos/))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "hospedaje_pirque_bd"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# Permite iniciar sesión en el panel con correo o usuario
AUTHENTICATION_BACKENDS = ["panel.backends.EmailOUsuario"]
LOGIN_URL = "panel:login"

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("es", "Español"),
    ("en", "English"),
    ("pt", "Português"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Datos del hospedaje (usados en las plantillas y en los correos)
SITIO = {
    "nombre": "Hospedaje Rural Pirque",
    "direccion": "Parque real 8 b - Pirque - Chile",
    "telefono": "+569 9771 0934",
    "whatsapp": "56931447377",
    "email": "martin.ponce579@gmail.com",
    "instagram": "hospedajeruralpirque",
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
SESSION_COOKIE_AGE = 60 * 60 * 8

# Cookies propias del proyecto: las cookies de localhost/127.0.0.1 se comparten entre TODOS los proyectos Django que
# corras en ese equipo (aunque usen otro puerto). Con el nombre por defecto (csrftoken / sessionid) otro proyecto
# o una versión anterior pisa la cookie y aparece «403 CSRF token from POST incorrect» o se pierde la sesión.
CSRF_COOKIE_NAME = "pirque_csrftoken"
SESSION_COOKIE_NAME = "pirque_sessionid"
LANGUAGE_COOKIE_NAME = "pirque_idioma"
# Si aun así el token vence, el sitio vuelve a la página anterior con un aviso en lugar de mostrar el 403.
CSRF_FAILURE_VIEW = "sitio.views.csrf_fallo"

# ---------------- Correo ----------------
# Por defecto los correos se IMPRIMEN en la terminal (no se envían). Para enviarlos de verdad define:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST_USER=tu_correo@gmail.com   EMAIL_HOST_PASSWORD=<contraseña de aplicación de Gmail>
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", f'{SITIO["nombre"]} <{EMAIL_HOST_USER or SITIO["email"]}>')
# Avisos de mensajes y cancelaciones: estas direcciones + los usuarios del Django Admin con "Es staff" y correo.
NOTIFICAR_A = [e.strip() for e in os.getenv("NOTIFICAR_A", SITIO["email"]).split(",") if e.strip()]

# ---------------- Reseñas y enlaces ----------------
# Carpeta con los scripts de la base de datos (preparar_bd y cargar_datos_prueba la usan).
BD_DIR = BASE_DIR / "base_de_datos"
# Dirección pública del sitio: se usa en los correos enviados SIN una petición web (python manage.py enviar_resenas).
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
# El enlace de reseña enviado por correo vence a los X días de la solicitud (y sirve una sola vez).
RESENA_DIAS_VALIDEZ = int(os.getenv("RESENA_DIAS_VALIDEZ", "60"))
