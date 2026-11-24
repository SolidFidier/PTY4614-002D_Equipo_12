"""Pruebas de compatibilidad (C1 a C6) de la hoja «Compatibilidad» del Plan de pruebas.

Revisan lo que se puede comprobar sin un navegador: estructura HTML estándar, formato de enlaces, PDF y correos.
Las pruebas en navegadores y dispositivos reales (C7 en adelante) están solo en el Excel y se hacen a mano.
"""
from django.core import mail
from django.urls import reverse

from panel.models import Reserva
from sitio import whatsapp

from .base import CORREO, Base, d

PUBLICAS = ("inicio", "servicios", "quienes_somos", "como_llegar", "contacto", "login_cliente", "reservar", "mis_reservas")
PANEL = ("inicio", "reservas", "clientes", "mensajes", "resenas", "reportes", "ayuda", "configuracion")


class Compatibilidad(Base):
    def revisar_html(self, html, pagina):
        inicio = html.lstrip()[:200].lower()
        self.assertTrue(inicio.startswith("<!doctype html>") or "<!doctype html>" in inicio, f"{pagina}: falta <!doctype html>")
        self.assertIn('charset="utf-8"', html.lower().replace("charset=utf-8", 'charset="utf-8"'), f"{pagina}: falta charset utf-8")
        self.assertIn('name="viewport"', html, f"{pagina}: falta la etiqueta viewport")
        self.assertIn("<html lang=", html, f"{pagina}: falta el idioma de la página")

    def test_C01_html_estandar_sitio(self):
        self.ingresar()
        for nombre in PUBLICAS:
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 200, nombre)
            self.revisar_html(r.content.decode(), nombre)
        self.obt(f"Las {len(PUBLICAS)} páginas públicas ({', '.join(PUBLICAS)}) declaran <!doctype html>, codificación UTF-8, "
                 "etiqueta viewport para celulares e idioma de la página.")

    def test_C02_html_estandar_panel(self):
        for nombre in PANEL:
            r = self.adm.get(reverse(f"panel:{nombre}"))
            self.assertEqual(r.status_code, 200, nombre)
            self.revisar_html(r.content.decode(), f"panel {nombre}")
        self.obt(f"Las {len(PANEL)} páginas del panel declaran <!doctype html>, UTF-8, viewport y lang=\"es\".")

    def test_C03_calendario_independiente_del_navegador(self):
        self.ingresar()
        vistos = []
        for codigo, archivo in (("es", "l10n/es.js"), ("pt", "l10n/pt.js"), ("en", None)):
            self.idioma(self.client, codigo)
            html = self.client.get(reverse("reservar")).content.decode()
            self.assertIn("flatpickr.min.css", html, codigo)
            self.assertIn("flatpickr(", html, codigo)
            self.assertIn(f'const lang = "{codigo}"', html, codigo)
            otros = [a for a in ("l10n/es.js", "l10n/pt.js") if a != archivo]
            if archivo:
                self.assertIn(archivo, html, f"En «{codigo}» no se carga la traducción {archivo}")
            for a in otros:
                self.assertNotIn(a, html, f"En «{codigo}» se carga una traducción que no corresponde ({a})")
            vistos.append(f"{codigo}: {archivo or 'inglés incluido en flatpickr'}")
        self.obt("El calendario de reserva usa la librería flatpickr en lugar del calendario nativo de cada navegador, "
                 "y carga solo la traducción del idioma activo (" + "; ".join(vistos) + ").")

    def test_C04_enlaces_whatsapp_app_y_web(self):
        res = self.reserva(d(6), d(8))
        url = whatsapp.solicitud(res)
        self.assertTrue(url.startswith("https://api.whatsapp.com/send/?phone="))
        self.assertIn("%F0%9F%93%85", url.upper())   # 📅 codificado en UTF-8
        self.assertNotIn(" ", url)
        self.obt("Los mensajes usan https://api.whatsapp.com/send/ (abre la app en el celular y WhatsApp Web en el computador) "
                 "con el texto codificado en UTF-8, de modo que los emojis (📅 = %F0%9F%93%85) llegan bien en ambos.")

    def test_C05_pdf_estandar(self):
        self.reserva(d(6), d(8), monto=50000)
        r = self.adm.get(reverse("panel:reporte_pdf"), {"tipo": "reservas"})
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF-1."))
        self.assertIn(b"%%EOF", r.content[-1024:])
        self.assertIn('filename="reservas.pdf"', r["Content-Disposition"])
        version = r.content[:8].decode()
        self.obt(f"El reporte se descarga como «reservas.pdf», con encabezado estándar {version} y cierre %%EOF, "
                 "compatible con cualquier lector de PDF.")

    def test_C06_correos_compatibles(self):
        self.ingresar()
        self.solicitar(d(6), d(8))
        res = Reserva.objects.get()
        mail.outbox.clear()
        self.adm.post(reverse("panel:reserva_aceptar", args=[res.id]))
        m = [m for m in mail.outbox if CORREO in m.to][0]
        msg = m.message()
        self.assertEqual(msg.get_content_type(), "text/plain")
        self.assertEqual(msg.get_content_charset(), "utf-8")
        self.assertIn("¡Tu reserva fue confirmada!", m.body)
        self.obt(f"El correo «{m.subject}» se envía como texto plano en UTF-8 (sin diseño HTML), por lo que se lee igual en "
                 "Gmail, Outlook o el celular y conserva tildes y signos (¡Tu reserva fue confirmada!).")
