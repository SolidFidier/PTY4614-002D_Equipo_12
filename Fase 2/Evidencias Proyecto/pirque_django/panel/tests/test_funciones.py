"""Pruebas funcionales (P1 a P97) de la hoja «Pruebas» del Plan de pruebas.

Cada método test_PNN_... corresponde a la fila PNN y, al aprobarse, registra el resultado concreto que obtuvo.
"""
import re
from datetime import date, timedelta
from io import StringIO
from unittest import mock

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core import mail
from django.core.management import call_command
from django.db import DatabaseError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from panel import views as pv
from panel.models import Cliente, Configuracion, Mensaje, Resena, Reserva
from sitio import datos as datos_mod, whatsapp
from sitio.datos import datos_sitio
from sitio.forms import ReservaForm

from .base import CLAVE, CORREO, RUT, Base, H, d, f, texto_wa


# =====================================================================  H1
class H1Reserva(Base):
    def test_P01_solicitud_fechas_disponibles(self):
        self.ingresar()
        r = self.solicitar(d(6), d(8))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("https://api.whatsapp.com/send/"), "No redirige a WhatsApp")
        res = Reserva.objects.get()
        self.assertEqual(res.estado_reserva, "pendiente")
        self.assertTrue(Cliente.objects.filter(id=RUT).exists(), "No se creó el cliente")
        avisos = [m for m in mail.outbox if "Nueva solicitud" in m.subject]
        self.assertTrue(avisos, "No se envió el aviso a los administradores")
        self.obt(f"Se creó el cliente {RUT} y la reserva #{res.id} ({f(d(6))} al {f(d(8))}, 2 adultos) en estado «Pendiente»; "
                 f"se envió el aviso «{avisos[0].subject}» a {', '.join(avisos[0].to)} y se redirigió a api.whatsapp.com.")

    def test_P02_solicitud_fechas_ocupadas(self):
        self.reserva(d(6), d(8), estado="aceptada", doc="111111111")
        self.ingresar()
        self.assertTrue(any(o["from"] == d(6).isoformat() for o in self.ocupadas_sitio()), "El calendario no recibe las fechas ocupadas")
        r = self.solicitar(d(7), d(9))
        self.assertEqual(r.status_code, 200)
        err = self.errores(r)
        self.assertIn("ya están ocupadas", err)
        self.assertEqual(Reserva.objects.count(), 1, "Se creó una reserva en fechas ocupadas")
        self.obt(f"El calendario recibió el rango ocupado {f(d(6))}–{f(d(7))}. Al enviar {f(d(7))}–{f(d(9))} el formulario mostró: "
                 f"«{err}» y no se creó la reserva (sigue habiendo 1).")

    def test_P03_llegada_pasada(self):
        self.ingresar()
        err = self.errores(self.solicitar(d(-1), d(2)))
        self.assertIn("La fecha de llegada no puede ser pasada", err)
        self.assertFalse(Reserva.objects.exists())
        self.obt(f"Con llegada {f(d(-1))} el formulario mostró: «{err}». No se registró ninguna reserva.")

    def test_P04_salida_igual_a_llegada(self):
        self.ingresar()
        err = self.errores(self.solicitar(d(6), d(6)))
        self.assertIn("La fecha de salida debe ser posterior a la de llegada", err)
        self.assertFalse(Reserva.objects.exists())
        self.obt(f"Con llegada y salida {f(d(6))} el formulario mostró: «{err}». No se registró la reserva.")

    def test_P05_identificacion_incompleta(self):
        r = self.ingresar(nombre="", telefono="")
        self.assertEqual(r.status_code, 200)
        frm = r.context["form"]
        self.assertIn("Campo obligatorio", str(frm.errors.get("nombre")))
        self.assertIn("telefono", frm.errors)
        self.assertNotIn("huesped", self.client.session)
        self.obt(f"El formulario marcó «{frm.errors['nombre'][0]}» en Nombre y «{frm.errors['telefono'][0]}» en Teléfono; "
                 "no se inició la sesión del cliente.")

    def test_P06_rut_formato_invalido(self):
        r = self.ingresar(rut="12AB")
        self.assertEqual(r.status_code, 200)
        msg = r.context["form"].errors.get("rut")
        self.assertIn("8 o 9 caracteres", str(msg))
        self.obt(f"Con RUT «12AB» el formulario mostró: «{msg[0]}» y no permitió continuar.")

    def test_P07_rut_digito_verificador_incorrecto(self):
        r = self.ingresar(rut="123456780")
        self.assertEqual(r.status_code, 302, "El RUT con dígito verificador incorrecto fue rechazado")
        doc = self.client.session["huesped"]["documento"]
        self.assertEqual(doc, "123456780")
        self.obt(f"El RUT 123456780 (dígito verificador incorrecto) fue aceptado: se inició la sesión con documento {doc}.")

    def test_P08_cliente_extranjero(self):
        r = self.ingresar(rut="AB123456", extranjero=True)
        self.assertEqual(r.status_code, 302, "No se aceptó el documento extranjero")
        self.solicitar(d(6), d(8))
        nac = Cliente.objects.get(id="AB123456").nacionalidad
        self.assertEqual(nac, "Extranjero")
        self.obt(f"Se aceptó el documento AB123456 y el cliente quedó registrado con nacionalidad «{nac}».")

    def test_P09_solicitud_repetida(self):
        self.ingresar()
        self.solicitar(d(6), d(8), adultos=2)
        n_correos = len(mail.outbox)
        self.solicitar(d(6), d(8), adultos=3)
        res = Reserva.objects.get()
        self.assertEqual(Reserva.objects.count(), 1, "Se duplicó la solicitud")
        self.assertEqual(res.cant_adultos, 3, "No se actualizaron los datos")
        self.assertEqual(len(mail.outbox), n_correos, "Se volvió a avisar a los administradores")
        self.obt(f"Hay 1 sola reserva (#{res.id}); sus adultos cambiaron de 2 a {res.cant_adultos} y no se envió un segundo aviso.")

    def test_P10_mensaje_whatsapp_solicitud(self):
        self.ingresar()
        t = texto_wa(self.solicitar(d(6), d(8))["Location"])
        r = Reserva.objects.get()
        esperados = ("Juan Pérez", f(d(6)), f(d(8)), "2 noches", "2 adultos", CORREO, f"Solicitud N° {r.id}")
        for esperado in esperados:
            self.assertIn(esperado, t, f"Falta «{esperado}» en el mensaje")
        self.assertNotIn(RUT, t, "El mensaje muestra el RUT")
        self.obt(f"El mensaje de WhatsApp incluye: {', '.join(esperados)}. El RUT {RUT} no aparece.")

    def test_P11_reservar_sin_identificarse(self):
        r = self.client.get(reverse("reservar"))
        self.assertEqual(r.status_code, 302)
        destino = r["Location"]
        self.assertIn(reverse("login_cliente"), destino)
        self.assertIn("next=", destino)
        r = self.client.post(f"{reverse('login_cliente')}?next={reverse('reservar')}",
                             {"nombre": "Juan", "apellido": "Pérez", "correo": CORREO, "rut": RUT, "telefono": "56912345678"})
        self.assertEqual(r["Location"], reverse("reservar"))
        self.obt(f"Sin sesión, /reservar/ redirigió a {destino}; al identificarse volvió a {r['Location']}.")


