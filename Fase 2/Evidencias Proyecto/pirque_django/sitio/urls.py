from django.urls import path
from . import views

urlpatterns = [
    # Páginas principales del sitio
    path("", views.inicio, name="inicio"),
    path("servicios/", views.servicios, name="servicios"),
    path("quienes-somos/", views.quienes_somos, name="quienes_somos"),
    path("como-llegar/", views.como_llegar, name="como_llegar"),
    path("contacto/", views.contacto, name="contacto"),

    # Identificación y sesión del cliente
    path("ingresar/", views.login_cliente, name="login_cliente"),
    path("salir/", views.logout_cliente, name="logout_cliente"),

    # Solicitud de reserva (termina en un mensaje prearmado de WhatsApp) y consulta de reservas
    path("reservar/", views.reservar, name="reservar"),
    path("mis-reservas/", views.mis_reservas, name="mis_reservas"),
    path("api/disponibilidad/", views.api_disponibilidad, name="api_disponibilidad"),

    # Reseña de la estadía (enlace personal enviado por correo)
    path("resena/<str:token>/", views.resena, name="resena"),
]
