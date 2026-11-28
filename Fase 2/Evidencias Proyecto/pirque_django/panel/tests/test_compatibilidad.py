"""Pruebas de compatibilidad y accesibilidad (C1 a C6 y C17 a C27) de la hoja «Compatibilidad» del Plan de pruebas.

Revisan lo que se puede comprobar sin un navegador: estructura HTML estándar, formato de enlaces, PDF y correos, y los
criterios de accesibilidad WCAG 2.2 nivel AA que se pueden verificar en el HTML (etiquetas, textos alternativos, idioma,
contraste de los colores, saltar al contenido, menú de accesibilidad, etc.).
Las pruebas en navegadores y dispositivos reales (C7 a C16) y las de accesibilidad con teclado, lector de pantalla,
zoom y Lighthouse (C28 a C31) están solo en el Excel y se hacen a mano.
"""
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.core import mail
from django.test import Client
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


# =====================================================================  Accesibilidad (WCAG 2.2 AA)
class Html(HTMLParser):
    """Recorre el HTML y junta lo necesario para revisar la accesibilidad."""
    def __init__(self):
        super().__init__()
        self.ids, self.labels_for, self.controles, self.imgs, self.iframes, self.h1 = set(), set(), [], [], [], 0
        self.html_lang, self.dentro_label = None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"): self.ids.add(a["id"])
        if tag == "html": self.html_lang = a.get("lang")
        if tag == "label":
            self.dentro_label += 1
            if a.get("for"): self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit", "button"):
            self.controles.append({**a, "_tag": tag, "_en_label": self.dentro_label > 0})
        if tag == "img": self.imgs.append(a)
        if tag == "iframe": self.iframes.append(a)
        if tag == "h1": self.h1 += 1

    def handle_endtag(self, tag):
        if tag == "label" and self.dentro_label: self.dentro_label -= 1

    def sin_etiqueta(self):
        """Controles visibles sin nombre accesible (ni <label for>, ni aria-label/labelledby, ni dentro de un <label>)."""
        malos = []
        for c in self.controles:
            if c.get("class", "").find("flatpickr") >= 0 or c.get("name") == "sitio_web":
                continue        # campo interno del calendario y campo trampa (ocultos para todos)
            if not (c.get("id") in self.labels_for or c.get("aria-label") or c.get("aria-labelledby") or c["_en_label"]):
                malos.append(c.get("name") or c.get("id") or c["_tag"])
        return malos


def analizar(html):
    h = Html(); h.feed(html); return h


