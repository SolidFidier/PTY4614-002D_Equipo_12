from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

SCRIPTS = ("hospedaje_pirque_bd.sql", "cambios_bd.sql")

class Command(BaseCommand):
    help = ("Crea o actualiza las tablas ejecutando base_de_datos/hospedaje_pirque_bd.sql y luego cambios_bd.sql. "
            "Se puede ejecutar varias veces.")

    def handle(self, *a, **o):
        rutas = [settings.BD_DIR / nombre for nombre in SCRIPTS]
        for ruta in rutas:
            if not ruta.exists(): raise CommandError(f"No existe {ruta}")
        with transaction.atomic(), connection.cursor() as c:
            for ruta in rutas:
                c.execute(ruta.read_text(encoding="utf-8"))
                self.stdout.write(f"  ejecutado: {ruta.name}")
            c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
                      "AND table_name IN ('clientes', 'reservas', 'mensajes', 'resenas', 'configuracion') ORDER BY 1")
            self.stdout.write("Tablas del hospedaje: " + ", ".join(r[0] for r in c.fetchall()))
            c.execute("SELECT 1 FROM pg_constraint WHERE conname = 'excl_reservas_aceptadas_sin_cruce'")
            if c.fetchone():
                self.stdout.write("  Regla «un solo grupo a la vez» activa en la base de datos.")
            else:
                self.stdout.write(self.style.WARNING(
                    "  AVISO: hay reservas ACEPTADAS con fechas cruzadas, por eso la base de datos aún no impide los cruces.\n"
                    "  Corrígelas en el panel (cancela o cambia las fechas de una de ellas) y vuelve a ejecutar: python manage.py preparar_bd"))
        self.stdout.write(self.style.SUCCESS("Base de datos lista. Siguiente: python manage.py migrate"))
