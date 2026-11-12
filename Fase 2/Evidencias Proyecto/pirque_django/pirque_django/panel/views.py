import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Max, Min, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from sitio import correos
from . import servicios
from .models import ESTADOS_PAGO, ESTADOS_RESERVA, Cliente, Mensaje, Reserva, Resena

ESTADOS_R = [e for e, _ in ESTADOS_RESERVA]
ESTADOS_P = [e for e, _ in ESTADOS_PAGO]
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
panel = login_required(login_url="panel:login")


def limpiar(v): return re.sub(r"[.\-\s]", "", v or "").upper()
def err(m): return JsonResponse({"ok": False, "error": m}, status=400)
def aceptadas(): return Reserva.objects.filter(estado_reserva="aceptada")   # son las que OCUPAN las fechas
def solape(r, a, b): return max(0, (min(r.fecha_salida, b) - max(r.fecha_entrada, a)).days)
def sig_mes(a, m): return date(a + (m == 12), m % 12 + 1, 1)
def pagina(request, qs, n=10):
    g = request.GET.copy(); g.pop("page", None)
    return Paginator(qs, n).get_page(request.GET.get("page")), g.urlencode()
def clp(n): return f"${n:,}".replace(",", ".")
def fd(x): return x.strftime("%d/%m/%Y")


def ocupacion_meses(anio):
    rs = list(aceptadas().filter(fecha_entrada__lt=date(anio + 1, 1, 1), fecha_salida__gt=date(anio, 1, 1)))
    return [sum(solape(r, date(anio, m, 1), sig_mes(anio, m)) for r in rs) for m in range(1, 13)]


def ocupacion_anios():
    rs = list(aceptadas())
    if not rs: return {timezone.localdate().year: 0}
    return {y: sum(solape(r, date(y, 1, 1), date(y + 1, 1, 1)) for r in rs)
            for y in range(min(r.fecha_entrada for r in rs).year, max(r.fecha_salida for r in rs).year + 1)}


# ---------- Sesión ----------
def login_view(request):
    if request.user.is_authenticated: return redirect("panel:inicio")
    error = ""
    if request.method == "POST":
        u = authenticate(request, username=request.POST.get("usuario", "").strip(), password=request.POST.get("password", ""))
        if u: login(request, u); return redirect("panel:inicio")
        error = "Usuario o contraseña incorrectos."
    return render(request, "panel/login.html", {"error": error})


def logout_view(request):
    logout(request); return redirect("panel:login")


# ---------- Avisos de fechas repetidas ----------
def conflictos():
    """Reservas SIN aceptar cuyas fechas se cruzan con otra solicitud o con una reserva ya aceptada.
    Devuelve (alertas, notas): alertas para mostrar arriba y notas {id_reserva: texto} para marcar cada fila."""
    hoy = timezone.localdate()
    pend = list(Reserva.objects.filter(estado_reserva="pendiente", fecha_salida__gt=hoy).order_by("fecha_entrada", "id"))
    acept = list(aceptadas().filter(fecha_salida__gt=hoy))
    cruza = lambda a, b: a.fecha_entrada < b.fecha_salida and b.fecha_entrada < a.fecha_salida
    vecinos = {a.id: [b for b in pend if b.id != a.id and cruza(a, b)] for a in pend}
    alertas, notas, vistos = [], defaultdict(list), set()
    for a in pend:                                   # solicitudes que piden las mismas fechas entre sí
        if a.id in vistos or not vecinos[a.id]: continue
        grupo, cola = [], [a]
        while cola:
            x = cola.pop()
            if x.id in vistos: continue
            vistos.add(x.id); grupo.append(x); cola.extend(vecinos[x.id])
        grupo.sort(key=lambda r: (r.fecha_entrada, r.id))
        alertas.append({"tipo": "pendientes", "reservas": grupo})
        for x in grupo: notas[x.id].append("Se cruza con " + ", ".join(f"#{y.id}" for y in vecinos[x.id]))
    for a in pend:                                   # solicitudes que chocan con una reserva ya aceptada
        for c in acept:
            if cruza(a, c):
                alertas.append({"tipo": "aceptada", "reserva": a, "aceptada": c})
                notas[a.id].append(f"Choca con la reserva ACEPTADA #{c.id}")
    return alertas, {k: " · ".join(v) for k, v in notas.items()}