# =====================================================================  H2
class H2MisReservas(Base):
    def test_P12_consultar_mis_reservas(self):
        self.reserva(d(6), d(8))
        self.reserva(d(-10), d(-8), estado="aceptada")
        self.reserva(d(20), d(22), estado="cancelada")
        self.ingresar()
        lista = self.client.get(reverse("mis_reservas")).context["reservas"]
        self.assertEqual(len(lista), 3)
        etiquetas = {r.etiqueta for r in lista}
        self.assertEqual(etiquetas, {"Pendiente de confirmación", "Finalizada", "Cancelada"})
        self.obt(f"«Mis Reservas» mostró {len(lista)} reservas con los estados: " +
                 "; ".join(f"#{r.id} {r.etiqueta}" for r in lista) + ".")

    def test_P13_privacidad_de_reservas(self):
        self.reserva(d(6), d(8), correo="a@correo.com")
        self.ingresar(correo="otro@correo.com")
        n = len(self.client.get(reverse("mis_reservas")).context["reservas"])
        self.assertEqual(n, 0, "Se muestran reservas con un correo distinto")
        self.obt(f"Con RUT {RUT} y correo otro@correo.com, «Mis Reservas» mostró {n} reservas (la reserva es de a@correo.com).")

    def test_P14_solicitar_cancelacion_whatsapp(self):
        res = self.reserva(d(6), d(8), estado="aceptada")
        self.ingresar()
        r = self.client.get(reverse("mis_reservas")).context["reservas"][0]
        self.assertTrue(r.puede_cancelar)
        t = texto_wa(r.wa_cancelar)
        self.assertIn(f"Reserva N° {res.id}", t)
        self.assertIn(f(d(6)), t)
        self.assertNotIn(RUT, t)
        self.obt(f"La reserva #{res.id} muestra el botón de cancelar; el mensaje de WhatsApp incluye «Reserva N° {res.id}» "
                 f"y la llegada {f(d(6))}, sin el RUT.")

    def test_P15_reserva_finalizada_o_cancelada(self):
        self.reserva(d(-10), d(-8), estado="aceptada")
        self.reserva(d(20), d(22), estado="cancelada")
        self.ingresar()
        lista = self.client.get(reverse("mis_reservas")).context["reservas"]
        for r in lista:
            self.assertFalse(r.puede_cancelar, f"La reserva #{r.id} muestra el botón de cancelar")
            self.assertEqual(r.wa_cancelar, "")
        self.obt("Ninguna de las reservas (" + ", ".join(f"#{r.id} {r.etiqueta}" for r in lista) + ") muestra el botón de cancelación.")

    def test_P16_registrar_cancelacion_panel(self):
        res = self.reserva(d(6), d(8), estado="aceptada")
        r = self.adm.post(reverse("panel:reserva_editar", args=[res.id]), self.form_panel(res, estado_reserva="cancelada"))
        self.assertTrue(r.json()["ok"], r.content)
        self.assertEqual(Reserva.objects.get(pk=res.id).estado_reserva, "cancelada")
        self.assertIn(res.id, [x.id for x in self.adm.get(reverse("panel:reservas_canceladas")).context["lista"]])
        ocup = self.ocupadas_sitio()
        self.assertEqual(ocup, [], "Las fechas no quedaron libres")
        self.ingresar()
        etq = self.client.get(reverse("mis_reservas")).context["reservas"][0].etiqueta
        self.assertEqual(etq, "Cancelada")
        self.obt(f"La reserva #{res.id} quedó en estado «cancelada», aparece en la sección Canceladas, el calendario no tiene "
                 f"fechas ocupadas ({ocup}) y el cliente la ve como «{etq}».")


# =====================================================================  H3
class H3Disponibilidad(Base):
    def test_P17_mostrar_fechas_ocupadas(self):
        self.reserva(d(6), d(8), estado="aceptada")
        ocup = self.ocupadas_sitio()
        self.assertEqual(ocup, [{"from": d(6).isoformat(), "to": d(7).isoformat()}])
        self.ingresar()
        html = self.client.get(reverse("reservar")).content.decode()
        self.assertIn("dia-ocupado", html)
        self.assertIn("disable:", html)
        self.obt(f"La API de disponibilidad devolvió {ocup} y el calendario las deshabilita y marca con la clase «dia-ocupado».")
        self.nota("El color rojo se debe confirmar visualmente en el navegador.")

    def test_P18_pendientes_no_ocupan(self):
        res = self.reserva(d(6), d(8), estado="pendiente")
        ocup = self.ocupadas_sitio()
        self.assertEqual(ocup, [])
        self.obt(f"Con la reserva #{res.id} pendiente ({f(d(6))}–{f(d(8))}), la API de disponibilidad devolvió {ocup}: las fechas siguen libres.")

    def test_P19_rango_con_fechas_ocupadas(self):
        self.reserva(d(6), d(8), estado="aceptada", doc="111111111")
        self.ingresar()
        self.assertIn("Ese rango incluye fechas ocupadas", self.client.get(reverse("reservar")).content.decode())
        err = self.errores(self.solicitar(d(4), d(11)))
        self.assertIn("ya están ocupadas", err)
        self.obt(f"Al enviar {f(d(4))}–{f(d(11))} (incluye la reserva aceptada) el servidor respondió: «{err}».")
        self.nota("El aviso inmediato del calendario se debe confirmar en el navegador.")

    def test_P20_disponibilidad_al_aceptar(self):
        res = self.reserva(d(6), d(8))
        antes = self.ocupadas_sitio()
        self.assertEqual(antes, [])
        self.adm.post(reverse("panel:reserva_aceptar", args=[res.id]))
        despues = self.ocupadas_sitio()
        self.assertEqual(len(despues), 1, "Las fechas no se marcan como ocupadas tras aceptar")
        self.obt(f"Antes de aceptar la reserva #{res.id} la API devolvía {antes}; después devolvió {despues}.")

    def test_P21_disponibilidad_al_cancelar(self):
        res = self.reserva(d(6), d(8), estado="aceptada")
        antes = self.ocupadas_sitio()
        self.adm.post(reverse("panel:reserva_editar", args=[res.id]), self.form_panel(res, estado_reserva="cancelada"))
        despues = self.ocupadas_sitio()
        self.assertEqual(despues, [])
        self.obt(f"Antes de cancelar la reserva #{res.id} la API devolvía {antes}; después devolvió {despues} (fechas libres).")

    def test_P22_calendario_del_panel(self):
        propia = self.reserva(d(6), d(8), estado="aceptada")
        otra = self.reserva(d(20), d(22), estado="aceptada", doc="111111111", nombre="Ana", apellido="Rojas")
        datos = self.adm.get(reverse("panel:api_ocupadas") + f"?excluir={propia.id}").json()["ocupadas"]
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["quien"], f"#{otra.id} Ana Rojas")
        self.obt(f"Al editar la reserva #{propia.id}, el calendario del panel mostró solo la otra reserva: "
                 f"«{datos[0]['quien']}» ({datos[0]['from']} a {datos[0]['to']}).")


# =====================================================================  H4
class H4Idiomas(Base):
    def test_P23_cambiar_idioma(self):
        r = self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        self.assertEqual(r.status_code, 302)
        html = self.client.get(reverse("servicios")).content.decode()
        for t in ('lang="en"', "Opening Hours", "Services"):
            self.assertIn(t, html)
        self.obt("Tras elegir English, la página de servicios se mostró con lang=\"en\", el menú «Services» y el título «Opening Hours».")

    def test_P24_mantener_idioma(self):
        self.client.post(reverse("set_language"), {"language": "pt", "next": "/"})
        paginas = ("servicios", "contacto", "login_cliente", "inicio")
        for nombre in paginas:
            self.assertIn('lang="pt"', self.client.get(reverse(nombre)).content.decode(), f"Se perdió el idioma en {nombre}")
        self.obt(f"Las páginas {', '.join(paginas)} se mostraron todas con lang=\"pt\" (cookie {settings.LANGUAGE_COOKIE_NAME}).")

    def test_P25_validaciones_traducidas(self):
        self.idioma(self.client, "en")
        self.ingresar()
        err = self.errores(self.solicitar(d(-1), d(2)))
        self.assertIn("The check-in date cannot be in the past.", err)
        self.obt(f"Con el sitio en inglés el error fue: «{err}».")

    def test_P26_whatsapp_y_correos_en_idioma(self):
        self.idioma(self.client, "pt")
        self.ingresar()
        t = texto_wa(self.solicitar(d(6), d(8))["Location"])
        res = Reserva.objects.get()
        self.assertEqual(res.idioma, "pt")
        self.assertTrue(t.startswith("Olá"), "El mensaje de WhatsApp no está en portugués")
        mail.outbox.clear()
        self.adm.post(reverse("panel:reserva_aceptar", args=[res.id]))
        al_cliente = [m for m in mail.outbox if CORREO in m.to]
        self.assertTrue(al_cliente and "Sua reserva foi confirmada" in al_cliente[0].body, "El correo al cliente no está en portugués")
        self.obt(f"La reserva #{res.id} quedó con idioma «{res.idioma}»; el WhatsApp empieza con «{t.splitlines()[0]}» y el correo "
                 f"de confirmación dice «Sua reserva foi confirmada!» (asunto: «{al_cliente[0].subject}»).")

    def test_P27_panel_en_espanol(self):
        self.idioma(self.adm, "en")
        html = self.adm.get(reverse("panel:inicio")).content.decode()
        self.assertIn("Qué necesita tu atención hoy", html)
        self.assertIn('lang="es"', html)
        self.obt("Con la cookie de idioma en inglés, el panel se mostró en español (lang=\"es\", título «Qué necesita tu atención hoy»).")


