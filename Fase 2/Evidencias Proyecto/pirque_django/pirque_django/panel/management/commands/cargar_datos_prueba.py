from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction

CLIENTE_MARCA = "123456785"  # primer cliente de prueba: si existe, los datos ya se cargaron
# Clientes y mensajes de PRUEBA (los de datos_prueba.sql). Nunca se tocan datos reales.
DOCS_PRUEBA = ["123456785", "234567896", "139876547", "16543210K", "AR32456789", "112223339", "176543213", "182345679", "158765438",
               "PE45678123", "193456782", "145678900", "201234565", "217654327", "134567899", "167890121", "189012349", "BR987654321", "120987658"]
CORREOS_MENSAJES = ["camila.rojas@example.com", "felipe.munoz@example.com", "daniela.soto@example.com", "javier.perez@example.com",
                    "john.miller@example.com", "marta.alvarado@example.com"]

class Command(BaseCommand):
    help = "Carga los datos de prueba de base_de_datos/datos_prueba.sql (clientes, reservas, mensajes y reseñas)."

    def add_arguments(self, parser):
        parser.add_argument("--forzar", action="store_true",
                            help="Ejecuta el archivo aunque los datos de prueba ya estén cargados (puede duplicar reservas).")
        parser.add_argument("--reiniciar", action="store_true",
                            help="Borra los datos de PRUEBA anteriores (solo los de datos_prueba.sql) y los carga de nuevo, con fechas actualizadas a hoy.")

    def handle(self, *a, **o):
        ruta = settings.BD_DIR / "datos_prueba.sql"
        if not ruta.exists(): raise CommandError(f"No existe {ruta}")
        try:
            with transaction.atomic(), connection.cursor() as c:
                if o["reiniciar"]:
                    c.execute('DELETE FROM resenas WHERE "FK_reserva" IN (SELECT "ID_reserva" FROM reservas WHERE "FK_cliente" = ANY(%s))', [DOCS_PRUEBA])
                    c.execute('DELETE FROM reservas WHERE "FK_cliente" = ANY(%s)', [DOCS_PRUEBA])
                    c.execute('DELETE FROM clientes WHERE "ID_cliente" = ANY(%s)', [DOCS_PRUEBA])
                    c.execute("DELETE FROM mensajes WHERE correo = ANY(%s)", [CORREOS_MENSAJES])
                    self.stdout.write("Datos de prueba anteriores eliminados.")
                else:
                    c.execute('SELECT count(*) FROM clientes WHERE "ID_cliente" = %s', [CLIENTE_MARCA])
                    if c.fetchone()[0] and not o["forzar"]:
                        self.stdout.write(self.style.WARNING("Los datos de prueba ya están cargados. Usa --reiniciar para borrarlos y cargarlos de nuevo."))
                        return
                c.execute(ruta.read_text(encoding="utf-8"))
                for tabla in ("clientes", "reservas", "mensajes", "resenas"):
                    c.execute(f"SELECT count(*) FROM {tabla}")
                    self.stdout.write(f"  {tabla}: {c.fetchone()[0]} filas")
            self.stdout.write(self.style.SUCCESS("Datos de prueba cargados (datos_prueba.sql)."))
        except DatabaseError as e:
            raise CommandError(
                f"No se cargaron los datos (se deshizo todo): {e}\n"
                "Si el error menciona una tabla o columna inexistente, ejecuta primero: python manage.py preparar_bd") from e
