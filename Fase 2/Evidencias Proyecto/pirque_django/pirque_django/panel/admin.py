from django.contrib import admin
from .models import Cliente, Reserva, Mensaje, Resena
for m in (Cliente, Reserva, Mensaje, Resena): admin.site.register(m)
