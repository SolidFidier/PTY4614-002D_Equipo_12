"""Datos de contacto del hospedaje (teléfono, WhatsApp, correo e Instagram).

Los valores originales están en SITIO (config/settings.py). La administradora puede cambiarlos desde
Panel → Configuraciones avanzadas; los cambios se guardan en la tabla `configuracion` y tienen prioridad.
Si la tabla no existe todavía (falta `python manage.py preparar_bd`) o falla la consulta, el sitio sigue
funcionando con los valores de settings.py.
"""
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DatabaseError, transaction

from panel.models import Configuracion

CLAVES = ("telefono", "whatsapp", "email", "instagram")
_USUARIO_IG = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def valores_originales():
    """Valores de settings.py (los que se usan si no hay nada guardado en la base de datos)."""
    return {c: settings.SITIO[c] for c in CLAVES}


def valores_guardados():
    """{clave: valor} de lo guardado desde el panel ({} si no hay nada o la tabla no está disponible)."""
    try:
        with transaction.atomic():   # punto de guardado: un error aquí no rompe la transacción de la petición
            return {c: v for c, v in Configuracion.objects.filter(clave__in=CLAVES).values_list("clave", "valor") if v}
    except DatabaseError:
        return {}


def datos_sitio():
    """Datos del hospedaje listos para plantillas y correos (settings.SITIO + lo editado en el panel)."""
    d = {**settings.SITIO, **valores_guardados()}
    digitos = re.sub(r"\D", "", d["telefono"])
    d["tel_enlace"] = ("+" if d["telefono"].strip().startswith("+") else "") + digitos   # para href="tel:..."
    return d


# ---------- Normalización y validación de lo que escribe la administradora ----------
def normalizar_telefono(v):
    v = " ".join((v or "").split())
    if not re.fullmatch(r"\+?[\d ()\-]+", v) or not 8 <= len(re.sub(r"\D", "", v)) <= 15:
        raise ValueError("El teléfono debe tener entre 8 y 15 números (puede llevar +, espacios o guiones). Ejemplo: +569 9771 0934")
    return v


def normalizar_whatsapp(v):
    """Solo dígitos con código de país, sin + ni espacios (así lo exige el enlace de WhatsApp). Un móvil chileno de
    9 dígitos que empieza con 9 recibe el 56 automáticamente."""
    d = re.sub(r"\D", "", v or "")
    if len(d) == 9 and d.startswith("9"):
        d = "56" + d
    if not 10 <= len(d) <= 15 or d.startswith("0"):
        raise ValueError("El WhatsApp debe incluir el código de país y tener entre 10 y 15 números. Ejemplo: +56 9 9771 0934")
    return d


def normalizar_correo(v):
    v = (v or "").strip().lower()
    try:
        validate_email(v)
    except ValidationError:
        raise ValueError("El correo no es válido. Ejemplo: contacto@gmail.com") from None
    if len(v) > 100:
        raise ValueError("El correo es demasiado largo.")
    return v


def normalizar_instagram(v):
    """Acepta «usuario», «@usuario» o el enlace completo del perfil y deja solo el nombre de usuario."""
    v = (v or "").strip()
    if "instagram.com" in v.lower():
        v = urlparse(v if "//" in v else "//" + v).path.strip("/").split("/")[0]
    v = v.lstrip("@").strip()
    if not _USUARIO_IG.fullmatch(v):
        raise ValueError("El usuario de Instagram solo puede tener letras, números, puntos y guion bajo (máx. 30). Ejemplo: hospedajepirque")
    return v


NORMALIZADORES = {"telefono": normalizar_telefono, "whatsapp": normalizar_whatsapp,
                  "email": normalizar_correo, "instagram": normalizar_instagram}