# ---------- Dashboard ----------
def _ingresos_periodo(d, h):
    """Dinero de las reservas NO canceladas cuya fecha de entrada cae en [d, h)."""
    pagado = cobrar = n_pag = n_cobrar = 0
    for r in Reserva.objects.filter(fecha_entrada__gte=d, fecha_entrada__lt=h).exclude(estado_reserva="cancelada"):
        if r.estado_pago == "pagado": pagado += r.monto; n_pag += 1
        elif r.estado_pago in ("pendiente", "abonado"): cobrar += r.monto; n_cobrar += 1
    return dict(pagado=pagado, cobrar=cobrar, n_pag=n_pag, n_cobrar=n_cobrar)


def _tarjeta_ingresos(d, h, d0, h0, etiqueta, comparado_con):
    act, ant = _ingresos_periodo(d, h), _ingresos_periodo(d0, h0)
    var = round((act["pagado"] - ant["pagado"]) * 100 / ant["pagado"]) if ant["pagado"] else None
    return dict(etiqueta=etiqueta, comparado_con=comparado_con, pagado=clp(act["pagado"]), cobrar=clp(act["cobrar"]),
                n_pag=act["n_pag"], n_cobrar=act["n_cobrar"], var=var, abs_var=abs(var) if var is not None else None)


@panel
def inicio(request):
    hoy = timezone.localdate()
    servicios.revisar_resenas_en_segundo_plano(correos.url_base(request))   # invitaciones de reseña (máx. cada 6 h)
    act = aceptadas().filter(fecha_entrada__lte=hoy, fecha_salida__gt=hoy).first()
    mes_ant = date(hoy.year - (hoy.month == 1), (hoy.month - 2) % 12 + 1, 1)
    ingresos = {
        "mes": _tarjeta_ingresos(hoy.replace(day=1), sig_mes(hoy.year, hoy.month), mes_ant, hoy.replace(day=1),
                                 f"{MESES_LARGOS[hoy.month - 1]} {hoy.year}", "el mes anterior"),
        "anio": _tarjeta_ingresos(date(hoy.year, 1, 1), date(hoy.year + 1, 1, 1), date(hoy.year - 1, 1, 1), date(hoy.year, 1, 1),
                                  f"el año {hoy.year}", "el año anterior")}
    prox = Reserva.objects.filter(fecha_entrada__gte=hoy).exclude(estado_reserva="cancelada").order_by("fecha_entrada")
    ev = []
    r = Reserva.objects.order_by("-fecha_reserva").first()
    if r: ev.append((r.fecha_reserva, "Reserva más reciente", f"#{r.id} · {r.nombre} {r.apellido} ({r.estado_reserva})", "bi-calendar-check"))
    for m in Mensaje.objects.filter(fecha_gestion__isnull=False).order_by("-fecha_gestion")[:2]:
        ev.append((m.fecha_gestion, f"Mensaje {m.codigo} gestionado", f"por {m.admin_nombre}", "bi-envelope-check"))
    for x in Resena.objects.filter(fecha_resena__isnull=False).select_related("reserva").order_by("-fecha_resena")[:2]:
        ev.append((x.fecha_resena, f"Nueva reseña ({x.calificacion}/5)", x.nombre_publico or x.reserva.nombre, "bi-star"))
    ev.sort(key=lambda x: x[0], reverse=True)
    tareas = {"reservas": Reserva.objects.filter(estado_reserva="pendiente").count(),
              "nuevas": Reserva.objects.filter(estado_reserva="pendiente", vista=False).count(),
              "mensajes": Mensaje.objects.filter(fecha_gestion__isnull=True).count()}
    return render(request, "panel/inicio.html", {
        "act": act, "ingresos": ingresos, "n_clientes": Cliente.objects.count(), "n_prox": prox.count(), "prox": prox[:5], "eventos": ev[:6],
        "tareas": tareas, "anios": range(hoy.year - 3, hoy.year + 1), "anio_actual": hoy.year})


@panel
def api_ocupacion(request):
    if request.GET.get("modo") == "anios":
        d = ocupacion_anios()
        return JsonResponse({"labels": [str(y) for y in d], "data": list(d.values()), "max": None})  # eje Y responsivo
    a = int(request.GET.get("anio") or timezone.localdate().year)
    return JsonResponse({"labels": MESES, "data": ocupacion_meses(a), "max": 50})


# ---------- Mensajes ----------
@panel
def api_pendientes(request):
    """Contadores de las burbujas del menú lateral (se actualizan solos)."""
    return JsonResponse({"pendientes": Mensaje.objects.filter(fecha_gestion__isnull=True).count(),
                         "reservas": Reserva.objects.filter(estado_reserva="pendiente").count()})