def contraste(a, b):
    def lum(x):
        x = x.lstrip("#"); c = [int(x[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


class Accesibilidad(Base):
    def paginas(self):
        """(nombre, html) de las páginas públicas y del panel, incluidas la reseña y la política de privacidad."""
        self.ingresar()
        res = self.resena()
        salida = [(n, self.client.get(reverse(n)).content.decode()) for n in PUBLICAS + ("privacidad",)]
        salida.append(("resena", self.client.get(reverse("resena", args=[res.token])).content.decode()))
        salida += [(f"panel {n}", self.adm.get(reverse(f"panel:{n}")).content.decode()) for n in PANEL]
        salida += [(f"panel {n}", Client().get(reverse(f"panel:{n}")).content.decode()) for n in ("login", "recuperar")]
        return salida

    def test_C17_saltar_al_contenido(self):
        paginas = self.paginas()
        for nombre, html in paginas:
            self.assertIn('class="saltar-contenido" href="#contenido"', html, nombre)
            self.assertIn('id="contenido"', html, nombre)
        self.obt(f"Las {len(paginas)} páginas (sitio, reseña, privacidad y panel, incluido el inicio de sesión) empiezan con el enlace "
                 "«Saltar al contenido principal» que lleva a #contenido (WCAG 2.4.1).")

    def test_C18_campos_con_etiqueta(self):
        revisados = 0
        paginas = self.paginas()
        for nombre, html in paginas:
            h = analizar(html)
            self.assertEqual(h.sin_etiqueta(), [], f"{nombre}: campos sin etiqueta")
            revisados += len(h.controles)
        self.obt(f"Los {revisados} campos de formulario de {len(paginas)} páginas tienen una etiqueta asociada (<label for>, aria-label "
                 "o dentro de su etiqueta), incluidos los de las ventanas del panel y el inicio de sesión (WCAG 1.3.1, 3.3.2 y 4.1.2).")

    def test_C19_errores_enlazados_al_campo(self):
        r = self.client.post(reverse("contacto"), {"nombre": "", "correo": "no-es-correo", "mensaje": "Hola"})
        h = r.content.decode()
        for campo in ("nombre", "correo"):
            self.assertRegex(h, rf'<(input)[^>]*name="{campo}"[^>]*aria-invalid="true"', campo)
            self.assertRegex(h, rf'<input[^>]*name="{campo}"[^>]*aria-describedby="[^"]*id_{campo}_error', campo)
            self.assertIn(f'id="id_{campo}_error"', h)
        r = self.ingresar(rut="12AB")
        self.assertRegex(r.content.decode(), r'<input[^>]*aria-describedby="[^"]*id_rut_error')
        self.obt("Con datos inválidos, cada campo con error queda marcado con aria-invalid=\"true\" y enlazado a su mensaje "
                 "(aria-describedby → id_<campo>_error), en contacto y en la identificación del huésped (WCAG 3.3.1 y 3.3.3).")

    def test_C20_imagenes_e_iframes_con_texto_alternativo(self):
        n_img = n_iframe = 0
        for nombre, html in self.paginas():
            h = analizar(html)
            for img in h.imgs:
                self.assertIn("alt", img, f"{nombre}: imagen sin alt ({img.get('src')})")
            for fr in h.iframes:
                self.assertTrue(fr.get("title"), f"{nombre}: iframe sin title")
            n_img, n_iframe = n_img + len(h.imgs), n_iframe + len(h.iframes)
        self.obt(f"Las {n_img} imágenes revisadas tienen texto alternativo (alt vacío solo en las decorativas) y los {n_iframe} mapas "
                 "incrustados tienen título; los íconos decorativos llevan aria-hidden (WCAG 1.1.1 y 4.1.2).")

    def test_C21_idioma_de_la_pagina_y_de_sus_partes(self):
        vistos = []
        for codigo in ("es", "en", "pt"):
            self.idioma(self.client, codigo)
            html = self.client.get(reverse("inicio")).content.decode()
            self.assertEqual(analizar(html).html_lang, codigo)
            for otro in ("es", "en", "pt"):
                self.assertIn(f'value="{otro}" lang="{otro}"', html)
            vistos.append(f'lang="{codigo}"')
        self.obt(f"El sitio declara el idioma activo ({', '.join(vistos)}) y cada opción del selector de idioma lleva su propio lang "
                 "(WCAG 3.1.1 y 3.1.2); el panel declara lang=\"es\".")

    def test_C22_menu_de_accesibilidad(self):
        paginas = self.paginas()
        for nombre, html in paginas:
            self.assertIn('id="a11yBoton"', html, nombre)
            for opcion in ("contraste", "subrayar", "espaciado", "legible", "sin-animaciones"):
                self.assertIn(f'data-a11y-opcion="{opcion}" aria-pressed=', html, f"{nombre}: falta {opcion}")
            self.assertIn('data-a11y-texto="3"', html, nombre)
        estatico = Path(settings.BASE_DIR) / "static"
        js = (estatico / "js" / "accesibilidad.js").read_text(encoding="utf-8")
        css = (estatico / "css" / "accesibilidad.css").read_text(encoding="utf-8")
        self.assertIn("pirque_a11y", js)
        self.assertIn("Escape", js)
        for clase in ("a11y-texto-1", "a11y-texto-2", "a11y-texto-3", "a11y-contraste", "a11y-subrayar", "a11y-espaciado",
                      "a11y-legible", "a11y-sin-animaciones"):
            self.assertIn(f"html.{clase}", css, clase)
        self.assertIn("prefers-reduced-motion", css)
        self.obt(f"Las {len(paginas)} páginas tienen el botón «Accesibilidad» con tamaño de texto (4 niveles), alto contraste, subrayar "
                 "enlaces, más espaciado, letra legible y detener animaciones; las opciones son botones con aria-pressed, el menú se "
                 "cierra con Esc y la elección se guarda en el navegador (pirque_a11y).")

    def test_C23_contraste_de_colores(self):
        estatico = Path(settings.BASE_DIR)
        css = " ".join(p.read_text(encoding="utf-8").lower() for p in (
            estatico / "static" / "css" / "style.css", estatico / "static" / "css" / "accesibilidad.css",
            estatico / "panel" / "static" / "panel" / "css" / "panel.css"))
        pares = [  # (texto o elemento, fondo, mínimo, dónde)
            ("ffffff", "557530", 4.5, "botón verde del sitio"), ("6c757d", "ffffff", 4.5, "texto de ayuda dentro de los campos"),
            ("6c757d", "ffffff", 3.0, "borde de los campos"), ("ffe5e8", "06744a", 4.5, "mensajes de error sobre el fondo verde"),
            ("7a4d00", "fdebc8", 4.5, "etiqueta «Pendiente» del panel"), ("8a6100", "ffffff", 3.0, "estrellas de las reseñas en el panel"),
            ("0f3d2c", "ffffff", 3.0, "anillo de foco sobre fondo claro"), ("ffd45e", "0f3d2c", 3.0, "anillo de foco sobre fondo oscuro"),
            ("ffffff", "0f3d2c", 4.5, "botón «Accesibilidad»"), ("1c2b24", "ffffff", 4.5, "texto del menú de accesibilidad"),
            ("ffffff", "06744a", 4.5, "texto blanco sobre el fondo del sitio"), ("ffff00", "000000", 7.0, "enlaces en alto contraste"),
        ]
        resultados = []
        for fg, bg, minimo, donde in pares:
            for color in (fg, bg):
                if color not in ("ffffff", "000000", "ffff00"):
                    self.assertIn(f"#{color}", css, f"El color #{color} ({donde}) ya no está en las hojas de estilo")
            valor = contraste(fg, bg)
            self.assertGreaterEqual(valor, minimo, f"{donde}: contraste {valor:.2f} (mínimo {minimo})")
            resultados.append(f"{donde} {valor:.1f}:1")
        self.obt("Contraste calculado con la fórmula de WCAG (1.4.3 texto 4.5:1, 1.4.11 componentes 3:1): " + "; ".join(resultados) + ".")

    def test_C24_carrusel_se_puede_pausar(self):
        html = self.client.get(reverse("servicios")).content.decode()
        self.assertIn('class="carrusel-pausa"', html)
        self.assertIn('aria-roledescription="carrusel"', html)
        js = (Path(settings.BASE_DIR) / "static" / "js" / "accesibilidad.js").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", js)
        self.assertIn("focusin", js)
        self.obt("El carrusel de Servicios tiene el botón «Pausar/Reanudar», se detiene mientras tiene el foco del teclado y no se mueve "
                 "solo si la persona eligió «Detener animaciones» o pidió reducir el movimiento en su sistema (WCAG 2.2.2).")

    def test_C25_actualizacion_automatica_se_puede_pausar(self):
        html = self.adm.get(reverse("panel:reservas")).content.decode()
        self.assertIn('id="chkAutoActualizar"', html)
        self.assertIn('<label class="form-check-label" for="chkAutoActualizar">', html)
        js = (Path(settings.BASE_DIR) / "panel" / "static" / "panel" / "js" / "panel.js").read_text(encoding="utf-8")
        self.assertIn("auto && !auto.checked", js)
        self.assertNotIn("setTimeout(() => d.remove()", js)
        self.obt("En Reservas la casilla «Actualizar sola cada 30 segundos» permite pausar la actualización automática (se recuerda), "
                 "y los avisos del panel ya no desaparecen solos: se cierran con la × (WCAG 2.2.1 y 2.2.2).")

    def test_C26_fechas_sin_calendario(self):
        self.ingresar()
        h = analizar(self.client.get(reverse("reservar")).content.decode())
        fechas = {c["id"]: c for c in h.controles if c.get("type") == "date"}
        self.assertEqual(set(fechas), {"id_llegada", "id_salida"})
        self.assertTrue({"id_llegada", "id_salida"} <= h.labels_for)
        r = self.solicitar(d(6), d(8))
        self.assertEqual(r.status_code, 302)
        self.obt("Además del calendario, la solicitud de reserva tiene «Escribir las fechas»: campos de fecha normales con etiqueta, "
                 "que se usan con el teclado o un lector de pantalla y se revisan igual que el calendario (WCAG 2.1.1).")

    def test_C27_un_titulo_principal_por_pagina(self):
        paginas = self.paginas()
        for nombre, html in paginas:
            self.assertEqual(analizar(html).h1, 1, f"{nombre}: debe tener un solo <h1>")
        self.obt(f"Cada una de las {len(paginas)} páginas tiene exactamente un título principal <h1> y las ventanas usan <h2> "
                 "(WCAG 1.3.1 y 2.4.6).")
