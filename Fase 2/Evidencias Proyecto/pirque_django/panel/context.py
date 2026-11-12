from .models import Mensaje, Reserva

def pendientes(request):
    """Contadores de las burbujas del menú lateral: {{ mensajes_pendientes }} y {{ reservas_pendientes }}."""
    if not request.path.startswith("/panel/") or not request.user.is_authenticated:
        return {}
    return {"mensajes_pendientes": Mensaje.objects.filter(fecha_gestion__isnull=True).count(),
            "reservas_pendientes": Reserva.objects.filter(estado_reserva="pendiente").count()}
