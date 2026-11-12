import logging
import re
from functools import wraps
from pathlib import Path
from urllib.parse import quote
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from panel.models import Cliente, Reserva, Mensaje, Resena
from . import correos, whatsapp
from .forms import ClienteLoginForm, MensajeForm, ReservaForm
from .idioma import L, idioma

log = logging.getLogger(__name__)

HORAS = ["Cerrado", "13:00 - 16:00 / 20:00 - 24:00", "13:00 - 16:00 / 20:00 - 24:00", "13:00 - 16:00 / 20:00 - 24:00",
         "13:00 - 16:00 / 20:00 - 01:00", "13:00 - 16:00 / 20:00 - 01:00", "13:00 - 16:00"]
DIAS = [("Lunes", "Monday", "Segunda"), ("Martes", "Tuesday", "Terça"), ("Miércoles", "Wednesday", "Quarta"), ("Jueves", "Thursday", "Quinta"),
        ("Viernes", "Friday", "Sexta"), ("Sábado", "Saturday", "Sábado"), ("Domingo", "Sunday", "Domingo")]

# Estado de la reserva -> (es, en, pt, color Bootstrap)
ESTADOS = {
    "pendiente": ("Pendiente de confirmación", "Pending confirmation", "Pendente de confirmação", "warning text-dark"),
    "aceptada": ("Aceptada", "Accepted", "Aceita", "success"),
    "terminada": ("Finalizada", "Completed", "Concluída", "secondary"),
    "cancelada": ("Cancelada", "Cancelled", "Cancelada", "danger"),
}


def _horario():
    hoy = timezone.localdate().weekday()   # lunes = 0, igual que HORAS
    return [{"dia": L(*DIAS[i]), "hora": h, "cerrado": h == "Cerrado", "hoy": i == hoy} for i, h in enumerate(HORAS)]


def _imagenes_carrusel():
    """Imágenes de static/img cuyo nombre contiene «carrusel» (carrusel1.png, carrusel2.jpg…), en orden numérico."""
    carpeta = Path(settings.STATICFILES_DIRS[0]) / "img"
    if not carpeta.is_dir():
        return []
    ok = {".jpg", ".jpeg", ".png", ".webp"}
    nombres = [p.name for p in carpeta.iterdir() if "carrusel" in p.name.lower() and p.suffix.lower() in ok]
    nombres.sort(key=lambda n: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", n.lower())])
    return [f"img/{n}" for n in nombres]


def inicio(request):
    resenas = list(Resena.objects.filter(visible=True, fecha_resena__isnull=False).order_by("-fecha_resena")[:6])
    return render(request, "sitio/inicio.html", {"resenas": resenas})


def servicios(request):
    return render(request, "sitio/servicios.html", {"horario": _horario(), "carrusel": _imagenes_carrusel()})


def quienes_somos(request):
    return render(request, "sitio/quienes_somos.html")


def como_llegar(request):
    return render(request, "sitio/como_llegar.html")


def contacto(request):
    form = MensajeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        m = Mensaje.objects.create(nombre=d["nombre"].strip(), correo=d["correo"].strip(), contenido=d["mensaje"].strip(), fecha_envio=timezone.now())
        correos.aviso_mensaje(correos.url_base(request), m)   # notificación por correo a los administradores
        messages.success(request, L("Mensaje enviado. Te responderemos pronto.", "Message sent. We will reply soon.", "Mensagem enviada. Responderemos em breve."))
        return redirect("contacto")
    return render(request, "sitio/contacto.html", {"form": form})


# --- IDENTIFICACIÓN DEL CLIENTE (sesión; no se crean usuarios de Django para los huéspedes) ---
def huesped_requerido(vista):
    @wraps(vista)
    def _v(request, *a, **k):
        if not request.session.get("huesped"):
            return redirect(f"{reverse('login_cliente')}?next={quote(request.get_full_path())}")
        return vista(request, *a, **k)
    return _v


def _siguiente(request, defecto):
    nxt = request.POST.get("next") or request.GET.get("next")
    ok = nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()})
    return nxt if ok else defecto


def login_cliente(request):
    ini = request.session.get("huesped") or {}
    form = ClienteLoginForm(request.POST or None, initial={**ini, "rut": ini.get("documento", "")})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        request.session.cycle_key()
        request.session["huesped"] = {"nombre": d["nombre"].strip(), "apellido": d["apellido"].strip(), "correo": d["correo"].strip().lower(),
                                      "documento": d["rut"], "telefono": d["telefono"], "extranjero": d["extranjero"]}
        return redirect(_siguiente(request, reverse("reservar")))
    return render(request, "sitio/login_cliente.html", {"form": form})


def logout_cliente(request):
    request.session.flush()
    messages.info(request, L("Has cerrado sesión correctamente.", "You have been signed out.", "Você saiu da sua conta com sucesso."))
    return redirect("inicio")


