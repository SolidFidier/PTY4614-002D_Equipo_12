from django.urls import path
from . import views

urlpatterns = [
    # Páginas principales del sitio
    path("", views.inicio, name="inicio"),
    path("habitaciones/", views.habitaciones, name="habitaciones"),
    path("servicios/", views.servicios, name="servicios"),
    path("quienes-somos/", views.quienes_somos, name="quienes_somos"),
    path("como-llegar/", views.como_llegar, name="como_llegar"),
    path("contacto/", views.contacto, name="contacto"),
    
    # Rutas de Autenticación, Identificación y Sesión
    path("ingresar/", views.login_cliente, name="login_cliente"),
    path("salir/", views.logout_cliente, name="logout_cliente"),
    
    # Rutas de Reservas, Checkout y Simulación de Pago
    path("reservar/", views.reservar, name="reservar"),
    path("checkout/<int:reserva_id>/", views.checkout_reserva, name="checkout_reserva"),
    path("simular-pago/<int:reserva_id>/", views.simular_pago, name="simular_pago"),
]