@panel
def mensajes(request):
    qs = Mensaje.objects.order_by("-fecha_envio")
    q, est = request.GET.get("q", "").strip(), request.GET.get("estado", "")
    if q: qs = qs.filter(Q(nombre__icontains=q) | Q(correo__icontains=q) | Q(id__in=[int(q[-6:])] if q[-6:].isdigit() else []))
    if est == "pendiente": qs = qs.filter(fecha_gestion__isnull=True)
    if est == "gestionado": qs = qs.filter(fecha_gestion__isnull=False)
    page, qstr = pagina(request, qs)
    return render(request, "panel/mensajes.html", {"page": page, "qs": qstr, "q": q, "est": est, "total": qs.count()})


@panel
@require_POST
def mensaje_toggle(request, pk):
    m = get_object_or_404(Mensaje, pk=pk)
    if m.fecha_gestion: m.fecha_gestion, m.admin_id = None, None
    else: m.fecha_gestion, m.admin_id = timezone.now(), request.user.id  # admin = usuario logueado
    m.save()
    return JsonResponse({"ok": True})


# ---------- Reservas ----------
SECCIONES = {"todas": "Todas las reservas", "pendientes": "Reservas pendientes", "aceptadas": "Reservas aceptadas",
             "terminadas": "Reservas terminadas", "canceladas": "Reservas canceladas"}


# Opciones de orden de la lista de reservas (valen igual en TODAS las secciones)
ORDENES = {"entrada_desc": "Entrada: más lejanas primero", "entrada_asc": "Entrada: más cercanas primero",
           "creada_desc": "Creadas: más recientes primero", "creada_asc": "Creadas: más antiguas primero"}
ORDEN_POR_DEFECTO = {"todas": "entrada_desc", "pendientes": "entrada_asc", "aceptadas": "entrada_asc",
                     "terminadas": "entrada_desc", "canceladas": "entrada_desc"}


def ordenar_reservas(lista, orden, hoy):
    """Ordena la lista según la opción elegida (con desempate por número de reserva, para que el orden sea siempre el mismo).
    «Entrada: más cercanas primero» pone primero lo que viene (o está en curso), de la fecha más próxima a la más lejana,
    y al final lo que ya pasó, empezando por lo más reciente."""
    if orden == "entrada_asc":
        return sorted(lista, key=lambda r: (0, r.fecha_entrada.toordinal(), r.id) if r.fecha_salida >= hoy else (1, -r.fecha_entrada.toordinal(), -r.id))
    if orden == "creada_asc":
        return sorted(lista, key=lambda r: (r.fecha_reserva, r.id))
    if orden == "creada_desc":
        return sorted(lista, key=lambda r: (r.fecha_reserva, r.id), reverse=True)
    return sorted(lista, key=lambda r: (r.fecha_entrada, r.id), reverse=True)     # entrada_desc


@panel
def reservas(request, seccion="todas"):
    hoy = timezone.localdate()
    base = Reserva.objects.select_related("cliente")
    conteos = {"pendientes": base.filter(estado_reserva="pendiente").count(),
               "aceptadas": base.filter(estado_reserva="aceptada", fecha_salida__gte=hoy).count(),
               "terminadas": base.filter(estado_reserva="aceptada", fecha_salida__lt=hoy).count(),
               "canceladas": base.filter(estado_reserva="cancelada").count()}
    conteos["todas"] = sum(conteos.values())
    qs = {"todas": base,
          "pendientes": base.filter(estado_reserva="pendiente"),
          "aceptadas": base.filter(estado_reserva="aceptada", fecha_salida__gte=hoy),
          "terminadas": base.filter(estado_reserva="aceptada", fecha_salida__lt=hoy),
          "canceladas": base.filter(estado_reserva="cancelada")}[seccion]
    q, pago, f = request.GET.get("q", "").strip(), request.GET.get("pago", ""), request.GET.get("fecha", "")
    orden = request.GET.get("orden", "")
    if orden == "recientes": orden = "creada_desc"                    # enlaces antiguos
    if orden not in ORDENES: orden = ORDEN_POR_DEFECTO[seccion]       # sin elegir: el orden normal de cada sección
    if q:
        c = Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(cliente__id__icontains=limpiar(q))
        if q.lstrip("#").isdigit(): c |= Q(id=int(q.lstrip("#")))
        qs = qs.filter(c)
    if pago in ESTADOS_P: qs = qs.filter(estado_pago=pago)
    if f == "mes": qs = qs.filter(fecha_entrada__gte=hoy.replace(day=1), fecha_entrada__lt=sig_mes(hoy.year, hoy.month))
    todas = ordenar_reservas(list(qs), orden, hoy)
    page, qstr = pagina(request, todas)
    lista = list(page)
    res = {x.reserva_id: x for x in Resena.objects.filter(reserva__in=[r.id for r in lista])}
    alertas, notas = conflictos()
    for r in lista:
        r.res = res.get(r.id)
        r.choque = notas.get(r.id, "")
    return render(request, "panel/reservas.html", {
        "page": page, "lista": lista, "qs": qstr, "q": q, "pago": pago, "f": f, "seccion": seccion, "titulo": SECCIONES[seccion], "orden": orden,
        "ordenes": ORDENES, "alertas": alertas, "secciones": SECCIONES, "conteos": conteos, "estados_reserva": ESTADOS_RESERVA,
        "estados_pago": ESTADOS_PAGO, "total": len(todas)})


