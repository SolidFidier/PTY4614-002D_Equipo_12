"""Lógica compartida entre el panel, los comandos y el sitio: invitaciones de reseña."""
import logging
import secrets
import threading
from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone

from .models import Reserva, Resena

log = logging.getLogger(__name__)
_ultima_revision = None  # última vez que el panel revisó reseñas pendientes (se hace como máximo cada 6 horas)


def enviar_invitacion(base_url, reserva):
    """Envía (o reenvía) la invitación de reseña de UNA reserva. Devuelve (ok, mensaje)."""
    from sitio import correos  # import tardío
    if not reserva.correo:
        return False, "La reserva no tiene correo."
    res = Resena.objects.filter(reserva=reserva).first()
    if res and res.respondida:
        return False, "Este huésped ya dejó su reseña."
    if not res:
        res = Resena.objects.create(reserva=reserva, token=secrets.token_urlsafe(32))
    if correos.pedir_resena(base_url, reserva, res):
        res.fecha_solicitud = timezone.now()
        res.save(update_fields=["fecha_solicitud"])
        return True, f"Invitación enviada a {reserva.correo}."
    return False, "No se pudo enviar el correo (revisa la configuración de correo)."


def solicitar_resenas(base_url=None):
    """Envía la invitación a cada estadía TERMINADA que aún no la recibió (solo las de los últimos RESENA_DIAS_VALIDEZ días).
    Devuelve (enviados, fallidos)."""
    base_url = (base_url or settings.SITE_URL).rstrip("/")
    hoy = timezone.localdate()
    reservas = [r for r in Reserva.objects.filter(estado_reserva="aceptada", fecha_salida__lt=hoy,
                                                  fecha_salida__gte=hoy - timedelta(days=settings.RESENA_DIAS_VALIDEZ)) if r.correo]
    existentes = {x.reserva_id: x for x in Resena.objects.filter(reserva__in=reservas)}
    enviados = fallidos = 0
    for r in reservas:
        res = existentes.get(r.id)
        if res and (res.fecha_resena or res.fecha_solicitud):
            continue  # ya respondió o ya se le envió el correo
        ok, _ = enviar_invitacion(base_url, r)
        enviados, fallidos = enviados + ok, fallidos + (not ok)
    return enviados, fallidos


def revisar_resenas_en_segundo_plano(base_url):
    """Se llama al abrir el panel: como máximo cada 6 horas envía las invitaciones pendientes (sin bloquear la página)."""
    global _ultima_revision
    ahora = timezone.now()
    if _ultima_revision and ahora - _ultima_revision < timedelta(hours=6):
        return
    _ultima_revision = ahora

    def tarea():
        try:
            solicitar_resenas(base_url)
        except Exception:
            log.exception("Falló el envío automático de invitaciones de reseña")
        finally:
            connection.close()
    threading.Thread(target=tarea, daemon=True).start()
