from django.db import models


class Mensaje(models.Model):
    nombre = models.CharField("Nombre y apellido", max_length=120)
    correo = models.EmailField("Correo")
    mensaje = models.TextField("Mensaje")
    creado = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.nombre} ({self.creado:%d/%m/%Y})"


class Habitacion(models.Model):
    nombre = models.CharField(max_length=80)
    imagen = models.ImageField(upload_to="habitaciones/", blank=True)
    caracteristicas = models.TextField(help_text="Una característica por línea")
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden"]
        verbose_name_plural = "habitaciones"

    def __str__(self):
        return self.nombre

    def lista(self):
        return [l.strip() for l in self.caracteristicas.splitlines() if l.strip()]


from django.db import models
from django.contrib.auth.models import User

class Reserva(models.Model):
    # Relacionamos la reserva con el usuario autenticado
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    rut = forms.CharField(max_length=12, blank=True) if False else models.CharField(max_length=12, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    
    llegada = models.DateField()
    salida = models.DateField()
    adultos = models.PositiveSmallIntegerField(default=1)
    ninos = models.PositiveSmallIntegerField("niños", default=0)
    nombre = models.CharField(max_length=120, blank=True)
    contacto = models.CharField(max_length=120, blank=True)
    estado = models.CharField(max_length=20, default='PENDIENTE')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Reserva de {self.nombre} ({self.llegada} al {self.salida})"
