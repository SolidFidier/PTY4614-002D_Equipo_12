"""Cancela las solicitudes que nunca se confirmaron (riesgo R08: solicitudes falsas o abandonadas).

Uso:  python manage.py expirar_solicitudes
Una solicitud PENDIENTE cuya fecha de llegada ya pasó no se va a realizar: queda «cancelada» (con una nota que lo explica)
para que no siga apareciendo como tarea pendiente. Prográmalo una vez al día junto a enviar_resenas y respaldar_bd.
"""
from django.core.management.base import BaseCommand
from django.db.models import Value
from django.db.models.functions import Concat, Left
from django.utils import timezone

from panel.models import Reserva

NOTA = "[Cancelada automáticamente: la fecha de llegada pasó sin que se confirmara la solicitud.]"


class Command(BaseCommand):
    help = "Cancela las solicitudes pendientes cuya fecha de llegada ya pasó."

    def handle(self, *a, **o):
        hoy = timezone.localdate()
        viejas = Reserva.objects.filter(estado_reserva="pendiente", fecha_entrada__lt=hoy)
        ids = list(viejas.values_list("id", flat=True))
        if ids:
            Reserva.objects.filter(id__in=ids, notas="").update(notas=NOTA)
            Reserva.objects.filter(id__in=ids).exclude(notas=NOTA).update(notas=Left(Concat("notas", Value(" " + NOTA)), 500))
            Reserva.objects.filter(id__in=ids).update(estado_reserva="cancelada", estado_pago="cancelado", vista=True)
        self.stdout.write(self.style.SUCCESS(f"Solicitudes vencidas canceladas: {len(ids)}" + (f" ({', '.join(f'#{i}' for i in ids)})" if ids else "")))