# =====================================================================  H5
class H5Resenas(Base):
    def test_P28_envio_invitacion(self):
        res = self.reserva(d(-10), d(-3), estado="aceptada")
        salida = StringIO()
        call_command("enviar_resenas", stdout=salida)
        x = Resena.objects.get(reserva=res)
        self.assertIsNotNone(x.fecha_solicitud)
        m = [m for m in mail.outbox if CORREO in m.to]
        self.assertTrue(m and f"/resena/{x.token}/" in m[0].body, "No llegó el correo con el enlace personal")
        texto = re.sub(r"\x1b\[[0-9;]*m", "", salida.getvalue()).strip()
        self.obt(f"El comando respondió «{texto}». Se envió a {CORREO} el correo «{m[0].subject}» "
                 f"con el enlace /resena/{x.token[:8]}…/ de la reserva #{res.id}.")

    def test_P29_publicar_resena_valida(self):
        x = self.resena()
        r = self.client.post(reverse("resena", args=[x.token]), {"calificacion": "5", "comentario": "Muy lindo", "nombre_publico": "Juan P."})
        self.assertEqual(r.context["estado"], "gracias")
        x.refresh_from_db()
        self.assertEqual((x.calificacion, x.visible), (5, False))
        avisos = [m for m in mail.outbox if "Nueva reseña" in m.subject]
        self.assertTrue(avisos, "No se avisó a los administradores")
        self.obt(f"Se mostró la página de agradecimiento; la reseña quedó con calificación {x.calificacion}, comentario "
                 f"«{x.comentario}», oculta (visible={x.visible}) y se envió el aviso «{avisos[0].subject}».")

    def test_P30_resena_sin_calificacion(self):
        x = self.resena()
        r = self.client.post(reverse("resena", args=[x.token]), {"comentario": "Sin nota"})
        self.assertTrue(r.context.get("error"))
        self.assertEqual(r.context.get("comentario"), "Sin nota")
        x.refresh_from_db()
        self.assertIsNone(x.fecha_resena)
        self.obt("El formulario mostró el error de calificación faltante, conservó el comentario «Sin nota» y la reseña no se guardó.")

    def test_P31_enlace_ya_utilizado(self):
        x = self.resena(respondida=True)
        estado = self.client.get(reverse("resena", args=[x.token])).context["estado"]
        self.assertEqual(estado, "ya")
        self.client.post(reverse("resena", args=[x.token]), {"calificacion": "1", "comentario": "otra"})
        x.refresh_from_db()
        self.assertEqual(x.calificacion, 5, "Se sobrescribió la reseña")
        self.obt(f"El enlace mostró la página de «reseña ya enviada» (estado «{estado}») y, al reenviar, la calificación siguió en {x.calificacion}.")

    def test_P32_enlace_vencido_o_invalido(self):
        x = self.resena(dias_solicitud=61)
        e1 = self.client.get(reverse("resena", args=[x.token])).context["estado"]
        self.assertEqual(e1, "vencida")
        r = self.client.get(reverse("resena", args=["token-que-no-existe"]))
        self.assertEqual((r.status_code, r.context["estado"]), (404, "invalida"))
        self.obt(f"El enlace solicitado hace 61 días mostró «enlace vencido» (estado «{e1}»); un token inexistente respondió "
                 f"{r.status_code} con «enlace no válido».")

    def test_P33_mostrar_resena_en_inicio(self):
        x = self.resena(respondida=True)
        self.adm.post(reverse("panel:resena_visible", args=[x.id]))
        self.assertIn(x.id, [y.id for y in self.client.get(reverse("inicio")).context["resenas"]])
        for i in range(7):
            self.resena(self.reserva(d(-40 - i * 3), d(-38 - i * 3), estado="aceptada", doc=f"20000000{i}"), respondida=True, visible=True)
        n = len(self.client.get(reverse("inicio")).context["resenas"])
        self.assertEqual(n, 6, "El inicio no limita a 6 reseñas")
        self.obt(f"Al marcarla visible, la reseña #{x.id} apareció en el inicio. Con 8 reseñas visibles, el inicio mostró {n}.")

    def test_P34_ocultar_y_eliminar_resena(self):
        x = self.resena(respondida=True, visible=True)
        self.adm.post(reverse("panel:resena_visible", args=[x.id]))
        en_inicio = list(self.client.get(reverse("inicio")).context["resenas"])
        self.assertEqual(en_inicio, [])
        self.adm.post(reverse("panel:resena_eliminar", args=[x.id]))
        self.assertFalse(Resena.objects.filter(pk=x.id).exists())
        self.obt(f"Al ocultar la reseña #{x.id} el inicio mostró {len(en_inicio)} reseñas; al eliminarla ya no existe en la base de datos.")

    def test_P35_reenviar_invitacion(self):
        res = self.reserva(d(-10), d(-2), estado="aceptada")
        r = self.adm.post(reverse("panel:reserva_resena", args=[res.id])).json()
        self.assertTrue(r["ok"])
        self.assertIn("Invitación enviada a", r["aviso"])
        self.obt(f"El panel respondió: «{r['aviso']}».")


# =====================================================================  H6
class H6WhatsApp(Base):
    def test_P36_whatsapp_desde_el_sitio(self):
        enlace = f"wa.me/{datos_sitio()['whatsapp']}"
        self.assertIn(enlace, self.client.get(reverse("inicio")).content.decode())
        self.obt(f"El pie de página contiene el enlace https://{enlace}.")

    def test_P37_whatsapp_en_distintas_secciones(self):
        enlace = f"wa.me/{datos_sitio()['whatsapp']}"
        paginas = ("inicio", "servicios", "contacto", "quienes_somos", "como_llegar")
        for nombre in paginas:
            self.assertIn(enlace, self.client.get(reverse(nombre)).content.decode(), f"Falta en {nombre}")
        self.obt(f"Las páginas {', '.join(paginas)} tienen el mismo enlace https://{enlace}.")

    def test_P38_mensaje_prearmado_con_emojis(self):
        res = self.reserva(d(6), d(8))
        url = whatsapp.solicitud(res)
        self.assertTrue(url.startswith(f"https://api.whatsapp.com/send/?phone={datos_sitio()['whatsapp']}"))
        t = texto_wa(url)
        self.assertIn("📅 *Llegada:*", t)
        self.assertIn("🔖", t)
        self.obt(f"El enlace usa api.whatsapp.com con el número {datos_sitio()['whatsapp']} y el texto contiene «📅 *Llegada:* {f(d(6))}» "
                 f"y «🔖 Solicitud N° {res.id}» con los emojis correctos.")
        self.nota("Que el cliente pueda editar el mensaje lo hace la propia aplicación de WhatsApp.")

    def test_P39_whatsapp_movil_y_computador(self):
        self.manual("abrir el enlace desde un celular (app) y desde un computador (WhatsApp Web).")


