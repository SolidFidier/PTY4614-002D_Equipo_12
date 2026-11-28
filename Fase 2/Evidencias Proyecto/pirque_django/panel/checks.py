"""Avisos de seguridad para el servidor de producción (riesgo R01).

Se muestran al iniciar el servidor y con `python manage.py check`. No detienen el sitio: solo avisan qué falta configurar.
"""
from django.conf import settings
from django.core.checks import Tags, Warning, register

CLAVE_DE_EJEMPLO = "cambia-esta-clave-en-produccion"


@register(Tags.security)
def seguridad_produccion(app_configs, **kwargs):
    if settings.DEBUG:
        return []          # en desarrollo no se exige nada de esto
    avisos = []
    if settings.SECRET_KEY == CLAVE_DE_EJEMPLO or len(settings.SECRET_KEY) < 40:
        avisos.append(Warning(
            "La clave secreta es la de ejemplo o es muy corta.",
            hint="Define DJANGO_SECRET_KEY en el servidor con una clave larga y aleatoria "
                 "(python -c \"from django.core.management.utils import get_random_secret_key as g; print(g())\").",
            id="pirque.W001"))
    if not getattr(settings, "HTTPS", False):
        avisos.append(Warning(
            "El sitio no está obligando a usar https.",
            hint="Cuando el dominio tenga certificado, define DJANGO_HTTPS=1 en el servidor.", id="pirque.W002"))
    if "*" in settings.ALLOWED_HOSTS:
        avisos.append(Warning(
            "ALLOWED_HOSTS acepta cualquier dominio.",
            hint="Define DJANGO_ALLOWED_HOSTS con el dominio del sitio, por ejemplo: hospedajepirque.cl,www.hospedajepirque.cl",
            id="pirque.W003"))
    return avisos
