"""Modelos NO administrados por Django (managed=False): usan las tablas existentes de PostgreSQL
(se crean con base_de_datos/hospedaje_pirque_bd.sql y se actualizan con `python manage.py preparar_bd`)."""
from datetime import timezone as _tz
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


class FechaHoraUTC(models.DateTimeField):
    """Columna `timestamp without time zone` que Django escribe en UTC.
    PostgreSQL la devuelve sin zona horaria; aquí se marca como UTC para poder compararla y mostrarla
    junto a las columnas `timestamptz` (evita «can't compare offset-naive and offset-aware datetimes»)."""
    def from_db_value(self, value, expression, connection):
        return value.replace(tzinfo=_tz.utc) if value is not None and value.tzinfo is None else value


ESTADOS_RESERVA = [("pendiente", "Pendiente"), ("aceptada", "Aceptada"), ("cancelada", "Cancelada")]
ESTADOS_PAGO = [("pendiente", "Pendiente"), ("abonado", "Abonado"), ("pagado", "Pagado"), ("cancelado", "Cancelado")]


class Cliente(models.Model):
    id = models.CharField(db_column="ID_cliente", primary_key=True, max_length=20)  # RUT/DNI limpio
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    nacionalidad = models.CharField(max_length=50)
    telefono = models.CharField(max_length=100)
    correo = models.CharField(max_length=100)
    class Meta: managed = False; db_table = "clientes"
    def __str__(self): return f"{self.nombre} {self.apellido} ({self.id})"


class Reserva(models.Model):
    """Servicio exclusivo: la reserva es del grupo completo (no hay habitaciones)."""
    id = models.AutoField(db_column="ID_reserva", primary_key=True)
    cliente = models.ForeignKey(Cliente, models.DO_NOTHING, db_column="FK_cliente", db_constraint=False)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    correo = models.CharField(max_length=100)
    telefono = models.CharField(max_length=100)
    cant_adultos = models.IntegerField(default=1)
    cant_ninos = models.IntegerField(null=True, default=0)
    fecha_entrada = models.DateField()
    fecha_salida = models.DateField()
    monto = models.IntegerField(default=0)                      # valor de la estadía, ingresado manualmente
    estado_reserva = models.CharField(max_length=15, default="pendiente")
    estado_pago = models.CharField(max_length=15, default="pendiente")
    notas = models.CharField(max_length=500, blank=True, default="")
    vista = models.BooleanField(default=False)                   # False = solicitud nueva aún sin revisar (se destaca)
    idioma = models.CharField(max_length=2, default="es")
    fecha_reserva = FechaHoraUTC(default=timezone.now)
    class Meta: managed = False; db_table = "reservas"
    def __str__(self): return f"#{self.id} {self.nombre} {self.apellido}"
    @property
    def personas(self): return self.cant_adultos + (self.cant_ninos or 0)
    @property
    def noches(self): return (self.fecha_salida - self.fecha_entrada).days
    @property
    def terminada(self):  # estadía aceptada cuya salida ya pasó
        return self.estado_reserva == "aceptada" and self.fecha_salida < timezone.localdate()
    @property
    def seccion(self):    # pendiente | aceptada | terminada | cancelada
        return "terminada" if self.terminada else self.estado_reserva


class Mensaje(models.Model):
    id = models.AutoField(db_column="ID_mensaje", primary_key=True)
    nombre = models.CharField(max_length=100)
    correo = models.CharField(max_length=100)
    contenido = models.CharField(max_length=1000)
    fecha_envio = models.DateTimeField()
    fecha_gestion = FechaHoraUTC(null=True)
    admin_id = models.IntegerField(db_column="FK_admin", null=True)
    class Meta: managed = False; db_table = "mensajes"
    @property
    def codigo(self): return f"MSG-{self.id:06d}"
    @property
    def admin_codigo(self): return f"ADM-{self.admin_id:03d}" if self.admin_id else ""
    @property
    def admin_nombre(self):
        if not self.admin_id: return ""
        return get_user_model().objects.filter(pk=self.admin_id).values_list("username", flat=True).first() or ""


class Resena(models.Model):
    """Reseña de una estadía. El enlace del correo contiene `token` y es válido solo para esa reserva (un uso)."""
    id = models.AutoField(db_column="ID_resena", primary_key=True)
    reserva = models.OneToOneField(Reserva, models.CASCADE, db_column="FK_reserva", related_name="resena")
    token = models.CharField(max_length=64, unique=True)
    fecha_solicitud = FechaHoraUTC(null=True)   # cuándo se envió el correo
    fecha_resena = FechaHoraUTC(null=True)      # cuándo respondió
    calificacion = models.SmallIntegerField(null=True)
    comentario = models.CharField(max_length=1000, blank=True, default="")
    nombre_publico = models.CharField(max_length=100, blank=True, default="")
    visible = models.BooleanField(default=False)
    class Meta: managed = False; db_table = "resenas"
    @property
    def respondida(self): return self.fecha_resena is not None
    @property
    def estrellas(self): return range(self.calificacion or 0)
    @property
    def vacias(self): return range(5 - (self.calificacion or 0))