# --- SOLICITUD DE RESERVA: se guarda como PENDIENTE y se redirige a WhatsApp con el mensaje prearmado ---
def _registrar_solicitud(request, hu, d):
    """Crea el cliente (o actualiza sus datos si el RUT/DNI ya existe) y la reserva pendiente. Devuelve (reserva, es_nueva)."""
    with transaction.atomic():
        Cliente.objects.update_or_create(id=hu["documento"], defaults=dict(
            nombre=hu["nombre"], apellido=hu["apellido"], telefono=hu["telefono"], correo=hu["correo"],
            nacionalidad="Extranjero" if hu["extranjero"] else "Chileno"))
        r = Reserva.objects.filter(cliente_id=hu["documento"], fecha_entrada=d["llegada"], fecha_salida=d["salida"], estado_reserva="pendiente").first()
        datos = dict(nombre=hu["nombre"], apellido=hu["apellido"], correo=hu["correo"], telefono=hu["telefono"],
                     cant_adultos=d["adultos"], cant_ninos=d["ninos"], idioma=idioma())
        if r:   # el mismo grupo pidiendo las mismas fechas: no se duplica la solicitud
            Reserva.objects.filter(pk=r.pk).update(**datos)
            r.refresh_from_db()
            return r, False
        r = Reserva.objects.create(cliente_id=hu["documento"], fecha_entrada=d["llegada"], fecha_salida=d["salida"], monto=0,
                                   estado_reserva="pendiente", estado_pago="pendiente", notas="", fecha_reserva=timezone.now(), **datos)
        return r, True


@huesped_requerido
def reservar(request):
    form = ReservaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        r, nueva = _registrar_solicitud(request, request.session["huesped"], form.cleaned_data)
        if nueva:
            correos.aviso_solicitud(correos.url_base(request), r)   # aviso por correo a los administradores
        return redirect(whatsapp.solicitud(r))                       # redirección directa a WhatsApp
    return render(request, "sitio/reservar.html", {"form": form, "api_url": reverse("api_disponibilidad")})


def api_disponibilidad(request):
    """Rangos ya ocupados (reservas ACEPTADAS) para mostrarlos en rojo en el calendario."""
    rs = Reserva.objects.filter(estado_reserva="aceptada", fecha_salida__gt=timezone.localdate())
    return JsonResponse({"ocupadas": [{"from": r.fecha_entrada.isoformat(), "to": (r.fecha_salida - timedelta(days=1)).isoformat()} for r in rs]})


@huesped_requerido
def mis_reservas(request):
    hu = request.session["huesped"]   # deben coincidir el documento y el correo con los de la reserva
    lista = list(Reserva.objects.filter(cliente_id=hu["documento"], correo__iexact=hu["correo"]).order_by("-fecha_entrada"))
    hoy = timezone.localdate()
    for r in lista:
        t = ESTADOS[r.seccion]
        r.etiqueta, r.color = t[{"es": 0, "en": 1, "pt": 2}[idioma()]], t[3]
        r.puede_cancelar = r.estado_reserva in ("pendiente", "aceptada") and r.fecha_salida >= hoy
        r.wa_cancelar = whatsapp.cancelacion(r) if r.puede_cancelar else ""
    return render(request, "sitio/mis_reservas.html", {"reservas": lista})


# --- RESEÑA: enlace personal enviado por correo (un solo uso, vence a los RESENA_DIAS_VALIDEZ días) ---
def _estado_resena(res):
    if res.fecha_resena:
        return "ya"
    if res.reserva.estado_reserva != "aceptada":
        return "invalida"
    if res.fecha_solicitud and timezone.now() - res.fecha_solicitud > timedelta(days=settings.RESENA_DIAS_VALIDEZ):
        return "vencida"
    return "ok"


def resena(request, token):
    res = Resena.objects.select_related("reserva").filter(token=token).first()
    if not res:
        return render(request, "sitio/resena.html", {"estado": "invalida"}, status=404)
    estado = _estado_resena(res)
    r = res.reserva
    publico = f"{r.nombre.split()[0]} {r.apellido[:1]}." if r.apellido else r.nombre
    if estado == "ok" and request.method == "POST":
        try:
            nota = int(request.POST.get("calificacion", ""))
        except ValueError:
            nota = 0
        if not 1 <= nota <= 5:
            return render(request, "sitio/resena.html", {"estado": "ok", "res": res, "publico": request.POST.get("nombre_publico", publico),
                                                         "error": True, "comentario": request.POST.get("comentario", "")})
        Resena.objects.filter(pk=res.pk, fecha_resena__isnull=True).update(
            calificacion=nota, comentario=request.POST.get("comentario", "").strip()[:1000],
            nombre_publico=(request.POST.get("nombre_publico", "").strip() or publico)[:100], fecha_resena=timezone.now(), visible=False)
        res.refresh_from_db()
        correos.aviso_resena(correos.url_base(request), res)
        return render(request, "sitio/resena.html", {"estado": "gracias"})
    return render(request, "sitio/resena.html", {"estado": estado, "res": res, "publico": publico})


def csrf_fallo(request, reason=""):
    """Token CSRF vencido (p. ej. se inició sesión en el panel desde otra pestaña): vuelve al formulario con un aviso."""
    log.warning("Fallo CSRF en %s: %s", request.path, reason)
    if request.path.startswith(("/panel/", "/admin/")):
        from django.views.csrf import csrf_failure
        return csrf_failure(request, reason=reason)
    messages.error(request, L("La página del formulario había expirado. Inténtalo de nuevo.",
                              "The form page had expired. Please try again.",
                              "A página do formulário havia expirado. Tente novamente."))
    destino = request.META.get("HTTP_REFERER", "")
    if not (destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()})):
        destino = reverse("inicio")
    return redirect(destino)
