"""Pruebas de rendimiento (R1 a R11) de la hoja «Rendimiento» del Plan de pruebas.

Los tiempos se miden en el servidor (sin red) y dependen del equipo donde se ejecutan.
"""
import time
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from panel.models import Cliente, Reserva

from .base import Base, H, d

N = 500                 # reservas cargadas para las pruebas de volumen
MAX_PUBLICA = 1.0       # segundos
MAX_PANEL = 2.0
MAX_API = 1.0
MAX_PDF = 5.0
MAX_IMAGEN = 1024 * 1024  # 1 MB


def medir(fn):
    t = time.perf_counter()
    r = fn()
    return r, time.perf_counter() - t


def ms(seg):
    return f"{seg * 1000:.0f} ms"


class Rendimiento(Base):
    def test_R01_paginas_publicas(self):
        self.ingresar()
        tiempos = {}
        for nombre in ("inicio", "servicios", "quienes_somos", "como_llegar", "contacto", "reservar", "mis_reservas"):
            r, t = medir(lambda: self.client.get(reverse(nombre)))
            self.assertEqual(r.status_code, 200, nombre)
            self.assertLess(t, MAX_PUBLICA, f"{nombre} tardó {ms(t)} (máximo {MAX_PUBLICA} s)")
            tiempos[nombre] = t
        self.obt("Tiempos de respuesta del servidor: " + ", ".join(f"{k} {ms(v)}" for k, v in tiempos.items()) +
                 f". Todas bajo {MAX_PUBLICA:.0f} s.")

    def test_R02_paginas_del_panel_con_volumen(self):
        self.muchas_reservas(N)
        tiempos = {}
        for nombre in ("inicio", "reservas", "clientes", "reportes", "resenas", "mensajes"):
            r, t = medir(lambda: self.adm.get(reverse(f"panel:{nombre}")))
            self.assertEqual(r.status_code, 200, nombre)
            self.assertLess(t, MAX_PANEL, f"{nombre} tardó {ms(t)} con {N} reservas (máximo {MAX_PANEL} s)")
            tiempos[nombre] = t
        self.obt(f"Con {N} reservas y {N} clientes cargados: " + ", ".join(f"{k} {ms(v)}" for k, v in tiempos.items()) +
                 f". Todas bajo {MAX_PANEL:.0f} s.")

    def test_R03_paginacion_con_volumen(self):
        self.muchas_reservas(N)
        r = self.adm.get(reverse("panel:reservas"))
        lista, page = r.context["lista"], r.context["page"]
        self.assertEqual(len(lista), 10)
        self.assertEqual(page.paginator.num_pages, N // 10)
        r2, t = medir(lambda: self.adm.get(reverse("panel:reservas"), {"page": page.paginator.num_pages}))
        self.assertEqual(len(r2.context["lista"]), 10)
        self.obt(f"Con {N} reservas la lista muestra {len(lista)} por página en {page.paginator.num_pages} páginas; "
                 f"abrir la última página tardó {ms(t)}.")

    def test_R04_consultas_sql_constantes(self):
        self.muchas_reservas(20)
        with CaptureQueriesContext(connection) as pocas:
            self.adm.get(reverse("panel:reservas"))
        Reserva.objects.all().delete()
        Cliente.objects.all().delete()
        self.muchas_reservas(N)
        with CaptureQueriesContext(connection) as muchas:
            self.adm.get(reverse("panel:reservas"))
        q1, q2 = len(pocas.captured_queries), len(muchas.captured_queries)
        self.assertLessEqual(q2, q1 + 3, f"La lista hizo {q1} consultas con 20 reservas y {q2} con {N}: crecen con la cantidad de datos")
        self.obt(f"La lista de reservas hizo {q1} consultas SQL con 20 reservas y {q2} con {N}: la cantidad no crece con los datos.")

    def test_R05_api_disponibilidad_con_volumen(self):
        self.muchas_reservas(N, inicio=d(1))
        r, t = medir(lambda: self.client.get(reverse("api_disponibilidad")))
        n = len(r.json()["ocupadas"])
        self.assertEqual(n, N)
        self.assertLess(t, MAX_API, f"La API tardó {ms(t)}")
        self.obt(f"La API de disponibilidad devolvió {n} rangos ocupados en {ms(t)} (máximo {MAX_API:.0f} s).")

    def test_R06_api_grafico_con_volumen(self):
        self.muchas_reservas(N)
        r1, t1 = medir(lambda: self.adm.get(reverse("panel:api_ocupacion"), {"anio": H.year}))
        r2, t2 = medir(lambda: self.adm.get(reverse("panel:api_ocupacion"), {"modo": "anios"}))
        self.assertEqual((r1.status_code, r2.status_code), (200, 200))
        self.assertLess(max(t1, t2), MAX_API)
        self.obt(f"Con {N} reservas, el gráfico por meses respondió en {ms(t1)} y por años en {ms(t2)} "
                 f"({len(r2.json()['labels'])} años). Ambos bajo {MAX_API:.0f} s.")

    def test_R07_reporte_pdf_con_volumen(self):
        self.muchas_reservas(N)
        tiempos = {}
        for tipo in ("ocupacion", "reservas", "ingresos", "clientes"):
            r, t = medir(lambda: self.adm.get(reverse("panel:reporte_pdf"), {"tipo": tipo}))
            self.assertEqual(r["Content-Type"], "application/pdf")
            self.assertLess(t, MAX_PDF, f"El PDF de {tipo} tardó {ms(t)}")
            tiempos[tipo] = (t, len(r.content))
        self.obt(f"Con {N} reservas, los PDF se generaron en: " +
                 ", ".join(f"{k} {ms(t)} ({b // 1024} KB)" for k, (t, b) in tiempos.items()) + f". Todos bajo {MAX_PDF:.0f} s.")

    def test_R08_envio_de_solicitud(self):
        self.ingresar()
        r, t = medir(lambda: self.solicitar(d(6), d(8)))
        self.assertEqual(r.status_code, 302)
        self.assertLess(t, MAX_PUBLICA)
        self.obt(f"La solicitud de reserva (validación, guardado y aviso por correo) se procesó en {ms(t)}.")

    def test_R09_peso_de_imagenes(self):
        carpeta = Path(settings.BASE_DIR) / "static" / "img"
        imgs = sorted((p for p in carpeta.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")),
                      key=lambda p: p.stat().st_size, reverse=True)
        pesadas = [f"{p.name} ({p.stat().st_size / 1024 / 1024:.1f} MB)" for p in imgs if p.stat().st_size > MAX_IMAGEN]
        total = sum(p.stat().st_size for p in imgs) / 1024 / 1024
        self.assertFalse(pesadas, f"Imágenes sobre 1 MB: {', '.join(pesadas)}. Conviene comprimirlas o pasarlas a .jpg/.webp")
        self.obt(f"Las {len(imgs)} imágenes pesan en total {total:.1f} MB; la más grande es {imgs[0].name} "
                 f"({imgs[0].stat().st_size / 1024:.0f} KB). Ninguna supera 1 MB.")

    def test_R10_carga_en_navegador(self):
        self.manual("medir con Lighthouse (F12 → Lighthouse) el puntaje de rendimiento y el tiempo de carga de Inicio y Servicios, "
                    "en computador y en modo móvil.")

    def test_R11_consulta_de_configuracion_una_vez_por_pagina(self):
        cantidades = {}
        for nombre in ("inicio", "contacto", "servicios"):
            with CaptureQueriesContext(connection) as q:
                self.client.get(reverse(nombre))
            cantidades[nombre] = sum('"configuracion"' in c["sql"] for c in q.captured_queries)
            self.assertEqual(cantidades[nombre], 1, f"{nombre} consultó la configuración {cantidades[nombre]} veces")
        self.obt("Leer los datos de contacto editables agrega una sola consulta SQL (por clave primaria, tabla de 4 filas) en cada página: "
                 + ", ".join(f"{k} {v}" for k, v in cantidades.items()) + ".")