@panel
def api_ocupadas(request):
    """Fechas ocupadas (reservas ACEPTADAS) para mostrarlas en rojo en el calendario de las modales del panel.
    `excluir` = id de la reserva que se está editando (para no marcar sus propias fechas)."""
    qs = aceptadas().filter(fecha_salida__gte=timezone.localdate() - timedelta(days=365))
    if request.GET.get("excluir", "").isdigit(): qs = qs.exclude(pk=int(request.GET["excluir"]))
    return JsonResponse({"ocupadas": [{"from": r.fecha_entrada.isoformat(), "to": (r.fecha_salida - timedelta(days=1)).isoformat(),
                                       "quien": f"#{r.id} {r.nombre} {r.apellido}"} for r in qs]})


def _leer_reserva(d, excluir=None):
    """Valida y normaliza el formulario de reserva del panel. Devuelve (datos, mensaje_de_error)."""
    try:
        e, s = date.fromisoformat(d["fecha_entrada"]), date.fromisoformat(d["fecha_salida"])
        adultos, ninos, monto = int(d.get("cant_adultos") or 1), int(d.get("cant_ninos") or 0), int(d.get("monto") or 0)
    except (KeyError, ValueError):
        return None, "Revisa las fechas y los números (adultos, niños y valor)."
    if s <= e: return None, "La fecha de salida debe ser posterior a la de entrada."
    if adultos < 1 or ninos < 0 or monto < 0: return None, "Revisa adultos, niños y valor de la estadía."
    doc, nombre, apellido = limpiar(d.get("documento")), d.get("nombre", "").strip(), d.get("apellido", "").strip()
    correo, tel = d.get("correo", "").strip(), d.get("telefono", "").strip()
    if not (doc and nombre and apellido and correo and tel): return None, "Completa nombre, apellido, RUT/DNI, correo y teléfono."
    if "@" not in correo: return None, "El correo no es válido."
    if d.get("estado_reserva") not in ESTADOS_R or d.get("estado_pago") not in ESTADOS_P: return None, "Estado inválido."
    if d["estado_reserva"] == "aceptada" and aceptadas().filter(fecha_entrada__lt=s, fecha_salida__gt=e).exclude(pk=excluir).exists():
        return None, "Ya hay otra reserva ACEPTADA en esas fechas (el servicio es exclusivo para un grupo a la vez)."
    return dict(doc=doc, nombre=nombre, apellido=apellido, correo=correo, tel=tel, entrada=e, salida=s, adultos=adultos, ninos=ninos, monto=monto,
                estado_reserva=d["estado_reserva"], estado_pago=d["estado_pago"], notas=d.get("notas", "").strip()[:500],
                nac="Extranjero" if d.get("nacionalidad") == "Extranjero" else "Chileno"), None


def _guardar_cliente(x):
    Cliente.objects.update_or_create(id=x["doc"], defaults=dict(nombre=x["nombre"], apellido=x["apellido"], telefono=x["tel"],
                                                                correo=x["correo"], nacionalidad=x["nac"]))


def _avisar_aceptacion(request, r):
    ok = correos.reserva_aceptada(correos.url_base(request), r)
    return f"Reserva aceptada. Correo de confirmación enviado a {r.correo}." if ok else \
           "Reserva aceptada, pero NO se pudo enviar el correo (revisa la configuración de correo)."


@panel
@require_POST
def reserva_crear(request):
    x, error = _leer_reserva(request.POST)
    if error: return err(error)
    with transaction.atomic():
        _guardar_cliente(x)
        r = Reserva.objects.create(cliente_id=x["doc"], nombre=x["nombre"], apellido=x["apellido"], correo=x["correo"], telefono=x["tel"],
                                   cant_adultos=x["adultos"], cant_ninos=x["ninos"], fecha_entrada=x["entrada"], fecha_salida=x["salida"],
                                   monto=x["monto"], estado_reserva=x["estado_reserva"], estado_pago=x["estado_pago"], notas=x["notas"],
                                   idioma="es", vista=True, fecha_reserva=timezone.now())
    aviso = _avisar_aceptacion(request, r) if x["estado_reserva"] == "aceptada" and request.POST.get("enviar_correo") == "1" else ""
    return JsonResponse({"ok": True, "aviso": aviso})


