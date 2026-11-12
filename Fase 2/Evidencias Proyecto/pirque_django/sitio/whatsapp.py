"""Mensajes prearmados que se envían por WhatsApp (el cliente puede editarlos antes de enviar).
Usan el formato de WhatsApp: *negrita*, saltos de línea y emojis. No incluyen el RUT/DNI; sí el número de reserva."""
from urllib.parse import quote
from django.conf import settings
from .idioma import L


def enlace(texto):
    # Se usa api.whatsapp.com y NO wa.me: wa.me redirige a api.whatsapp.com y, en esa redirección, los emojis
    # llegan al chat convertidos en «�». Con este enlace directo los emojis se conservan.
    return f"https://api.whatsapp.com/send/?phone={settings.SITIO['whatsapp']}&text={quote(texto, safe='')}"


def _limpio(texto):
    """Quita los símbolos que WhatsApp usa para dar formato, para que un nombre raro no rompa la negrita."""
    return " ".join(str(texto).translate({ord(c): None for c in "*_~`"}).split())


def _noches(n):
    return (f"{n} noche{'s' if n != 1 else ''}", f"{n} night{'s' if n != 1 else ''}", f"{n} noite{'s' if n != 1 else ''}")


def _personas(adultos, ninos):
    """Texto de huéspedes con singular/plural correctos; si no hay niños, solo se nombran los adultos."""
    es = f"{adultos} adulto{'s' if adultos != 1 else ''}" + (f" y {ninos} niño{'s' if ninos != 1 else ''}" if ninos else "")
    en = f"{adultos} adult{'s' if adultos != 1 else ''}" + (f" and {ninos} {'child' if ninos == 1 else 'children'}" if ninos else "")
    pt = f"{adultos} adulto{'s' if adultos != 1 else ''}" + (f" e {ninos} criança{'s' if ninos != 1 else ''}" if ninos else "")
    return es, en, pt


def solicitud(r):
    nombre = _limpio(f"{r.nombre} {r.apellido}")
    e, s = f"{r.fecha_entrada:%d/%m/%Y}", f"{r.fecha_salida:%d/%m/%Y}"
    n_es, n_en, n_pt = _noches(r.noches)
    p_es, p_en, p_pt = _personas(r.cant_adultos, r.cant_ninos or 0)
    return enlace(L(
        f"¡Hola! 👋 Soy *{nombre}* y me gustaría solicitar una estadía en Hospedaje Rural Pirque 🌿\n\n"
        f"📅 *Llegada:* {e}\n"
        f"📅 *Salida:* {s}\n"
        f"🌙 *Estadía:* {n_es}\n"
        f"👥 *Personas:* {p_es}\n"
        f"✉️ *Correo:* {r.correo}\n\n"
        f"🔖 *Solicitud N° {r.id}*\n\n"
        f"¡Gracias! Quedo atento/a a su respuesta 🙏",
        f"Hello! 👋 I'm *{nombre}* and I would like to request a stay at Hospedaje Rural Pirque 🌿\n\n"
        f"📅 *Check-in:* {e}\n"
        f"📅 *Check-out:* {s}\n"
        f"🌙 *Stay:* {n_en}\n"
        f"👥 *Guests:* {p_en}\n"
        f"✉️ *Email:* {r.correo}\n\n"
        f"🔖 *Request No. {r.id}*\n\n"
        f"Thank you! I look forward to your reply 🙏",
        f"Olá! 👋 Sou *{nombre}* e gostaria de solicitar uma estadia no Hospedaje Rural Pirque 🌿\n\n"
        f"📅 *Chegada:* {e}\n"
        f"📅 *Saída:* {s}\n"
        f"🌙 *Estadia:* {n_pt}\n"
        f"👥 *Hóspedes:* {p_pt}\n"
        f"✉️ *E-mail:* {r.correo}\n\n"
        f"🔖 *Solicitação nº {r.id}*\n\n"
        f"Obrigado(a)! Aguardo sua resposta 🙏"))


def cancelacion(r):
    nombre = _limpio(f"{r.nombre} {r.apellido}")
    e, s = f"{r.fecha_entrada:%d/%m/%Y}", f"{r.fecha_salida:%d/%m/%Y}"
    return enlace(L(
        f"Hola 👋 Soy *{nombre}*.\n\n"
        f"Lamentablemente necesito *cancelar* mi reserva 😔\n\n"
        f"🔖 *Reserva N° {r.id}*\n"
        f"📅 {e} → {s}\n\n"
        f"Muchas gracias por su comprensión 🙏",
        f"Hello 👋 I'm *{nombre}*.\n\n"
        f"Unfortunately I need to *cancel* my booking 😔\n\n"
        f"🔖 *Booking No. {r.id}*\n"
        f"📅 {e} → {s}\n\n"
        f"Thank you very much for your understanding 🙏",
        f"Olá 👋 Sou *{nombre}*.\n\n"
        f"Infelizmente preciso *cancelar* minha reserva 😔\n\n"
        f"🔖 *Reserva nº {r.id}*\n"
        f"📅 {e} → {s}\n\n"
        f"Muito obrigado(a) pela compreensão 🙏"))