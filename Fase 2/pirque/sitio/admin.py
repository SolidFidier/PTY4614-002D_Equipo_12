from django.contrib import admin
from .models import Mensaje, Habitacion, Reserva

@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ("nombre", "correo", "creado", "leido")
    list_filter = ("leido",)

@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden")

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("llegada", "salida", "adultos", "ninos", "creado")