@panel
@require_POST
def reserva_editar(request, pk):
    r = get_object_or_404(Reserva, pk=pk)
    x, error = _leer_reserva(request.POST, excluir=r.pk)
    if error: return err(error)
    previo = r.estado_reserva
    with transaction.atomic():
        _guardar_cliente(x)
        Reserva.objects.filter(pk=pk).update(cliente_id=x["doc"], nombre=x["nombre"], apellido=x["apellido"], correo=x["correo"], telefono=x["tel"],
                                             cant_adultos=x["adultos"], cant_ninos=x["ninos"], fecha_entrada=x["entrada"], fecha_salida=x["salida"],
                                             monto=x["monto"], estado_reserva=x["estado_reserva"], estado_pago=x["estado_pago"], notas=x["notas"], vista=True)
    aviso = ""
    if x["estado_reserva"] == "aceptada" and previo != "aceptada" and request.POST.get("enviar_correo") == "1":
        aviso = _avisar_aceptacion(request, Reserva.objects.get(pk=pk))
    return JsonResponse({"ok": True, "aviso": aviso})


@panel
@require_POST
def reserva_aceptar(request, pk):
    """Acción rápida de la lista de pendientes: acepta la reserva y avisa por correo al cliente."""
    r = get_object_or_404(Reserva, pk=pk)
    if aceptadas().filter(fecha_entrada__lt=r.fecha_salida, fecha_salida__gt=r.fecha_entrada).exclude(pk=r.pk).exists():
        return err("Ya hay otra reserva ACEPTADA en esas fechas (el servicio es exclusivo para un grupo a la vez).")
    Reserva.objects.filter(pk=pk).update(estado_reserva="aceptada", vista=True)
    return JsonResponse({"ok": True, "aviso": _avisar_aceptacion(request, Reserva.objects.get(pk=pk))})


@panel
@require_POST
def reserva_vista(request, pk):
    """La administradora abrió/revisó la reserva: deja de destacarse como «Nueva»."""
    Reserva.objects.filter(pk=pk).update(vista=True)
    return JsonResponse({"ok": True})


@panel
@require_POST
def reserva_eliminar(request, pk):
    get_object_or_404(Reserva, pk=pk).delete()   # la reseña asociada se elimina en cascada
    return JsonResponse({"ok": True})


@panel
@require_POST
def reserva_resena(request, pk):
    """Envía (o reenvía) al huésped la invitación a dejar su reseña."""
    ok, msg = servicios.enviar_invitacion(correos.url_base(request), get_object_or_404(Reserva, pk=pk))
    return JsonResponse({"ok": True, "aviso": msg}) if ok else err(msg)


# ---------- Clientes ----------
@panel
def clientes(request):
    qs, q = Cliente.objects.order_by("nombre", "apellido"), request.GET.get("q", "").strip()
    if q: qs = qs.filter(Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(id__icontains=limpiar(q)) | Q(correo__icontains=q))
    page, qstr = pagina(request, qs)
    return render(request, "panel/clientes.html", {"page": page, "qs": qstr, "q": q, "total": qs.count()})


@panel
@require_POST
def cliente_editar(request, pk):
    c, d = get_object_or_404(Cliente, pk=pk), request.POST
    nuevo = limpiar(d.get("documento"))
    if not nuevo or d.get("nacionalidad") not in ("Chileno", "Extranjero"): return err("Datos inválidos.")
    if nuevo != pk and Cliente.objects.filter(pk=nuevo).exists(): return err("Ya existe un cliente con ese RUT/DNI.")
    Cliente.objects.filter(pk=pk).update(id=nuevo, nombre=d["nombre"].strip(), apellido=d["apellido"].strip(),
        correo=d["correo"].strip(), telefono=d["telefono"].strip(), nacionalidad=d["nacionalidad"])  # FK con ON UPDATE CASCADE
    return JsonResponse({"ok": True})


@panel
@require_POST
def cliente_eliminar(request, pk):
    if Reserva.objects.filter(cliente_id=pk).exists(): return err("No se puede eliminar: el cliente tiene reservas.")
    get_object_or_404(Cliente, pk=pk).delete()
    return JsonResponse({"ok": True})


