"""Ayudas comunes para todas las pruebas (funciones, seguridad, compatibilidad y rendimiento)."""
import secrets
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from panel.models import Cliente, Resena, Reserva
from sitio.datos import CLAVES, datos_sitio

H = timezone.localdate()
RUT = "123456785"
CORREO = "juan@correo.com"
CLAVE = "Clave-Segura-123"


def d(n):
    return H + timedelta(days=n)


def texto_wa(url):
    """Texto (ya decodificado) de un enlace de WhatsApp."""
    return parse_qs(urlparse(url).query)["text"][0]


def f(fecha):
    return fecha.strftime("%d/%m/%Y")


class Base(TestCase):
    def setUp(self):
        self.notas = []
        self.obtenido = ""
        cache.clear()   # los intentos fallidos de ingreso al panel se cuentan en la caché: cada prueba parte de cero
        # El inicio del panel lanza un hilo que envía invitaciones de reseña; en pruebas se desactiva.
        p = mock.patch("panel.servicios.revisar_resenas_en_segundo_plano")
        p.start()
        self.addCleanup(p.stop)
        self.admin = get_user_model().objects.create_user("admin", "admin@pirque.cl", CLAVE, is_staff=True)
        self.adm = Client()
        self.adm.force_login(self.admin)

    # ---------- registro del resultado ----------
    def obt(self, texto):
        """Texto que se copiará en «Resultado obtenido» si la prueba se aprueba."""
        self.obtenido = texto

    def nota(self, texto):
        self.notas.append(texto)

    def manual(self, motivo):
        self.skipTest(f"Requiere prueba manual: {motivo}")

    # ---------- datos ----------
    def cliente(self, doc=RUT, nombre="Juan", apellido="Pérez", correo=CORREO, nac="Chileno"):
        return Cliente.objects.update_or_create(id=doc, defaults=dict(nombre=nombre, apellido=apellido, correo=correo,
                                                                      telefono="56912345678", nacionalidad=nac))[0]

    def reserva(self, e, s, estado="pendiente", pago="pendiente", monto=0, doc=RUT, nombre="Juan", apellido="Pérez",
                correo=CORREO, **kw):
        self.cliente(doc, nombre, apellido, correo)
        return Reserva.objects.create(cliente_id=doc, nombre=nombre, apellido=apellido, correo=correo, telefono="56912345678",
                                      fecha_entrada=e, fecha_salida=s, estado_reserva=estado, estado_pago=pago, monto=monto, **kw)

    def resena(self, res=None, respondida=False, visible=False, dias_solicitud=1, comentario="Excelente"):
        res = res or self.reserva(d(-10), d(-3), estado="aceptada")
        x = Resena.objects.create(reserva=res, token=secrets.token_urlsafe(32),
                                  fecha_solicitud=timezone.now() - timedelta(days=dias_solicitud))
        if respondida:
            Resena.objects.filter(pk=x.pk).update(calificacion=5, comentario=comentario, nombre_publico="Juan P.",
                                                  fecha_resena=timezone.now(), visible=visible)
            x.refresh_from_db()
        return x

    def muchas_reservas(self, n=500, inicio=None):
        """Carga n clientes y n reservas aceptadas sin fechas cruzadas (para pruebas de volumen)."""
        inicio = inicio or d(-3 * n)
        Cliente.objects.bulk_create([Cliente(id=f"9{i:08d}", nombre=f"Cliente{i}", apellido="Prueba", correo=f"c{i}@correo.com",
                                             telefono="56912345678", nacionalidad="Chileno") for i in range(n)])
        Reserva.objects.bulk_create([Reserva(cliente_id=f"9{i:08d}", nombre=f"Cliente{i}", apellido="Prueba", correo=f"c{i}@correo.com",
                                             telefono="56912345678", fecha_entrada=inicio + timedelta(days=3 * i),
                                             fecha_salida=inicio + timedelta(days=3 * i + 2), estado_reserva="aceptada",
                                             estado_pago="pagado" if i % 2 else "pendiente", monto=100000, vista=True)
                                     for i in range(n)])

    def contacto_panel(self, **cambios):
        """Formulario de Configuraciones avanzadas: los datos actuales con los cambios indicados."""
        actuales = datos_sitio()
        return {**{c: actuales[c] for c in CLAVES}, **cambios}

    def guardar_contacto(self, c=None, **cambios):
        return (c or self.adm).post(reverse("panel:configuracion_guardar"), self.contacto_panel(**cambios))

    # ---------- acciones ----------
    def ingresar(self, c=None, rut=RUT, correo=CORREO, extranjero=False, **extra):
        c = c or self.client
        datos = {"nombre": "Juan", "apellido": "Pérez", "correo": correo, "rut": rut, "telefono": "56912345678",
                 "acepto_privacidad": "on", **extra}
        if extranjero:
            datos["extranjero"] = "on"
        return c.post(reverse("login_cliente"), datos)

    def solicitar(self, e, s, adultos=2, ninos=0, c=None):
        return (c or self.client).post(reverse("reservar"), {"llegada": e.isoformat(), "salida": s.isoformat(),
                                                             "adultos": adultos, "ninos": ninos})

    def errores(self, resp):
        frm = resp.context["form"]
        return (" ".join(str(x) for x in frm.non_field_errors()) + " " +
                " ".join(f"{k}: {' '.join(v)}" for k, v in frm.errors.items() if k != "__all__")).strip()

    def admin2(self, usuario="ana", nombre="Ana", apellido="Soto"):
        """Segundo administrador con su propia sesión (para ver quién hizo cada cambio)."""
        u = get_user_model().objects.create_user(usuario, f"{usuario}@pirque.cl", CLAVE, is_staff=True, first_name=nombre, last_name=apellido)
        c = Client()
        c.force_login(u)
        return u, c

    def editar(self, r, c=None, **cambios):
        """Guarda la ventana «Ver / Editar» de la reserva r con los cambios indicados. Devuelve la respuesta JSON."""
        return (c or self.adm).post(reverse("panel:reserva_editar", args=[r.id]), self.form_panel(r, **cambios)).json()

    def form_panel(self, r=None, **cambios):
        datos = dict(nombre="Juan", apellido="Pérez", documento=RUT, nacionalidad="Chileno", telefono="56912345678",
                     correo=CORREO, fecha_entrada=d(10).isoformat(), fecha_salida=d(12).isoformat(), cant_adultos=2,
                     cant_ninos=0, monto=0, estado_reserva="pendiente", estado_pago="pendiente", notas="")
        if r:
            datos.update(nombre=r.nombre, apellido=r.apellido, documento=r.cliente_id, correo=r.correo, telefono=r.telefono,
                         fecha_entrada=r.fecha_entrada.isoformat(), fecha_salida=r.fecha_salida.isoformat(),
                         cant_adultos=r.cant_adultos, cant_ninos=r.cant_ninos or 0, monto=r.monto,
                         estado_reserva=r.estado_reserva, estado_pago=r.estado_pago, notas=r.notas)
        datos.update(cambios)
        return datos

    def ocupadas_sitio(self):
        return self.client.get(reverse("api_disponibilidad")).json()["ocupadas"]

    def idioma(self, c, codigo):
        c.cookies[settings.LANGUAGE_COOKIE_NAME] = codigo
