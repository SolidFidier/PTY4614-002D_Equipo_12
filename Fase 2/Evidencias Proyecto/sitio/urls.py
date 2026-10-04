from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("habitaciones/", views.habitaciones, name="habitaciones"),
    path("servicios/", views.servicios, name="servicios"),
    path("quienes-somos/", views.quienes_somos, name="quienes_somos"),
    path("como-llegar/", views.como_llegar, name="como_llegar"),
    path("reservar/", views.reservar, name="reservar"),
    path("contacto/", views.contacto, name="contacto"),
]