# ---------- Reseñas ----------
@panel
def resenas(request):
    qs = Resena.objects.select_related("reserva").order_by(F("fecha_resena").desc(nulls_last=True), "-id")
    est = request.GET.get("estado", "")
    if est == "respondidas": qs = qs.filter(fecha_resena__isnull=False)
    if est == "sin_responder": qs = qs.filter(fecha_resena__isnull=True)
    if est == "visibles": qs = qs.filter(visible=True)
    if est == "ocultas": qs = qs.filter(fecha_resena__isnull=False, visible=False)
    page, qstr = pagina(request, qs)
    return render(request, "panel/resenas.html", {
        "page": page, "qs": qstr, "est": est, "total": qs.count(),
        "n_visibles": Resena.objects.filter(visible=True).count(), "n_sin_responder": Resena.objects.filter(fecha_resena__isnull=True).count(),
        "n_por_enviar": Reserva.objects.filter(estado_reserva="aceptada", fecha_salida__lt=timezone.localdate(), resena__isnull=True).count()})


@panel
@require_POST
def resena_visible(request, pk):
    x = get_object_or_404(Resena, pk=pk)
    if not x.respondida: return err("Esta reseña aún no fue respondida.")
    Resena.objects.filter(pk=pk).update(visible=not x.visible)
    return JsonResponse({"ok": True})


@panel
@require_POST
def resena_eliminar(request, pk):
    get_object_or_404(Resena, pk=pk).delete()
    return JsonResponse({"ok": True})


@panel
@require_POST
def resenas_enviar(request):
    enviados, fallidos = servicios.solicitar_resenas(correos.url_base(request))
    return JsonResponse({"ok": True, "aviso": f"Invitaciones enviadas: {enviados}" + (f" · con error: {fallidos}" if fallidos else "")})


# ---------- Reportes ----------
TIPOS = {"ocupacion": "Reporte de ocupación", "reservas": "Reporte de reservas",
         "ingresos": "Reporte de ingresos", "clientes": "Reporte de clientes y huéspedes"}


AYUDA_TIPOS = {"ocupacion": "Cuántos días estuvo ocupado el alojamiento y cuándo hay fechas libres.",
               "reservas": "La lista de reservas y en qué estado están (pendientes, aceptadas, terminadas, canceladas).",
               "ingresos": "Cuánto dinero se ha pagado, cuánto falta por cobrar y qué reservas aún no están pagadas.",
               "clientes": "Quiénes han reservado, de qué nacionalidad y cuántas veces."}


def _entero(v, minimo, maximo):
    try: n = int(v)
    except (TypeError, ValueError): return 0
    return n if minimo <= n <= maximo else 0


def rango(g):
    """Período del reporte: (desde, hasta_exclusivo, etiqueta, seleccion).
    Sin año ni mes elegidos se muestran TODOS los registros. «Últimos 3 meses» (p=trimestre) es un atajo aparte."""
    hoy = timezone.localdate()
    if g.get("p") == "trimestre":
        y, mm = (hoy.year, hoy.month - 2) if hoy.month > 2 else (hoy.year - 1, hoy.month + 10)
        return date(y, mm, 1), sig_mes(hoy.year, hoy.month), "Últimos 3 meses", {"p": "trimestre", "anio": 0, "mes": 0}
    a, m = _entero(g.get("anio"), 1900, 2100), _entero(g.get("mes"), 1, 12)
    if m and not a: a = hoy.year            # mes elegido sin año: se usa el año actual (y así se ve en el selector)
    sel = {"p": "", "anio": a, "mes": m}
    if a and m: return date(a, m, 1), sig_mes(a, m), f"{MESES_LARGOS[m - 1].capitalize()} de {a}", sel
    if a: return date(a, 1, 1), date(a + 1, 1, 1), f"Todo el año {a}", sel
    ext = Reserva.objects.aggregate(a=Min("fecha_entrada"), b=Max("fecha_salida"))
    d = ext["a"] or hoy
    return d, max(ext["b"] or hoy, d + timedelta(days=1)), "Todos los registros", sel


def _por_entrada(d, h):
    """Reservas cuya fecha de ENTRADA cae en el período."""
    return list(Reserva.objects.filter(fecha_entrada__gte=d, fecha_entrada__lt=h).select_related("cliente").order_by("fecha_entrada", "id"))


def _huesped(r): return f"{r.nombre} {r.apellido}"


