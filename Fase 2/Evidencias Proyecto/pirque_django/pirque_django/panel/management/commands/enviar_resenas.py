from django.core.management.base import BaseCommand
from panel.servicios import solicitar_resenas

class Command(BaseCommand):
    help = ("Envía por correo la invitación a dejar una reseña a los huéspedes cuya estadía ya terminó. "
            "Programa este comando una vez al día (Programador de tareas de Windows o cron).")

    def handle(self, *a, **o):
        enviados, fallidos = solicitar_resenas()
        self.stdout.write(self.style.SUCCESS(f"Invitaciones enviadas: {enviados}") + (f" · con error: {fallidos}" if fallidos else ""))
