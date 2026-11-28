"""Respaldo de la base de datos (riesgo R03: pérdida de datos de reservas y clientes).

Uso:  python manage.py respaldar_bd                 (guarda en RESPALDOS_DIR y conserva los últimos RESPALDOS_CONSERVAR)
      python manage.py respaldar_bd --carpeta D:\\respaldos --conservar 30
Prográmalo una vez al día (Programador de tareas de Windows o cron). Para restaurar un respaldo:
      pg_restore --clean --if-exists -d hospedaje_pirque_bd -U postgres archivo.dump
"""
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

PREFIJO = "hospedaje_pirque_"


class Command(BaseCommand):
    help = "Guarda un respaldo completo de la base de datos (pg_dump) y borra los respaldos más antiguos."

    def add_arguments(self, parser):
        parser.add_argument("--carpeta", help="Carpeta donde guardar el respaldo (por defecto RESPALDOS_DIR de settings.py).")
        parser.add_argument("--conservar", type=int, help="Cuántos respaldos guardar (por defecto RESPALDOS_CONSERVAR).")

    def handle(self, *a, **o):
        carpeta = Path(o["carpeta"] or settings.RESPALDOS_DIR)
        conservar = o["conservar"] or settings.RESPALDOS_CONSERVAR
        if conservar < 1:
            raise CommandError("--conservar debe ser 1 o más.")
        pg_dump = shutil.which(settings.PG_DUMP) or (settings.PG_DUMP if Path(settings.PG_DUMP).is_file() else None)
        if not pg_dump:
            raise CommandError(f"No se encontró pg_dump ({settings.PG_DUMP}). Instala las herramientas de PostgreSQL o define PG_DUMP "
                               "con la ruta completa, por ejemplo C:\\Program Files\\PostgreSQL\\16\\bin\\pg_dump.exe")
        carpeta.mkdir(parents=True, exist_ok=True)
        bd = connection.settings_dict
        destino = carpeta / f"{PREFIJO}{datetime.now():%Y%m%d_%H%M%S}.dump"
        comando = [pg_dump, "--format=custom", "--no-owner", f"--file={destino}", f"--host={bd.get('HOST') or 'localhost'}",
                   f"--port={bd.get('PORT') or '5432'}", f"--username={bd.get('USER') or 'postgres'}", bd["NAME"]]
        entorno = {**os.environ, "PGPASSWORD": bd.get("PASSWORD") or ""}   # la clave no queda visible en la lista de procesos
        r = subprocess.run(comando, env=entorno, capture_output=True, text=True)
        if r.returncode != 0:
            destino.unlink(missing_ok=True)
            raise CommandError(f"pg_dump falló: {r.stderr.strip() or r.returncode}")
        self.stdout.write(self.style.SUCCESS(f"Respaldo guardado: {destino} ({destino.stat().st_size / 1024:.0f} KB)"))
        antiguos = sorted(carpeta.glob(f"{PREFIJO}*.dump"))[:-conservar]
        for viejo in antiguos:
            viejo.unlink()
        if antiguos:
            self.stdout.write(f"Se borraron {len(antiguos)} respaldo(s) antiguo(s); quedan los últimos {conservar}.")