def datos_reporte(tipo, d, h):
    """Cada reporte devuelve: resumen [(titulo, valor, explicación)], tablas [{titulo, cols, filas, vacio}] y una nota."""
    hoy = timezone.localdate()
    if tipo == "ocupacion":
        total = (h - d).days
        ocup = sum(solape(r, d, h) for r in aceptadas().filter(fecha_entrada__lt=h, fecha_salida__gt=d))
        cur, filas = hoy, []
        for r in aceptadas().filter(fecha_salida__gt=hoy).order_by("fecha_entrada"):
            if r.fecha_entrada > cur: filas.append([fd(cur), fd(r.fecha_entrada), (r.fecha_entrada - cur).days])
            cur = max(cur, r.fecha_salida)
        filas.append([fd(cur), "(sin reservas posteriores)", "—"])
        return dict(nota="Cuenta las noches con una reserva ACEPTADA dentro del período.",
            resumen=[("Días ocupados", ocup, "Noches en que hubo un grupo hospedado."),
                     ("Días libres", total - ocup, "Noches sin ninguna reserva aceptada."),
                     ("Porcentaje de ocupación", f"{ocup * 100 / total:.1f}%", f"Días ocupados sobre los {total} días del período.")],
            tablas=[dict(titulo="Próximos períodos libres (sin reservas aceptadas)", cols=["Libre desde", "Libre hasta", "Días"], filas=filas, vacio="")])
    rs = _por_entrada(d, h)
    nota = "Se consideran las reservas cuya fecha de entrada cae en el período. Las reservas canceladas no suman dinero."
    if tipo == "reservas":
        c = Counter(r.seccion for r in rs)
        return dict(nota=nota.split(".")[0] + ".",
            resumen=[("Pendientes", c.get("pendiente", 0), "Solicitudes que aún no aceptas."), ("Aceptadas", c.get("aceptada", 0), "Estadías confirmadas que todavía no terminan."),
                     ("Terminadas", c.get("terminada", 0), "Estadías aceptadas cuya salida ya pasó."), ("Canceladas", c.get("cancelada", 0), "Reservas canceladas."),
                     ("Total de reservas", len(rs), "Todas las del período.")],
            tablas=[dict(titulo="Detalle de las reservas", cols=["ID", "Huésped", "RUT/DNI", "Entrada", "Salida", "Personas", "Noches", "Reserva", "Pago"],
                         filas=[[f"#{r.id}", _huesped(r), r.cliente_id, fd(r.fecha_entrada), fd(r.fecha_salida), r.personas, r.noches,
                                 r.estado_reserva.capitalize(), r.estado_pago.capitalize()] for r in rs], vacio="No hay reservas en este período.")])
    if tipo == "ingresos":
        vig = [r for r in rs if r.estado_reserva != "cancelada"]
        pagadas = [r for r in vig if r.estado_pago == "pagado"]
        por_cobrar = [r for r in vig if r.estado_pago in ("pendiente", "abonado")]
        sin_valor = [r for r in vig if not r.monto]
        suma = lambda lista: sum(r.monto for r in lista)
        por_mes = Counter()
        for r in pagadas: por_mes[(r.fecha_entrada.year, r.fecha_entrada.month)] += r.monto
        meses_n = Counter((r.fecha_entrada.year, r.fecha_entrada.month) for r in pagadas)
        tablas = [
            dict(titulo="Reservas que aún NO están pagadas por completo (pago pendiente o con abono)",
                 cols=["ID", "Huésped", "Entrada", "Salida", "Valor", "Estado del pago", "Estado de la reserva"],
                 filas=[[f"#{r.id}", _huesped(r), fd(r.fecha_entrada), fd(r.fecha_salida), clp(r.monto) if r.monto else "sin definir",
                         r.estado_pago.capitalize(), r.estado_reserva.capitalize()] for r in por_cobrar],
                 vacio="¡Todo está pagado! No hay reservas pendientes de pago en este período."),
            dict(titulo="Resumen por estado de pago", cols=["Estado del pago", "Reservas", "Valor total"],
                 filas=[[e.capitalize(), sum(1 for r in vig if r.estado_pago == e), clp(suma([r for r in vig if r.estado_pago == e]))] for e in ("pagado", "abonado", "pendiente")], vacio=""),
            dict(titulo="Total pagado por mes (según la fecha de entrada)", cols=["Mes", "Reservas pagadas", "Total pagado"],
                 filas=[[f"{MESES_LARGOS[m - 1].capitalize()} {a}", meses_n[(a, m)], clp(t)] for (a, m), t in sorted(por_mes.items())], vacio="Aún no hay reservas pagadas en este período.")]
        if sin_valor:
            tablas.append(dict(titulo="Reservas a las que falta escribir el valor de la estadía", cols=["ID", "Huésped", "Entrada", "Salida", "Estado de la reserva", "Estado del pago"],
                               filas=[[f"#{r.id}", _huesped(r), fd(r.fecha_entrada), fd(r.fecha_salida), r.estado_reserva.capitalize(), r.estado_pago.capitalize()] for r in sin_valor], vacio=""))
        return dict(nota=nota,
            resumen=[("Total pagado", clp(suma(pagadas)), "Suma del valor de las reservas marcadas como «Pagado»."),
                     ("Falta por cobrar", clp(suma(por_cobrar)), f"Valor de {len(por_cobrar)} reserva(s) con pago «Pendiente» o «Abonado» (no se descuenta lo abonado)."),
                     ("Reservas pagadas", len(pagadas), "Cantidad de reservas con el pago completo."),
                     ("Reservas sin valor definido", len(sin_valor), "Reservas a las que todavía no les escribes el valor de la estadía; por eso no suman en los montos.")],
            tablas=tablas)
    por = Counter(r.cliente_id for r in rs); cl = {r.cliente_id: r.cliente for r in rs}
    nac = Counter(c.nacionalidad for c in cl.values())
    return dict(nota="Se consideran los clientes con reservas cuya fecha de entrada cae en el período.",
        resumen=[("Clientes con reservas", len(cl), "Personas distintas que reservaron."), ("Chilenos", nac.get("Chileno", 0), ""), ("Extranjeros", nac.get("Extranjero", 0), ""),
                 ("Clientes registrados (total)", Cliente.objects.count(), "Todos los clientes guardados, hayan reservado o no en este período.")],
        tablas=[dict(titulo="Clientes del período", cols=["RUT/DNI", "Nombre", "Nacionalidad", "Correo", "Teléfono", "Reservas"],
                     filas=[[k, _huesped(c), c.nacionalidad, c.correo, c.telefono, por[k]] for k, c in sorted(cl.items(), key=lambda kc: (kc[1].nombre.lower(), kc[1].apellido.lower()))], vacio="No hay clientes en este período.")])


