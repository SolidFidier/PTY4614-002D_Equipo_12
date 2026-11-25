"""Pruebas de seguridad básica (S1 a S23) de la hoja «Seguridad» del Plan de pruebas."""
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from io import StringIO

from panel.models import Cliente, Configuracion, Mensaje, Resena, Reserva
from sitio import whatsapp

from .base import CLAVE, RUT, Base, d, texto_wa

PAGINAS_PANEL = ["inicio", "reservas", "clientes", "mensajes", "resenas", "reportes", "reporte_pdf", "ayuda",
                 "configuracion", "api_ocupacion", "api_pendientes", "api_ocupadas"]
ATAQUE_SQL = "' OR '1'='1' --"
SCRIPT = "<script>alert('x')</script>"


class Seguridad(Base):
    def test_S01_paginas_del_panel_sin_sesion(self):
        c = Client()
        for nombre in PAGINAS_PANEL:
            r = c.get(reverse(f"panel:{nombre}"))
            self.assertEqual(r.status_code, 302, f"/{nombre} respondió {r.status_code} sin sesión")
            self.assertIn(reverse("panel:login"), r["Location"], f"{nombre} no redirige al inicio de sesión")
        self.obt(f"Las {len(PAGINAS_PANEL)} páginas y consultas del panel ({', '.join(PAGINAS_PANEL)}) respondieron 302 "
                 "y redirigieron a /panel/login/ sin sesión.")

    def test_S02_acciones_del_panel_sin_sesion(self):
        res = self.reserva(d(6), d(8))
        msj = Mensaje.objects.create(nombre="Ana", correo="ana@c.cl", contenido="Hola", fecha_envio=res.fecha_reserva)
        c = Client()
        acciones = [("reserva_aceptar", res.id), ("reserva_eliminar", res.id), ("cliente_eliminar", RUT), ("mensaje_toggle", msj.id)]
        for nombre, pk in acciones:
            r = c.post(reverse(f"panel:{nombre}", args=[pk]))
            self.assertEqual(r.status_code, 302, f"{nombre} respondió {r.status_code} sin sesión")
        res.refresh_from_db()
        msj.refresh_from_db()
        self.assertEqual(res.estado_reserva, "pendiente")
        self.assertTrue(Cliente.objects.filter(id=RUT).exists())
        self.assertIsNone(msj.fecha_gestion)
        self.obt(f"Las acciones {', '.join(a for a, _ in acciones)} enviadas sin sesión fueron redirigidas al inicio de sesión; "
                 f"la reserva #{res.id} siguió «pendiente», el cliente siguió registrado y el mensaje siguió sin gestionar.")

    def test_S03_contrasenas_cifradas(self):
        guardada = self.admin.password
        self.assertNotEqual(guardada, CLAVE)
        self.assertNotIn(CLAVE, guardada)
        algoritmo = guardada.split("$")[0]
        self.assertIn(algoritmo, ("pbkdf2_sha256", "argon2", "bcrypt_sha256", "scrypt"))
        self.obt(f"La contraseña se guarda cifrada con el algoritmo «{algoritmo}» ({len(guardada)} caracteres); el texto original no aparece.")

    def test_S04_cierre_de_sesion_panel(self):
        r = self.adm.get(reverse("panel:logout"))
        self.assertEqual(r["Location"], reverse("panel:login"))
        r = self.adm.get(reverse("panel:inicio"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("panel:login"), r["Location"])
        self.obt(f"Tras cerrar sesión, al volver a /panel/ se redirigió a {r['Location']}.")

    def test_S05_cierre_de_sesion_cliente(self):
        self.ingresar()
        self.assertIn("huesped", self.client.session)
        self.client.get(reverse("logout_cliente"))
        self.assertNotIn("huesped", self.client.session)
        r = self.client.get(reverse("mis_reservas"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login_cliente"), r["Location"])
        self.obt(f"Tras «Salir», la sesión del cliente se borró y «Mis Reservas» redirigió a {r['Location']}.")

    def test_S06_csrf_formulario_publico(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("contacto"), {"nombre": "Ana", "correo": "ana@c.cl", "mensaje": "Hola"}, follow=True)
        self.assertFalse(Mensaje.objects.exists(), "Se guardó un mensaje enviado sin token CSRF")
        self.assertContains(r, "había expirado")
        self.obt("El formulario de contacto enviado sin token CSRF fue rechazado: se mostró «La página del formulario había expirado. "
                 "Inténtalo de nuevo.» y no se guardó el mensaje.")

    def test_S07_csrf_panel(self):
        res = self.reserva(d(6), d(8))
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        r = c.post(reverse("panel:reserva_aceptar", args=[res.id]))
        self.assertEqual(r.status_code, 403)
        res.refresh_from_db()
        self.assertEqual(res.estado_reserva, "pendiente")
        self.obt(f"Con sesión iniciada pero sin token CSRF, aceptar la reserva #{res.id} respondió {r.status_code} (prohibido) "
                 f"y la reserva siguió «{res.estado_reserva}».")

    def test_S08_privacidad_entre_clientes(self):
        ajena = self.reserva(d(6), d(8), doc="111111111", nombre="Ana", apellido="Rojas", correo="ana@correo.com")
        r = Client().get(reverse("mis_reservas"))
        self.assertEqual(r.status_code, 302)
        self.ingresar()
        lista = self.client.get(reverse("mis_reservas")).context["reservas"]
        self.assertNotIn(ajena.id, [x.id for x in lista])
        self.obt(f"Sin identificarse, «Mis Reservas» redirigió al ingreso. Identificado como {RUT}, se mostraron {len(lista)} reservas "
                 f"y no apareció la #{ajena.id} de otro cliente.")

    def test_S09_inyeccion_sql_en_buscadores(self):
        self.reserva(d(6), d(8))
        Mensaje.objects.create(nombre="Ana", correo="ana@c.cl", contenido="Hola", fecha_envio=Reserva.objects.get().fecha_reserva)
        resultados = []
        for nombre, clave in (("reservas", "lista"), ("clientes", "page"), ("mensajes", "page")):
            r = self.adm.get(reverse(f"panel:{nombre}"), {"q": ATAQUE_SQL})
            self.assertEqual(r.status_code, 200)
            n = len(list(r.context[clave]))
            self.assertEqual(n, 0, f"La búsqueda en {nombre} devolvió {n} registros con un texto de inyección SQL")
            resultados.append(f"{nombre}: {n}")
        self.assertEqual((Reserva.objects.count(), Cliente.objects.count(), Mensaje.objects.count()), (1, 1, 1))
        self.obt(f"Al buscar «{ATAQUE_SQL}» las páginas respondieron 200 sin resultados ({', '.join(resultados)}) "
                 "y los datos siguieron intactos (1 reserva, 1 cliente, 1 mensaje).")

    def test_S10_xss_contenido_escapado(self):
        Mensaje.objects.create(nombre="Atacante", correo="x@c.cl", contenido=SCRIPT, fecha_envio=self.reserva(d(6), d(8)).fecha_reserva)
        html_panel = self.adm.get(reverse("panel:mensajes")).content.decode()
        self.assertNotIn(SCRIPT, html_panel)
        self.assertIn("&lt;script&gt;", html_panel)
        self.resena(respondida=True, visible=True, comentario=SCRIPT)
        html_inicio = self.client.get(reverse("inicio")).content.decode()
        self.assertNotIn(SCRIPT, html_inicio)
        self.obt("Un mensaje y una reseña con «<script>alert('x')</script>» se mostraron escapados (&lt;script&gt;) en el panel "
                 "y en el inicio; el código no se ejecuta.")

    def test_S11_enlaces_de_resena_impredecibles(self):
        r1 = self.reserva(d(-10), d(-8), estado="aceptada")
        r2 = self.reserva(d(-6), d(-3), estado="aceptada", doc="111111111")
        call_command("enviar_resenas", stdout=StringIO())
        t1, t2 = Resena.objects.get(reserva=r1).token, Resena.objects.get(reserva=r2).token
        self.assertNotEqual(t1, t2)
        self.assertGreaterEqual(min(len(t1), len(t2)), 40)
        r = self.client.get(reverse("resena", args=[t1[:-1] + ("A" if t1[-1] != "A" else "B")]))
        self.assertEqual(r.status_code, 404)
        self.obt(f"Cada reserva recibió un enlace distinto de {len(t1)} caracteres aleatorios; cambiar un solo carácter del enlace respondió 404.")

    def test_S12_datos_sensibles_en_whatsapp(self):
        res = self.reserva(d(6), d(8))
        t1, t2 = texto_wa(whatsapp.solicitud(res)), texto_wa(whatsapp.cancelacion(res))
        self.assertNotIn(RUT, t1)
        self.assertNotIn(RUT, t2)
        self.obt(f"Ni el mensaje de solicitud ni el de cancelación de la reserva #{res.id} incluyen el RUT {RUT}.")

    def test_S13_validacion_en_el_servidor(self):
        self.ingresar()
        err = self.errores(self.solicitar(d(6), d(8), adultos=0))
        self.assertTrue(err, "Se aceptaron 0 adultos")
        r = self.client.post(reverse("contacto"), {"nombre": "A" * 150, "correo": "ana@c.cl", "mensaje": "Hola"})
        self.assertIn("nombre", r.context["form"].errors)
        self.assertFalse(Reserva.objects.exists())
        self.assertFalse(Mensaje.objects.exists())
        self.obt(f"Saltándose el navegador, una reserva con 0 adultos fue rechazada («{err}») y un nombre de 150 caracteres "
                 "en contacto también; no se guardó nada.")

    def test_S14_configuracion_de_sesion_y_cookies(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 8 * 60 * 60)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual((settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME), ("pirque_sessionid", "pirque_csrftoken"))
        self.obt(f"La sesión vence a las {settings.SESSION_COOKIE_AGE // 3600} horas, la cookie de sesión es HttpOnly "
                 f"(no la puede leer JavaScript) y las cookies usan nombres propios ({settings.SESSION_COOKIE_NAME}, {settings.CSRF_COOKIE_NAME}).")

    def test_S15_configuracion_para_publicar(self):
        fuente = (Path(settings.BASE_DIR) / "config" / "settings.py").read_text(encoding="utf-8")
        for var in ("DJANGO_SECRET_KEY", "DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS"):
            self.assertIn(var, fuente, f"settings.py no lee {var}")
        self.manual("settings.py lee DJANGO_SECRET_KEY, DJANGO_DEBUG y DJANGO_ALLOWED_HOSTS, pero sus valores por defecto son de desarrollo "
                    "(DEBUG activado y clave de ejemplo). Antes de publicar se deben definir en el servidor y comprobarlo.")

    # ---------- Configuraciones avanzadas (datos de contacto del sitio) ----------
    def test_S16_configuracion_sin_sesion_o_con_metodo_incorrecto(self):
        c = Client()
        for nombre in ("configuracion_guardar", "configuracion_restaurar"):
            r = c.post(reverse(f"panel:{nombre}"), self.contacto_panel(whatsapp="56911112222"))
            self.assertEqual(r.status_code, 302, f"{nombre} respondió {r.status_code} sin sesión")
            self.assertIn(reverse("panel:login"), r["Location"])
        self.assertFalse(Configuracion.objects.exists(), "Se guardó un dato sin haber iniciado sesión")
        for nombre in ("configuracion_guardar", "configuracion_restaurar"):
            self.assertEqual(self.adm.get(reverse(f"panel:{nombre}")).status_code, 405, f"{nombre} acepta GET")
        self.obt("Guardar y restaurar los datos de contacto sin sesión redirigen al inicio de sesión y no cambian nada; con sesión pero por GET "
                 "responden 405 (solo aceptan POST).")

    def test_S17_configuracion_exige_token_csrf(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        r = c.post(reverse("panel:configuracion_guardar"), self.contacto_panel(whatsapp="56911112222"))
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Configuracion.objects.exists())
        self.obt("Un POST a «guardar datos de contacto» sin token CSRF (aunque haya sesión iniciada) fue rechazado con 403 y no se guardó nada.")

    def test_S18_configuracion_rechaza_codigo_malicioso(self):
        ataques = [("instagram", SCRIPT), ("instagram", '"><img src=x onerror=alert(1)>'), ("telefono", SCRIPT), ("email", SCRIPT),
                   ("email", f"a@b.cl{ATAQUE_SQL}"), ("whatsapp", ATAQUE_SQL), ("instagram", ATAQUE_SQL)]
        for clave, valor in ataques:
            r = self.guardar_contacto(**{clave: valor})
            self.assertEqual(r.status_code, 400, f"{clave}={valor!r} se aceptó")
        self.assertFalse(Configuracion.objects.exists())
        pagina = self.client.get(reverse("inicio")).content.decode() + self.client.get(reverse("contacto")).content.decode()
        self.assertNotIn("<script>alert", pagina)
        self.assertNotIn("onerror=", pagina)
        self.obt(f"Se rechazaron {len(ataques)} intentos con código HTML/JavaScript o SQL en los campos de contacto; no se guardó nada y el sitio no contiene "
                 "ese código.")

    # ---------- Recuperación de contraseña del panel (H15) ----------
    def _pedir_enlace(self, correo="admin@pirque.cl"):
        return Client().post(reverse("panel:recuperar"), {"email": correo})

    def _enlace(self):
        import re
        return re.search(r"https?://[^/\s]+(/\S+)", mail.outbox[-1].body).group(1)

    def test_S19_recuperar_con_correo_no_registrado(self):
        r1 = self._pedir_enlace("nadie@ejemplo.cl")
        self.assertRedirects(r1, reverse("panel:recuperar_enviado"))
        self.assertEqual(len(mail.outbox), 0)
        r2 = self._pedir_enlace()
        self.assertEqual(r1["Location"], r2["Location"])
        self.obt("Con un correo que no existe se mostró la misma pantalla «Revisa tu correo» que con uno registrado y no se envió ningún "
                 "correo: no se puede averiguar qué cuentas existen.")

    def test_S20_recuperar_solo_para_cuentas_del_personal(self):
        get_user_model().objects.create_user("cliente", "cliente@ejemplo.cl", "Otra.Clave2026", is_staff=False)
        self._pedir_enlace("cliente@ejemplo.cl")
        self.assertEqual(len(mail.outbox), 0)
        self.obt("Un usuario activo que no es del personal (is_staff = falso) pidió recuperar su contraseña y no se le envió el enlace.")

    def test_S21_contrasena_nueva_debil(self):
        self._pedir_enlace()
        c = Client()
        url = c.get(self._enlace(), follow=True).redirect_chain[-1][0]
        r = c.post(url, {"new_password1": "12345678", "new_password2": "12345678"})
        self.assertEqual(r.status_code, 200)
        errores = " ".join(r.context["form"].errors.get("new_password2", []))
        self.assertTrue(errores)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(CLAVE))
        self.obt(f"La contraseña «12345678» fue rechazada por los validadores de Django («{errores}») y la contraseña no cambió.")

    def test_S22_enlace_de_un_solo_uso(self):
        self._pedir_enlace()
        enlace, c = self._enlace(), Client()
        url = c.get(enlace, follow=True).redirect_chain[-1][0]
        c.post(url, {"new_password1": "Pirque.Valle2026", "new_password2": "Pirque.Valle2026"})
        r = Client().get(enlace, follow=True)
        self.assertContains(r, "El enlace ya no sirve")
        self.obt("Después de cambiar la contraseña, al abrir de nuevo el mismo enlace se mostró «El enlace ya no sirve» con el botón para "
                 "pedir uno nuevo.")

    def test_S23_enlace_vence_en_una_hora(self):
        from datetime import timedelta
        from unittest import mock
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        self.assertEqual(settings.PASSWORD_RESET_TIMEOUT, 3600)
        self._pedir_enlace()
        enlace = self._enlace()
        ahora = PasswordResetTokenGenerator()._now()
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=ahora + timedelta(minutes=61)):
            r = Client().get(enlace, follow=True)
        self.assertContains(r, "El enlace ya no sirve")
        self.obt("Con PASSWORD_RESET_TIMEOUT = 3600, el enlace abierto 61 minutos después mostró «El enlace ya no sirve» y no permitió "
                 "cambiar la contraseña.")
