"""Correos del sitio: avisos a los administradores y mensajes a los clientes (en el idioma de la reserva).
Si el envío falla (SMTP mal configurado, sin internet…) se registra en el log y el sitio sigue funcionando."""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.utils import timezone

log = logging.getLogger(__name__)


def url_base(request=None):
    """Dirección pública del sitio (con la petición si existe; si no, SITE_URL de settings)."""
    return request.build_absolute_uri("/").rstrip("/") if request else settings.SITE_URL


def por(idioma, es, en, pt):
    """Texto en el idioma guardado en la reserva (es/en/pt)."""
    return {"en": en, "pt": pt}.get(idioma, es)


def correos_admin():
    """NOTIFICAR_A (settings) + usuarios activos del Django Admin con «Es staff» y correo."""
    staff = get_user_model().objects.filter(is_active=True, is_staff=True).exclude(email="").values_list("email", flat=True)
    return sorted({e.strip().lower() for e in [*settings.NOTIFICAR_A, *staff] if e and e.strip()})


def enviar(asunto, cuerpo, destinatarios, reply_to=None):
    destinatarios = [d for d in destinatarios if d]
    if not destinatarios:
        return False
    try:
        EmailMessage(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, destinatarios, reply_to=[reply_to] if reply_to else None).send()
        return True
    except Exception:
        log.exception("No se pudo enviar el correo «%s»", asunto)
        return False


def _firma():
    s = settings.SITIO
    return f"\n\n{s['nombre']}\n{s['direccion']}\nWhatsApp: {s['telefono']} · {s['email']}"


def _fechas(r):
    return f"{r.fecha_entrada:%d/%m/%Y}", f"{r.fecha_salida:%d/%m/%Y}"


# ---------- Avisos a los administradores ----------
def aviso_mensaje(base, m):
    """Nuevo mensaje del formulario de contacto (se puede responder con «Responder»)."""
    cuerpo = (f"Has recibido un nuevo mensaje desde el formulario de contacto.\n\nDe: {m.nombre} <{m.correo}>\n"
              f"Fecha: {timezone.localtime(m.fecha_envio):%d/%m/%Y %H:%M}\n\n{m.contenido}\n\n— Gestiónalo en el panel: {base}/panel/mensajes/")
    return enviar(f"Nuevo mensaje de contacto: {m.nombre} ({m.codigo})", cuerpo, correos_admin(), reply_to=m.correo)


def aviso_solicitud(base, r):
    """Nueva solicitud de reserva hecha desde el sitio (queda PENDIENTE hasta que la administradora la acepte)."""
    e, s = _fechas(r)
    cuerpo = (f"Nueva solicitud de reserva #{r.id} (pendiente).\n\nHuésped: {r.nombre} {r.apellido} · RUT/DNI {r.cliente_id}\n"
              f"Correo: {r.correo} · Teléfono: {r.telefono}\nEstadía: {e} → {s} ({r.noches} noche(s))\n"
              f"Personas: {r.cant_adultos} adulto(s), {r.cant_ninos or 0} niño(s)\n\n"
              f"El huésped continúa la conversación por WhatsApp. Gestiona la reserva en: {base}/panel/reservas/pendientes/")
    return enviar(f"Nueva solicitud de reserva #{r.id}: {r.nombre} {r.apellido}", cuerpo, correos_admin(), reply_to=r.correo)


def aviso_resena(base, res):
    cuerpo = (f"{res.nombre_publico or res.reserva.nombre} dejó una reseña ({res.calificacion}/5) de su estadía #{res.reserva_id}:\n\n"
              f"{res.comentario or '(sin comentario)'}\n\nLa reseña NO se muestra en el sitio hasta que la marques como visible: {base}/panel/resenas/")
    return enviar(f"Nueva reseña ({res.calificacion}/5) por moderar", cuerpo, correos_admin())


# ---------- Correos al cliente ----------
def reserva_aceptada(base, r):
    """Se envía cuando la administradora ACEPTA (confirma) la reserva."""
    e, s = _fechas(r)
    cuerpo = por(r.idioma,
        f"Hola {r.nombre},\n\n¡Tu reserva fue confirmada! Te esperamos.\n\nReserva #{r.id}\nLlegada: {e}\nSalida: {s} ({r.noches} noche(s))\n"
        f"Huéspedes: {r.cant_adultos} adulto(s), {r.cant_ninos or 0} niño(s)\n\nSi necesitas hacer cambios o cancelar, escríbenos por WhatsApp.",
        f"Hello {r.nombre},\n\nYour booking is confirmed! We look forward to welcoming you.\n\nBooking #{r.id}\nCheck-in: {e}\nCheck-out: {s} ({r.noches} night(s))\n"
        f"Guests: {r.cant_adultos} adult(s), {r.cant_ninos or 0} child(ren)\n\nIf you need to change or cancel it, please write to us on WhatsApp.",
        f"Olá {r.nombre},\n\nSua reserva foi confirmada! Esperamos você.\n\nReserva #{r.id}\nChegada: {e}\nSaída: {s} ({r.noches} noite(s))\n"
        f"Hóspedes: {r.cant_adultos} adulto(s), {r.cant_ninos or 0} criança(s)\n\nSe precisar fazer alterações ou cancelar, escreva para nós pelo WhatsApp.")
    asunto = por(r.idioma, f"Reserva confirmada #{r.id} · {settings.SITIO['nombre']}", f"Booking confirmed #{r.id} · {settings.SITIO['nombre']}",
                 f"Reserva confirmada #{r.id} · {settings.SITIO['nombre']}")
    return enviar(asunto, cuerpo + _firma(), [r.correo])


def pedir_resena(base, r, res):
    """Invitación a dejar una reseña. El enlace lleva el token único de ESA reserva y sirve una sola vez."""
    enlace = f"{base}/resena/{res.token}/"
    dias = settings.RESENA_DIAS_VALIDEZ
    cuerpo = por(r.idioma,
        f"Hola {r.nombre},\n\nGracias por hospedarte con nosotros. Nos encantaría conocer tu opinión sobre tu estadía.\n\nDeja tu reseña aquí:\n{enlace}\n\n"
        f"Este enlace es personal (solo para esta reserva), se puede usar una vez y vence en {dias} días.",
        f"Hello {r.nombre},\n\nThank you for staying with us. We would love to hear what you thought of your stay.\n\nLeave your review here:\n{enlace}\n\n"
        f"This link is personal (only for this booking), can be used once and expires in {dias} days.",
        f"Olá {r.nombre},\n\nObrigado por se hospedar conosco. Adoraríamos saber o que você achou da sua estadia.\n\nDeixe sua avaliação aqui:\n{enlace}\n\n"
        f"Este link é pessoal (somente para esta reserva), pode ser usado uma vez e expira em {dias} dias.")
    asunto = por(r.idioma, f"¿Cómo fue tu estadía? · {settings.SITIO['nombre']}", f"How was your stay? · {settings.SITIO['nombre']}",
                 f"Como foi sua estadia? · {settings.SITIO['nombre']}")
    return enviar(asunto, cuerpo + _firma(), [r.correo])