@panel
def reportes(request):
    hoy = timezone.localdate()
    tipo = request.GET.get("tipo", "")
    d, h, etiqueta, sel = rango(request.GET)
    if sel["p"] == "trimestre": activo = "trimestre"
    elif sel["anio"] == hoy.year and sel["mes"] == hoy.month: activo = "mes"
    elif sel["anio"] == hoy.year and not sel["mes"]: activo = "anio"
    elif not sel["anio"] and not sel["mes"]: activo = "todos"
    else: activo = ""
    filtro = "&".join(f"{k}={v}" for k, v in (("p", sel["p"]), ("anio", sel["anio"]), ("mes", sel["mes"])) if v)
    primero = Reserva.objects.aggregate(a=Min("fecha_entrada"))["a"]
    ctx = {"tipos": TIPOS, "tipo": tipo, "sel": sel, "activo": activo, "etiqueta": etiqueta, "filtro": filtro,
           "desde": d, "hasta": h - timedelta(days=1), "meses": enumerate(MESES_LARGOS, 1), "hoy": hoy,
           "anios": range(min(primero.year if primero else hoy.year, hoy.year), hoy.year + 2)}
    ctx["lista_tipos"] = [(k, TIPOS[k], AYUDA_TIPOS[k]) for k in TIPOS]
    if tipo in TIPOS: ctx.update(titulo=TIPOS[tipo], **datos_reporte(tipo, d, h))
    return render(request, "panel/reportes.html", ctx)


@panel
def reporte_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    tipo = request.GET.get("tipo")
    if tipo not in TIPOS: return HttpResponse("Reporte inválido", status=400)
    d, h, etiqueta, _ = rango(request.GET); r = datos_reporte(tipo, d, h); st = getSampleStyleSheet()
    resp = HttpResponse(content_type="application/pdf"); resp["Content-Disposition"] = f'attachment; filename="{tipo}.pdf"'
    def tabla(filas, cab=True):
        t = Table(filas, repeatRows=1 if cab else 0)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .4, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)] +
                              ([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3d2c")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)] if cab else [])))
        return t
    doc = [Paragraph(f"Hospedaje Rural Pirque — {TIPOS[tipo]}", st["Title"]),
           Paragraph(f"Período: {etiqueta} ({fd(d)} a {fd(h - timedelta(days=1))})", st["Normal"]), Paragraph(r["nota"], st["Italic"]), Spacer(1, 10),
           tabla([[k, str(v)] for k, v, _ in r["resumen"]], cab=False)]
    for t in r["tablas"]:
        doc += [Spacer(1, 12), Paragraph(t["titulo"], st["Heading3"])]
        doc.append(tabla([t["cols"]] + [[str(c) for c in f] for f in t["filas"]]) if t["filas"] else Paragraph(t["vacio"] or "Sin datos.", st["Normal"]))
    SimpleDocTemplate(resp, pagesize=landscape(A4)).build(doc)
    return resp


@panel
def ayuda(request):
    return render(request, "panel/ayuda.html")


@panel
def configuracion(request):
    return render(request, "panel/configuracion.html")
