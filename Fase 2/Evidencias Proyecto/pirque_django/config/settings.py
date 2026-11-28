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
# django-extensions es solo una ayuda de desarrollo (requirements-dev.txt): si no está instalada, el sitio funciona igual.
try:
    import django_extensions  # noqa: F401
    INSTALLED_APPS.append("django_extensions")
except ImportError:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "panel.middleware.PanelEnEspanol",   # el panel siempre se ve en español
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
# Recuperación de contraseña del panel: el enlace enviado por correo vence en 1 hora (y sirve una sola vez).
PASSWORD_RESET_TIMEOUT = 60 * 60
# Reglas para contraseñas nuevas (recuperación de contraseña, Django Admin y createsuperuser):
# no parecida al usuario/correo, mínimo 8 caracteres, no una contraseña común y no solo números.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

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

# Datos del hospedaje (usados en las plantillas y en los correos). telefono, whatsapp, email e instagram son los valores
# ORIGINALES: la administradora puede cambiarlos desde Panel → Configuraciones avanzadas (se guardan en la BD y tienen prioridad).
SITIO = {
    "nombre": "Hospedaje Rural Pirque",
    "direccion": "Parque real 8 b - Pirque - Chile",
    "telefono": "+569 9771 0934",
    "whatsapp": "56997710934",
    "email": "alojamientopirque@gmail.com",
    "instagram": "hospedajepirque",
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
# Avisos de mensajes y solicitudes: llegan al correo del hospedaje (el de Panel → Configuraciones avanzadas) y a los
# usuarios del Django Admin con "Es staff" y correo. Si defines NOTIFICAR_A (direcciones separadas por coma), esas
# direcciones reemplazan al correo del hospedaje.
NOTIFICAR_A = [e.strip() for e in os.getenv("NOTIFICAR_A", "").split(",") if e.strip()]

# ---------------- Reseñas y enlaces ----------------
# Carpeta con los scripts de la base de datos (preparar_bd y cargar_datos_prueba la usan).
BD_DIR = BASE_DIR / "base_de_datos"
# Dirección pública del sitio: se usa en los correos enviados SIN una petición web (python manage.py enviar_resenas).
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
# El enlace de reseña enviado por correo vence a los X días de la solicitud (y sirve una sola vez).
RESENA_DIAS_VALIDEZ = int(os.getenv("RESENA_DIAS_VALIDEZ", "60"))

# ---------------- Solicitudes de reserva (riesgo R08: solicitudes falsas o abandonadas) ----------------
# Máximo de solicitudes PENDIENTES (aún sin confirmar) que un mismo cliente puede tener a la vez.
MAX_SOLICITUDES_PENDIENTES = int(os.getenv("MAX_SOLICITUDES_PENDIENTES", "3"))

# ---------------- Respaldos de la base de datos (riesgo R03) ----------------
# python manage.py respaldar_bd guarda un archivo .dump aquí y conserva los últimos RESPALDOS_CONSERVAR.
# Por defecto la carpeta queda FUERA del proyecto (para que nunca se suba a GitHub con datos personales).
# Lo ideal es que sea una carpeta sincronizada con la nube (Google Drive, OneDrive) o un disco externo.
RESPALDOS_DIR = Path(os.getenv("RESPALDOS_DIR", str(Path.home() / "respaldos_hospedaje_pirque")))
RESPALDOS_CONSERVAR = int(os.getenv("RESPALDOS_CONSERVAR", "14"))
PG_DUMP = os.getenv("PG_DUMP", "pg_dump")   # en Windows, p. ej.: C:\Program Files\PostgreSQL\16\bin\pg_dump.exe

# ---------------- Seguridad al publicar (riesgo R01) ----------------
# Cuando el sitio ya tiene certificado (https://), define en el servidor DJANGO_HTTPS=1: redirige todo a https, las cookies
# solo viajan cifradas y el navegador recuerda usar https (HSTS). Se deja opcional para no romper un servidor sin certificado.
HTTPS = os.getenv("DJANGO_HTTPS", "0") == "1"
if HTTPS:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # el hosting atiende el https y avisa con esta cabecera
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", str(60 * 60 * 24 * 30)))
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True          # el panel toma el token CSRF de la etiqueta <meta name="csrf">, no de la cookie
SESSION_COOKIE_HTTPONLY = True

# ---------------- Registro de seguridad (incidentes y cambios importantes) ----------------
# El registro «seguridad» anota: ingresos al panel, intentos fallidos, bloqueos, reservas restauradas o eliminadas,
# clientes eliminados y envíos sospechosos de formularios. Siempre se ve en la consola del servidor; si defines
# DJANGO_LOG_SEGURIDAD=ruta/al/archivo.log también se guarda en ese archivo (rota a los 2 MB y conserva 5 copias).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"consola": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "loggers": {"seguridad": {"handlers": ["consola"], "level": "INFO", "propagate": False}},
}
LOG_SEGURIDAD = os.getenv("DJANGO_LOG_SEGURIDAD", "")
if LOG_SEGURIDAD:
    Path(LOG_SEGURIDAD).parent.mkdir(parents=True, exist_ok=True)
    LOGGING["handlers"]["archivo"] = {"class": "logging.handlers.RotatingFileHandler", "filename": LOG_SEGURIDAD,
                                      "maxBytes": 2_000_000, "backupCount": 5, "encoding": "utf-8", "formatter": "simple"}
    LOGGING["loggers"]["seguridad"]["handlers"].append("archivo")
