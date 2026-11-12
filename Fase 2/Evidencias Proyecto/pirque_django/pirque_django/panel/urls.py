from django.urls import path
from . import views as v
app_name = "panel"
urlpatterns = [
    path("login/", v.login_view, name="login"),
    path("logout/", v.logout_view, name="logout"),
    path("", v.inicio, name="inicio"),
    path("api/ocupacion/", v.api_ocupacion, name="api_ocupacion"),
    path("api/mensajes/pendientes/", v.api_pendientes, name="api_pendientes"),
    path("mensajes/", v.mensajes, name="mensajes"),
    path("api/mensajes/<int:pk>/toggle/", v.mensaje_toggle, name="mensaje_toggle"),
    # Reservas: todas y por tipo
    path("reservas/", v.reservas, {"seccion": "todas"}, name="reservas"),
    path("reservas/pendientes/", v.reservas, {"seccion": "pendientes"}, name="reservas_pendientes"),
    path("reservas/aceptadas/", v.reservas, {"seccion": "aceptadas"}, name="reservas_aceptadas"),
    path("reservas/terminadas/", v.reservas, {"seccion": "terminadas"}, name="reservas_terminadas"),
    path("reservas/canceladas/", v.reservas, {"seccion": "canceladas"}, name="reservas_canceladas"),
    path("api/reservas/crear/", v.reserva_crear, name="reserva_crear"),
    path("api/reservas/<int:pk>/editar/", v.reserva_editar, name="reserva_editar"),
    path("api/reservas/<int:pk>/aceptar/", v.reserva_aceptar, name="reserva_aceptar"),
    path("api/reservas/<int:pk>/vista/", v.reserva_vista, name="reserva_vista"),
    path("api/reservas/<int:pk>/eliminar/", v.reserva_eliminar, name="reserva_eliminar"),
    path("api/reservas/<int:pk>/resena/", v.reserva_resena, name="reserva_resena"),
    path("api/ocupadas/", v.api_ocupadas, name="api_ocupadas"),
    path("clientes/", v.clientes, name="clientes"),
    path("api/clientes/<str:pk>/editar/", v.cliente_editar, name="cliente_editar"),
    path("api/clientes/<str:pk>/eliminar/", v.cliente_eliminar, name="cliente_eliminar"),
    # Reseñas
    path("resenas/", v.resenas, name="resenas"),
    path("api/resenas/<int:pk>/visible/", v.resena_visible, name="resena_visible"),
    path("api/resenas/<int:pk>/eliminar/", v.resena_eliminar, name="resena_eliminar"),
    path("api/resenas/enviar/", v.resenas_enviar, name="resenas_enviar"),
    path("reportes/", v.reportes, name="reportes"),
    path("reportes/pdf/", v.reporte_pdf, name="reporte_pdf"),
    path("ayuda/", v.ayuda, name="ayuda"),
    path("configuracion/", v.configuracion, name="configuracion"),
]