# =====================================================================  H7
class H7Panel(Base):
    def test_P40_panel_sin_sesion(self):
        r = Client().get(reverse("panel:inicio"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("panel:login"), r["Location"])
        self.obt(f"/panel/ sin sesión respondió {r.status_code} y redirigió a {r['Location']}.")

    def test_P41_login_correo_o_usuario(self):
        for usuario in ("admin@pirque.cl", "admin"):
            r = Client().post(reverse("panel:login"), {"usuario": usuario, "password": CLAVE})
            self.assertEqual(r.status_code, 302, f"No pudo ingresar con «{usuario}»")
            self.assertEqual(r["Location"], reverse("panel:inicio"))
        self.obt("Con «admin@pirque.cl» y con «admin» (misma contraseña) se ingresó al panel (redirección a /panel/).")

    def test_P42_credenciales_incorrectas(self):
        r = Client().post(reverse("panel:login"), {"usuario": "admin", "password": "mala"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Usuario o contraseña incorrectos.")
        self.obt("Con una contraseña incorrecta se mostró «Usuario o contraseña incorrectos.» y no se ingresó al panel.")

    def test_P43_grafico_por_meses(self):
        y = H.year - 1
        self.reserva(date(y, 3, 10), date(y, 3, 13), estado="aceptada")
        self.reserva(date(y, 7, 1), date(y, 7, 5), estado="aceptada")
        j = self.adm.get(reverse("panel:api_ocupacion") + f"?anio={y}").json()
        self.assertEqual(len(j["labels"]), 12)
        self.assertEqual((j["data"][2], j["data"][6], sum(j["data"])), (3, 4, 7))
        self.obt(f"El gráfico de {y} mostró 12 meses: marzo = {j['data'][2]} noches, julio = {j['data'][6]} noches, total {sum(j['data'])}.")

    def test_P44_grafico_por_anios(self):
        y = H.year
        self.reserva(date(y - 1, 1, 10), date(y - 1, 1, 12), estado="aceptada")
        self.reserva(date(y, 2, 1), date(y, 2, 4), estado="aceptada")
        j = self.adm.get(reverse("panel:api_ocupacion") + "?modo=anios").json()
        self.assertEqual(j["labels"], [str(y - 1), str(y)])
        self.assertEqual(j["data"], [2, 3])
        self.obt("El gráfico por años mostró: " + ", ".join(f"{a} = {n} noches" for a, n in zip(j["labels"], j["data"])) + ".")
        self.nota("El bloqueo del selector de año se debe confirmar en el navegador.")

    def test_P45_indicadores_de_ingresos(self):
        ini = H.replace(day=1)
        self.reserva(ini, ini + timedelta(days=2), estado="aceptada", pago="pagado", monto=100000)
        self.reserva(ini, ini + timedelta(days=1), estado="pendiente", pago="pendiente", monto=50000, doc="111111111")
        mes = self.adm.get(reverse("panel:inicio")).context["ingresos"]["mes"]
        self.assertEqual((mes["pagado"], mes["cobrar"]), ("$100.000", "$50.000"))
        self.obt(f"La tarjeta del mes mostró pagado {mes['pagado']} y por cobrar {mes['cobrar']}.")

    def test_P46_que_necesita_tu_atencion(self):
        self.reserva(d(6), d(8), vista=False)
        self.reserva(d(20), d(22), vista=True, doc="111111111")
        Mensaje.objects.create(nombre="Ana", correo="ana@c.cl", contenido="Hola", fecha_envio=timezone.now())
        r = self.adm.get(reverse("panel:inicio"))
        t = r.context["tareas"]
        self.assertEqual(t, {"reservas": 2, "nuevas": 1, "mensajes": 1})
        self.assertContains(r, "Qué necesita tu atención hoy")
        self.obt(f"El cuadro mostró {t['reservas']} solicitudes pendientes ({t['nuevas']} nueva) y {t['mensajes']} mensaje sin gestionar.")


# =====================================================================  H8
class H8Historial(Base):
    def test_P47_historial_por_estado(self):
        p = self.reserva(d(6), d(8))
        a = self.reserva(d(20), d(22), estado="aceptada")
        t = self.reserva(d(-10), d(-8), estado="aceptada")
        c = self.reserva(d(30), d(32), estado="cancelada")
        conteos = self.adm.get(reverse("panel:reservas")).context["conteos"]
        self.assertEqual(conteos, {"pendientes": 1, "aceptadas": 1, "terminadas": 1, "canceladas": 1, "todas": 4})
        for nombre, obj in (("reservas_pendientes", p), ("reservas_aceptadas", a), ("reservas_terminadas", t), ("reservas_canceladas", c)):
            self.assertEqual([x.id for x in self.adm.get(reverse(f"panel:{nombre}")).context["lista"]], [obj.id], nombre)
        self.obt("Contadores: " + ", ".join(f"{k} = {v}" for k, v in conteos.items()) +
                 f". Cada sección mostró solo su reserva (#{p.id}, #{a.id}, #{t.id}, #{c.id}).")

    def test_P48_buscar_reserva(self):
        ana = self.reserva(d(6), d(8), doc="111111111", nombre="Ana", apellido="Rojas", correo="ana@correo.com")
        pedro = self.reserva(d(20), d(22), doc="222222222", nombre="Pedro", apellido="Soto", correo="pedro@correo.com")
        ids = lambda q: [x.id for x in self.adm.get(reverse("panel:reservas"), {"q": q}).context["lista"]]
        r1, r2, r3 = ids("Rojas"), ids("222222222"), ids(f"#{pedro.id}")
        self.assertEqual(r1, [ana.id])
        self.assertEqual(r2, [pedro.id])
        self.assertEqual(r3, [pedro.id])
        self.obt(f"«Rojas» → reserva {r1}; «222222222» → {r2}; «#{pedro.id}» → {r3}.")

    def test_P49_filtrar_pago_y_mes(self):
        ini = H.replace(day=1)
        sig = pv.sig_mes(H.year, H.month)
        ok = self.reserva(ini, ini + timedelta(days=1), pago="pagado")
        self.reserva(sig, sig + timedelta(days=1), pago="pagado", doc="111111111")
        self.reserva(ini, ini + timedelta(days=1), pago="pendiente", doc="222222222")
        lista = [x.id for x in self.adm.get(reverse("panel:reservas"), {"pago": "pagado", "fecha": "mes"}).context["lista"]]
        self.assertEqual(lista, [ok.id])
        self.obt(f"De 3 reservas, el filtro «Pagado» + «Este mes» mostró solo la #{ok.id} (pagada y con entrada {f(ini)}).")

    def test_P50_ordenar_lista(self):
        rs = [self.reserva(d(6 + i * 3), d(7 + i * 3), doc=f"30000000{i}") for i in range(3)]
        for i, r in enumerate(rs):
            Reserva.objects.filter(pk=r.pk).update(fecha_reserva=timezone.now() - timedelta(days=3 - i))
        lista = [x.id for x in self.adm.get(reverse("panel:reservas"), {"orden": "creada_desc"}).context["lista"]]
        self.assertEqual(lista, [r.id for r in reversed(rs)])
        self.obt(f"Con «Creadas: más recientes primero» el orden fue {lista} (de la más nueva a la más antigua).")

    def test_P51_buscar_y_editar_cliente(self):
        self.cliente(nombre="Juan")
        self.cliente("111111111", nombre="Ana", apellido="Rojas", correo="ana@correo.com")
        encontrados = [c.id for c in self.adm.get(reverse("panel:clientes"), {"q": "Juan"}).context["page"]]
        self.assertEqual(encontrados, [RUT])
        r = self.adm.post(reverse("panel:cliente_editar", args=[RUT]), {"documento": RUT, "nombre": "Juan", "apellido": "Pérez",
                                                                       "correo": CORREO, "telefono": "56999999999", "nacionalidad": "Chileno"})
        self.assertTrue(r.json()["ok"])
        tel = Cliente.objects.get(id=RUT).telefono
        self.assertEqual(tel, "56999999999")
        self.obt(f"La búsqueda «Juan» encontró {encontrados}; el teléfono cambió de 56912345678 a {tel}.")

    def test_P52_eliminar_cliente_con_reservas(self):
        self.reserva(d(6), d(8))
        r = self.adm.post(reverse("panel:cliente_eliminar", args=[RUT]))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "No se puede eliminar: el cliente tiene reservas.")
        self.assertTrue(Cliente.objects.filter(id=RUT).exists())
        self.obt(f"El panel respondió {r.status_code}: «{r.json()['error']}» y el cliente sigue registrado.")

    def test_P53_restringir_acceso_historial(self):
        destinos = []
        for nombre in ("panel:reservas", "panel:clientes"):
            r = Client().get(reverse(nombre))
            self.assertEqual(r.status_code, 302)
            self.assertIn(reverse("panel:login"), r["Location"])
            destinos.append(f"{reverse(nombre)} → {r['Location']}")
        self.obt("Sin sesión ambas páginas redirigieron al inicio de sesión: " + "; ".join(destinos) + ".")


# =====================================================================  H9
class H9Servicios(Base):
    def test_P54_visualizar_servicios(self):
        r = Client().get(reverse("servicios"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Baños de Luna")
        self.assertContains(r, "Baños de arena volcánica")
        self.obt(f"Sin iniciar sesión la página respondió {r.status_code} y mostró los servicios (p. ej. «Baños de Luna» y «Baños de arena volcánica»).")

    def test_P55_carrusel(self):
        r = self.client.get(reverse("servicios"))
        imgs = r.context["carrusel"]
        self.assertTrue(imgs, "No hay imágenes en el carrusel")
        self.assertTrue(all("carrusel" in i for i in imgs))
        self.assertEqual(imgs, sorted(imgs, key=lambda n: int("".join(ch for ch in n if ch.isdigit()) or 0)))
        self.assertContains(r, "carousel-item")
        self.obt(f"El carrusel cargó {len(imgs)} imágenes en orden: {', '.join(i.split('/')[-1] for i in imgs)}.")
        self.nota("El paso de una imagen a otra se debe confirmar en el navegador.")

    def test_P56_horario_de_atencion(self):
        h = self.client.get(reverse("servicios")).context["horario"]
        self.assertEqual(len(h), 7)
        hoy = [x for x in h if x["hoy"]]
        self.assertEqual(len(hoy), 1)
        self.assertTrue(h[0]["cerrado"], "El lunes no aparece como «Cerrado»")
        self.obt(f"El horario mostró 7 días; se destacó «{hoy[0]['dia']}» como hoy y " +
                 ", ".join(x["dia"] for x in h if x["cerrado"]) + " aparece como «Cerrado».")

    def test_P57_servicios_en_otro_idioma(self):
        self.idioma(self.client, "en")
        r = self.client.get(reverse("servicios"))
        self.assertContains(r, "Moon Baths")
        self.assertContains(r, "Opening Hours")
        self.obt("En inglés se mostraron «Moon Baths» (Baños de Luna) y «Opening Hours» (Horarios de Atención).")

    def test_P58_visualizacion_movil(self):
        self.assertContains(self.client.get(reverse("servicios")), 'name="viewport"')
        self.manual("la página tiene la etiqueta viewport y usa Bootstrap, pero se debe revisar en un celular o en el modo móvil del navegador.")


# =====================================================================  H10
class H10Pagos(Base):
    def test_P59_registrar_valor(self):
        res = self.reserva(d(6), d(8))
        self.assertTrue(self.adm.post(reverse("panel:reserva_editar", args=[res.id]), self.form_panel(res, monto=150000)).json()["ok"])
        monto = Reserva.objects.get(pk=res.id).monto
        self.assertEqual(monto, 150000)
        html = self.adm.get(reverse("panel:reservas")).content.decode()
        self.assertIn("$150000", html, "El valor se guardó, pero no aparece como $150000 en la lista de reservas")
        self.obt(f"El valor de la reserva #{res.id} se guardó como {monto} y la lista de reservas lo muestra como $150000.")

    def test_P60_cambiar_estado_pago(self):
        res = self.reserva(d(6), d(8), monto=100000)
        vistos = []
        for estado in ("abonado", "pagado"):
            self.adm.post(reverse("panel:reserva_editar", args=[res.id]), self.form_panel(res, estado_pago=estado))
            vistos.append(Reserva.objects.get(pk=res.id).estado_pago)
            self.assertEqual(vistos[-1], estado)
        self.obt(f"El estado de pago de la reserva #{res.id} cambió de «pendiente» a «{vistos[0]}» y luego a «{vistos[1]}».")

    def test_P61_valor_invalido(self):
        res = self.reserva(d(6), d(8))
        r1 = self.adm.post(reverse("panel:reserva_editar", args=[res.id]), self.form_panel(res, monto=-5000))
        self.assertEqual(r1.status_code, 400)
        self.assertIn("valor de la estadía", r1.json()["error"])
        r2 = self.adm.post(reverse("panel:reserva_editar", args=[res.id]), self.form_panel(res, monto="abc"))
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(Reserva.objects.get(pk=res.id).monto, 0)
        self.obt(f"Con -5000 el panel respondió «{r1.json()['error']}»; con «abc» respondió «{r2.json()['error']}». El valor siguió en 0.")

    def test_P62_pagos_en_ingresos(self):
        self.reserva(d(6), d(7), estado="aceptada", pago="pagado", monto=100000)
        self.reserva(d(10), d(11), pago="abonado", monto=30000, doc="111111111")
        self.reserva(d(14), d(15), pago="pendiente", monto=20000, doc="222222222")
        self.reserva(d(18), d(19), estado="cancelada", pago="pagado", monto=99999, doc="333333333")
        res = {t: v for t, v, _ in pv.datos_reporte("ingresos", d(-30), d(60))["resumen"]}
        self.assertEqual((res["Total pagado"], res["Falta por cobrar"]), ("$100.000", "$50.000"))
        self.obt(f"Con 4 reservas (pagada $100.000, abonada $30.000, pendiente $20.000 y cancelada $99.999) el reporte calculó "
                 f"Total pagado {res['Total pagado']} y Falta por cobrar {res['Falta por cobrar']}; la cancelada no sumó.")

    def test_P63_sitio_sin_precios_ni_pagos(self):
        campos = set(ReservaForm().fields)
        self.assertEqual(campos, {"llegada", "salida", "adultos", "ninos"})
        self.ingresar()
        paginas = ("servicios", "reservar", "inicio")
        for nombre in paginas:
            html = self.client.get(reverse(nombre)).content.decode().lower()
            self.assertNotIn("precio", html, f"Aparece «precio» en {nombre}")
            self.assertNotIn("pagar", html, f"Aparece «pagar» en {nombre}")
        self.obt(f"El formulario de reserva solo pide {', '.join(sorted(campos))}; en {', '.join(paginas)} no aparecen «precio» ni «pagar».")


# =====================================================================  H11
class H11Gestion(Base):
    def test_P64_solicitud_nueva_destacada(self):
        res = self.reserva(d(6), d(8), vista=False)
        self.assertContains(self.adm.get(reverse("panel:reservas_pendientes")), "etq-nueva")
        self.adm.post(reverse("panel:reserva_vista", args=[res.id]))
        self.assertNotContains(self.adm.get(reverse("panel:reservas_pendientes")), "etq-nueva")
        self.obt(f"La reserva #{res.id} se mostró con la etiqueta «Nueva»; al abrirla (vista={Reserva.objects.get(pk=res.id).vista}) la etiqueta desapareció.")

    def test_P65_aceptar_sin_conflicto(self):
        res = self.reserva(d(6), d(8))
        j = self.adm.post(reverse("panel:reserva_aceptar", args=[res.id])).json()
        self.assertTrue(j["ok"])
        self.assertIn("Correo de confirmación enviado", j["aviso"])
        estado = Reserva.objects.get(pk=res.id).estado_reserva
        self.assertEqual(estado, "aceptada")
        m = [m for m in mail.outbox if CORREO in m.to and "Reserva confirmada" in m.subject]
        self.assertTrue(m)
        self.obt(f"La reserva #{res.id} quedó «{estado}»; el panel avisó «{j['aviso']}» y el cliente recibió «{m[0].subject}».")

    def test_P66_aceptar_con_fechas_ocupadas(self):
        otra = self.reserva(d(6), d(9), estado="aceptada", doc="111111111")
        res = self.reserva(d(7), d(8))
        r = self.adm.post(reverse("panel:reserva_aceptar", args=[res.id]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ya hay otra reserva ACEPTADA", r.json()["error"])
        estado = Reserva.objects.get(pk=res.id).estado_reserva
        self.assertEqual(estado, "pendiente")
        self.obt(f"Al aceptar la #{res.id} (se cruza con la #{otra.id}) el panel respondió {r.status_code}: «{r.json()['error']}». "
                 f"La reserva siguió «{estado}».")

    def test_P67_aviso_fechas_repetidas(self):
        a = self.reserva(d(6), d(9))
        b = self.reserva(d(8), d(10), doc="111111111")
        r = self.adm.get(reverse("panel:reservas"))
        al = r.context["alertas"]
        self.assertTrue(any(x["tipo"] == "pendientes" and {y.id for y in x["reservas"]} == {a.id, b.id} for x in al))
        self.assertContains(r, "alerta-fechas")
        self.obt(f"Se mostró el recuadro amarillo «Atención: hay reservas sin aceptar con fechas repetidas» con las solicitudes #{a.id} y #{b.id}.")

    def test_P68_crear_reserva_manual(self):
        r = self.adm.post(reverse("panel:reserva_crear"), self.form_panel(documento="444444444", monto=80000))
        self.assertTrue(r.json()["ok"], r.content)
        res = Reserva.objects.get(cliente_id="444444444")
        self.assertEqual(res.monto, 80000)
        self.assertTrue(Cliente.objects.filter(id="444444444").exists())
        self.obt(f"Se creó la reserva #{res.id} del cliente 444444444 ({f(res.fecha_entrada)} al {f(res.fecha_salida)}, valor {res.monto}) "
                 "y el cliente quedó registrado.")

    def test_P69_reserva_manual_incompleta(self):
        r = self.adm.post(reverse("panel:reserva_crear"), self.form_panel(correo=""))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "Completa nombre, apellido, RUT/DNI, correo y teléfono.")
        self.assertFalse(Reserva.objects.exists())
        self.obt(f"Sin correo el panel respondió {r.status_code}: «{r.json()['error']}» y no se creó la reserva.")

    def test_P70_eliminar_reserva(self):
        res = self.reserva(d(-10), d(-3), estado="aceptada")
        Resena.objects.create(reserva=res, token="t" * 40)
        self.adm.post(reverse("panel:reserva_eliminar", args=[res.id]))
        self.assertFalse(Reserva.objects.filter(pk=res.id).exists())
        self.assertFalse(Resena.objects.exists(), "La reseña asociada no se eliminó")
        self.obt(f"Se eliminaron la reserva #{res.id} y su reseña asociada (quedan {Reserva.objects.count()} reservas y "
                 f"{Resena.objects.count()} reseñas).")

    def test_P71_actualizacion_automatica(self):
        self.reserva(d(6), d(8))
        n = self.adm.get(reverse("panel:api_pendientes")).json()["reservas"]
        self.assertEqual(n, 1)
        ruta = finders.find("panel/js/panel.js")
        self.assertTrue(ruta and "30000" in open(ruta, encoding="utf-8").read(), "No se encontró la actualización cada 30 s")
        self.obt(f"La consulta de contadores devolvió {n} reserva pendiente y panel.js la repite cada 30000 ms (30 s).")
        self.nota("El refresco en pantalla se debe confirmar en el navegador.")


# =====================================================================  H12
class H12Contacto(Base):
    def test_P72_enviar_mensaje(self):
        r = self.client.post(reverse("contacto"), {"nombre": "Ana Rojas", "correo": "ana@correo.com", "mensaje": "¿Tienen fechas en enero?"}, follow=True)
        self.assertContains(r, "Mensaje enviado. Te responderemos pronto.")
        msj = Mensaje.objects.get(correo="ana@correo.com")
        m = [m for m in mail.outbox if "Nuevo mensaje de contacto" in m.subject]
        self.assertTrue(m, "No se avisó a los administradores")
        self.assertEqual(m[0].reply_to, ["ana@correo.com"])
        self.obt(f"Se mostró «Mensaje enviado. Te responderemos pronto.»; se guardó el mensaje #{msj.id} y se envió «{m[0].subject}» "
                 f"a {', '.join(m[0].to)} con «responder a» ana@correo.com.")

    def test_P73_mensaje_invalido(self):
        errores = []
        for datos in ({"nombre": "Ana", "correo": "no-es-correo", "mensaje": "Hola"}, {"nombre": "Ana", "correo": "ana@c.cl", "mensaje": ""}):
            r = self.client.post(reverse("contacto"), datos)
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.context["form"].errors)
            errores.append(", ".join(r.context["form"].errors))
        self.assertFalse(Mensaje.objects.exists())
        self.obt(f"Con correo inválido se marcó el campo «{errores[0]}»; con mensaje vacío, «{errores[1]}». No se guardó ningún mensaje.")

    def test_P74_marcar_gestionado(self):
        m = Mensaje.objects.create(nombre="Ana", correo="ana@c.cl", contenido="Hola", fecha_envio=timezone.now())
        self.adm.post(reverse("panel:mensaje_toggle", args=[m.id]))
        m.refresh_from_db()
        self.assertIsNotNone(m.fecha_gestion)
        self.assertEqual(m.admin_id, self.admin.id)
        gestion = timezone.localtime(m.fecha_gestion).strftime("%d/%m/%Y %H:%M")
        self.adm.post(reverse("panel:mensaje_toggle", args=[m.id]))
        m.refresh_from_db()
        self.assertIsNone(m.fecha_gestion)
        self.obt(f"Al marcarlo, el mensaje #{m.id} registró la fecha {gestion} y el administrador «admin»; al volver a pendiente la fecha quedó vacía.")

    def test_P75_buscar_y_filtrar_mensajes(self):
        a = Mensaje.objects.create(nombre="Ana", correo="ana@c.cl", contenido="Hola", fecha_envio=timezone.now())
        Mensaje.objects.create(nombre="Ana", correo="ana2@c.cl", contenido="Hola", fecha_envio=timezone.now(), fecha_gestion=timezone.now())
        Mensaje.objects.create(nombre="Pedro", correo="p@c.cl", contenido="Hola", fecha_envio=timezone.now())
        ids = [m.id for m in self.adm.get(reverse("panel:mensajes"), {"q": "Ana", "estado": "pendiente"}).context["page"]]
        self.assertEqual(ids, [a.id])
        self.obt(f"De 3 mensajes, la búsqueda «Ana» con filtro «Pendiente» mostró solo el #{a.id}.")


# =====================================================================  H13
class H13Reportes(Base):
    def ctx(self, **g):
        return self.adm.get(reverse("panel:reportes"), g).context

    def test_P76_reporte_sin_filtros(self):
        for i, y in enumerate((H.year - 2, H.year - 1, H.year)):
            self.reserva(date(y, 3, 1), date(y, 3, 3), doc=f"50000000{i}")
        c = self.ctx(tipo="reservas")
        self.assertEqual(c["etiqueta"], "Todos los registros")
        n = len(c["tablas"][0]["filas"])
        self.assertEqual(n, 3)
        self.obt(f"Sin filtros el reporte indicó «{c['etiqueta']}» y listó las {n} reservas de {H.year - 2}, {H.year - 1} y {H.year}.")

    def test_P77_atajos_de_periodo(self):
        este = self.reserva(H.replace(day=1), H.replace(day=1) + timedelta(days=1))
        self.reserva(H - timedelta(days=400), H - timedelta(days=398), doc="111111111")
        vistos = []
        for g in ({"p": "trimestre"}, {"anio": H.year, "mes": H.month}, {"anio": H.year}):
            c = self.ctx(tipo="reservas", **g)
            ids = [fila[0] for fila in c["tablas"][0]["filas"]]
            self.assertEqual(ids, [f"#{este.id}"], f"Filtro {g}")
            vistos.append(f"«{c['etiqueta']}» → {ids}")
        self.assertTrue(vistos[0].startswith("«Últimos 3 meses»"))
        self.obt("Cada atajo mostró solo la reserva del período (la de hace 400 días quedó fuera): " + "; ".join(vistos) + ".")

    def test_P78_reporte_ocupacion(self):
        y = H.year + 1
        self.reserva(date(y, 6, 1), date(y, 6, 4), estado="aceptada")
        res = {t: v for t, v, _ in self.ctx(tipo="ocupacion", anio=y)["resumen"]}
        dias = (date(y + 1, 1, 1) - date(y, 1, 1)).days
        self.assertEqual((res["Días ocupados"], res["Días libres"]), (3, dias - 3))
        self.assertTrue(res["Porcentaje de ocupación"].endswith("%"))
        self.obt(f"Reporte de ocupación {y}: Días ocupados {res['Días ocupados']}, Días libres {res['Días libres']}, "
                 f"Porcentaje de ocupación {res['Porcentaje de ocupación']}.")

    def test_P79_reporte_ingresos(self):
        p = self.reserva(d(6), d(7), pago="pendiente", monto=20000)
        a = self.reserva(d(10), d(11), pago="abonado", monto=30000, doc="111111111")
        s = self.reserva(d(14), d(15), pago="pendiente", monto=0, doc="222222222")
        self.reserva(d(18), d(19), estado="aceptada", pago="pagado", monto=90000, doc="333333333")
        tablas = self.ctx(tipo="ingresos")["tablas"]
        no_pagadas = sorted(fila[0] for fila in tablas[0]["filas"])
        self.assertEqual(set(no_pagadas), {f"#{p.id}", f"#{a.id}", f"#{s.id}"})
        sin_valor = [t for t in tablas if t["titulo"].startswith("Reservas a las que falta escribir el valor")]
        self.assertTrue(sin_valor and [fila[0] for fila in sin_valor[0]["filas"]] == [f"#{s.id}"])
        self.obt(f"El reporte listó como no pagadas {', '.join(no_pagadas)} y como «sin valor definido» la #{s.id}; la pagada no aparece.")

    def test_P80_descargar_pdf(self):
        self.reserva(d(6), d(8), monto=50000)
        r = self.adm.get(reverse("panel:reporte_pdf"), {"tipo": "ingresos"})
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.obt(f"Se descargó un archivo PDF ({r['Content-Type']}, {len(r.content):,} bytes) con el reporte de ingresos.".replace(",", "."))


# =====================================================================  H14
class H14Configuracion(Base):
    """Configuraciones avanzadas: la administradora cambia teléfono, WhatsApp, correo e Instagram y el sitio lo refleja."""
    NUEVOS = {"telefono": "+56 2 2345 6789", "whatsapp": "+56 9 8765 4321", "email": "Nuevo@Pirque.cl", "instagram": "@nuevo.pirque"}
    WA, CORREO_NUEVO = "56987654321", "nuevo@pirque.cl"

    def test_P81_pantalla_muestra_datos_actuales(self):
        r = self.adm.get(reverse("panel:configuracion"))
        self.assertEqual(r.status_code, 200)
        for clave in ("telefono", "whatsapp", "email", "instagram"):
            self.assertContains(r, f'name="{clave}"')
            self.assertContains(r, settings.SITIO[clave])
        self.assertContains(r, "Guardar cambios")
        self.assertNotContains(r, "Volver a los datos originales")   # nada que restaurar todavía
        self.obt("La pantalla mostró los cuatro campos (teléfono, WhatsApp, correo e Instagram) con los datos actuales del sitio y el botón "
                 "«Guardar cambios»; «Volver a los datos originales» no aparece mientras no se haya cambiado nada.")

    def test_P82_cambios_se_ven_en_el_sitio(self):
        r = self.guardar_contacto(**self.NUEVOS)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(datos_sitio()["whatsapp"], self.WA)
        inicio = self.client.get(reverse("inicio")).content.decode()
        contacto = self.client.get(reverse("contacto")).content.decode()
        for pagina, nombre in ((inicio, "inicio"), (contacto, "contacto")):
            self.assertIn(f"wa.me/{self.WA}", pagina, f"{nombre}: falta el WhatsApp nuevo")
            self.assertIn(f"mailto:{self.CORREO_NUEVO}", pagina, f"{nombre}: falta el correo nuevo")
            self.assertIn("instagram.com/nuevo.pirque", pagina, f"{nombre}: falta el Instagram nuevo")
            self.assertNotIn(settings.SITIO["whatsapp"], pagina, f"{nombre}: sigue el WhatsApp anterior")
            self.assertNotIn(settings.SITIO["email"], pagina, f"{nombre}: sigue el correo anterior")
        self.assertIn("+56 2 2345 6789", contacto)
        self.assertIn("tel:+56223456789", contacto)
        self.obt("Tras guardar, el pie de página y la pantalla Contacto muestran el WhatsApp wa.me/56987654321, el correo nuevo@pirque.cl, "
                 "instagram.com/nuevo.pirque y el teléfono +56 2 2345 6789 (enlace tel:+56223456789); los datos anteriores desaparecieron.")

    def test_P83_whatsapp_nuevo_en_solicitud_y_cancelacion(self):
        self.guardar_contacto(whatsapp=self.WA)
        self.ingresar()
        r = self.solicitar(d(6), d(8))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith(f"https://api.whatsapp.com/send/?phone={self.WA}&"), r["Location"])
        pagina = self.client.get(reverse("mis_reservas")).content.decode()
        self.assertIn(f"phone={self.WA}", pagina, "El botón «Cancelar por WhatsApp» no usa el número nuevo")
        self.assertNotIn(settings.SITIO["whatsapp"], pagina)
        self.obt(f"La solicitud de reserva redirigió a api.whatsapp.com/send/?phone={self.WA} y el botón «Cancelar por WhatsApp» de Mis Reservas "
                 "usa el mismo número nuevo.")

    @override_settings(NOTIFICAR_A=[])
    def test_P84_correos_con_datos_nuevos(self):
        self.guardar_contacto(**self.NUEVOS)
        self.ingresar()
        self.solicitar(d(6), d(8))
        avisos = [m for m in mail.outbox if "Nueva solicitud de reserva" in m.subject]
        self.assertTrue(avisos, "No se avisó a los administradores")
        self.assertIn(self.CORREO_NUEVO, avisos[0].to)
        self.assertNotIn(settings.SITIO["email"], avisos[0].to)
        res = Reserva.objects.get()
        mail.outbox.clear()
        self.adm.post(reverse("panel:reserva_aceptar", args=[res.id]))
        m = [m for m in mail.outbox if CORREO in m.to][0]
        self.assertIn("+56 2 2345 6789", m.body)
        self.assertIn(self.CORREO_NUEVO, m.body)
        self.assertNotIn(settings.SITIO["telefono"], m.body)
        self.obt(f"El aviso de nueva solicitud llegó a {self.CORREO_NUEVO} (ya no al correo anterior) y el correo de confirmación al cliente "
                 "termina con la firma «WhatsApp: +56 2 2345 6789 · nuevo@pirque.cl».")

    def test_P85_validaciones(self):
        casos = [("whatsapp", "abc"), ("whatsapp", "12345"), ("whatsapp", "0123456789"), ("whatsapp", "1" * 16),
                 ("email", "no-es-correo"), ("email", ""), ("instagram", "hola mundo"), ("instagram", "x" * 31),
                 ("instagram", "https://instagram.com/"), ("telefono", "llamar"), ("telefono", "12"), ("telefono", "")]
        for clave, valor in casos:
            r = self.guardar_contacto(**{clave: valor})
            self.assertEqual(r.status_code, 400, f"{clave}={valor!r} debió rechazarse")
            self.assertFalse(r.json()["ok"])
            self.assertTrue(r.json()["error"])
        self.assertFalse(Configuracion.objects.exists(), "Se guardó algo a pesar de los errores")
        self.obt(f"Se rechazaron los {len(casos)} datos inválidos probados (WhatsApp con letras, muy corto, con 0 inicial o muy largo; correo sin formato "
                 "o vacío; Instagram con espacios o muy largo; teléfono con letras, muy corto o vacío) con un mensaje que explica el formato; no se guardó nada.")

    def test_P86_todo_o_nada(self):
        r = self.guardar_contacto(telefono="+56 2 2345 6789", email="no-es-correo")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Configuracion.objects.exists())
        self.assertEqual(datos_sitio()["telefono"], settings.SITIO["telefono"])
        self.obt("Con un teléfono válido y un correo inválido el panel mostró el error y NO guardó tampoco el teléfono (se guarda todo o nada).")

    def test_P87_normalizacion_de_datos(self):
        n = datos_mod
        pares = [(n.normalizar_whatsapp, "+56 9 9771 0934", "56997710934"), (n.normalizar_whatsapp, "997710934", "56997710934"),
                 (n.normalizar_whatsapp, "(56) 9-9771-0934", "56997710934"), (n.normalizar_whatsapp, "+1 202 555 0143", "12025550143"),
                 (n.normalizar_instagram, "@hospedajepirque", "hospedajepirque"),
                 (n.normalizar_instagram, "https://www.instagram.com/Hospedaje.Pirque/?hl=es", "Hospedaje.Pirque"),
                 (n.normalizar_instagram, "instagram.com/abc/", "abc"),
                 (n.normalizar_correo, "  ADMIN@Correo.CL ", "admin@correo.cl"),
                 (n.normalizar_telefono, "  +569   9771  0934 ", "+569 9771 0934")]
        for funcion, entrada, esperado in pares:
            self.assertEqual(funcion(entrada), esperado, f"{funcion.__name__}({entrada!r})")
        self.obt(f"Se normalizaron correctamente {len(pares)} formas de escribir los datos: «+56 9 9771 0934» y «997710934» → 56997710934, "
                 "«@usuario» y el enlace completo del perfil → usuario, correo en minúsculas y sin espacios, teléfono con espacios simples.")

    def test_P88_sin_cambios(self):
        r = self.guardar_contacto()
        self.assertTrue(r.json()["ok"])
        self.assertIn("No había nada que cambiar", r.json()["aviso"])
        self.assertFalse(Configuracion.objects.exists())
        self.obt(f"Al guardar sin modificar nada el panel respondió «{r.json()['aviso']}» y no escribió en la base de datos.")

    def test_P89_cambio_parcial(self):
        r = self.guardar_contacto(instagram="otro.perfil")
        self.assertIn("el Instagram", r.json()["aviso"])
        self.assertEqual(set(Configuracion.objects.values_list("clave", flat=True)), {"instagram"})
        self.assertEqual(datos_sitio()["instagram"], "otro.perfil")
        self.assertEqual(datos_sitio()["whatsapp"], settings.SITIO["whatsapp"])
        pantalla = self.adm.get(reverse("panel:configuracion"))
        self.assertContains(pantalla, "Volver a los datos originales")
        self.assertContains(pantalla, "Último cambio")
        self.obt(f"Al cambiar solo el Instagram se guardó únicamente esa fila; el aviso fue «{r.json()['aviso']}», el resto de los datos siguió igual "
                 "y la pantalla ofrece «Volver a los datos originales» y muestra la fecha del último cambio.")

    def test_P90_restaurar_datos_originales(self):
        self.guardar_contacto(**self.NUEVOS)
        self.assertEqual(Configuracion.objects.count(), 4)
        r = self.adm.post(reverse("panel:configuracion_restaurar"))
        self.assertTrue(r.json()["ok"])
        self.assertFalse(Configuracion.objects.exists())
        for clave in ("telefono", "whatsapp", "email", "instagram"):
            self.assertEqual(datos_sitio()[clave], settings.SITIO[clave])
        self.assertIn(f"wa.me/{settings.SITIO['whatsapp']}", self.client.get(reverse("inicio")).content.decode())
        r2 = self.adm.post(reverse("panel:configuracion_restaurar"))
        self.assertIn("Ya estaban", r2.json()["aviso"])
        self.obt(f"«Volver a los datos originales» borró los 4 cambios, el sitio volvió a usar wa.me/{settings.SITIO['whatsapp']} y, "
                 "al repetirlo, avisó que ya estaban los datos originales.")

    def test_P91_sitio_funciona_si_falla_la_tabla(self):
        with mock.patch("sitio.datos.Configuracion") as falso:
            falso.objects.filter.side_effect = DatabaseError("la tabla no existe")
            r = self.client.get(reverse("inicio"))
            self.assertEqual(r.status_code, 200)
            self.assertIn(f"wa.me/{settings.SITIO['whatsapp']}", r.content.decode())
            self.assertEqual(datos_sitio()["email"], settings.SITIO["email"])
        self.obt("Si la tabla de configuración no existe o la consulta falla, el inicio responde 200 y usa los datos originales de settings.py "
                 "(el sitio no se cae).")

    def test_P92_tabla_definida_en_script_principal(self):
        sql = (settings.BD_DIR / "hospedaje_pirque_bd.sql").read_text(encoding="utf-8")
        self.assertRegex(sql, r"CREATE TABLE IF NOT EXISTS configuracion\s*\(")
        for columna in ("clave", "valor", "fecha_cambio", '"FK_admin"'):
            self.assertIn(columna, sql)
        self.assertIn("configuracion", (settings.BASE_DIR / "panel" / "management" / "commands" / "preparar_bd.py").read_text(encoding="utf-8"))
        self.obt("hospedaje_pirque_bd.sql crea la tabla «configuracion» (clave, valor, fecha_cambio, FK_admin) y preparar_bd la incluye en su resumen.")

    def test_P93_whatsapp_real_con_numero_nuevo(self):
        self.manual("cambiar el WhatsApp en Configuraciones avanzadas y pulsar «Abrir WhatsApp» y «Continuar por WhatsApp» desde un celular: "
                    "debe abrir el chat del número nuevo.")

    # ---------- Recuperación de contraseña del panel (H15) ----------
    def _pedir_enlace(self, correo="admin@pirque.cl"):
        return Client().post(reverse("panel:recuperar"), {"email": correo})

    def _enlace(self):
        return re.search(r"https?://[^/\s]+(/\S+)", mail.outbox[-1].body).group(1)

    def _abrir_formulario(self, c):
        """Abre el enlace del correo; Django redirige a la URL con «set-password». Devuelve esa URL."""
        r = c.get(self._enlace(), follow=True)
        self.assertContains(r, "Crea tu nueva contraseña")
        return r.redirect_chain[-1][0]

    def test_P94_login_muestra_enlace_recuperar(self):
        r = Client().get(reverse("panel:login"))
        self.assertContains(r, "¿Olvidaste tu contraseña?")
        self.assertContains(r, reverse("panel:recuperar"))
        self.assertEqual(Client().get(reverse("panel:recuperar")).status_code, 200)
        self.obt(f"La pantalla de inicio de sesión muestra «¿Olvidaste tu contraseña?», que lleva a {reverse('panel:recuperar')} "
                 "(responde 200 sin sesión).")

    def test_P95_correo_registrado_recibe_enlace(self):
        r = self._pedir_enlace()
        self.assertRedirects(r, reverse("panel:recuperar_enviado"))
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, ["admin@pirque.cl"])
        self.assertIn("/panel/recuperar/", m.body)
        self.obt(f"Con el correo admin@pirque.cl se mostró «Revisa tu correo» y llegó 1 correo («{m.subject}») a {m.to[0]} "
                 f"con el enlace {self._enlace()[:28]}…")

    def test_P96_cambio_de_contrasena_con_enlace_valido(self):
        nueva = "Pirque.Valle2026"
        self._pedir_enlace()
        c = Client()
        url = self._abrir_formulario(c)
        r = c.post(url, {"new_password1": nueva, "new_password2": nueva})
        self.assertRedirects(r, reverse("panel:recuperar_listo"))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(nueva))
        self.assertFalse(self.admin.check_password(CLAVE))
        r = Client().post(reverse("panel:login"), {"usuario": "admin@pirque.cl", "password": nueva})
        self.assertRedirects(r, reverse("panel:inicio"), fetch_redirect_response=False)
        self.obt("Con el enlace del correo se guardó la contraseña nueva, apareció «¡Listo! Tu contraseña cambió», se inició sesión con la "
                 "contraseña nueva y la anterior dejó de funcionar.")

    def test_P97_contrasenas_que_no_coinciden(self):
        self._pedir_enlace()
        c = Client()
        url = self._abrir_formulario(c)
        r = c.post(url, {"new_password1": "Pirque.Valle2026", "new_password2": "OtraDistinta.99"})
        self.assertEqual(r.status_code, 200)
        error = " ".join(r.context["form"].errors.get("new_password2", []))
        self.assertTrue(error)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(CLAVE))
        self.obt(f"Con dos contraseñas distintas el formulario mostró «{error}» y la contraseña no cambió.")
