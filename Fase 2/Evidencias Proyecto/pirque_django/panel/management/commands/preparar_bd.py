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
                      "AND table_name IN ('clientes', 'reservas', 'mensajes', 'resenas') ORDER BY 1")
            self.stdout.write("Tablas del hospedaje: " + ", ".join(r[0] for r in c.fetchall()))
        self.stdout.write(self.style.SUCCESS("Base de datos lista. Siguiente: python manage.py migrate"))
