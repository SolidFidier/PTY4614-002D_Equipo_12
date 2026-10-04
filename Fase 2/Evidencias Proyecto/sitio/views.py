from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import MensajeForm, ReservaForm
from .models import Habitacion

HORARIO = [
    ("Lun", "Cerrado"),
    ("Mar", "13:00 – 16:00 / 20:00 – 24:00"),
    ("Mié", "13:00 – 16:00 / 20:00 – 24:00"),
    ("Jue", "13:00 – 16:00 / 20:00 – 24:00"),
    ("Vie", "13:00 – 16:00 / 20:00 – 01:00"),
    ("Sáb", "13:00 – 16:00 / 20:00 – 01:00"),
    ("Dom", "13:00 – 16:00"),
]


def inicio(request):
    return render(request, "sitio/inicio.html")


def habitaciones(request):
    return render(request, "sitio/habitaciones.html",
                  {"habitaciones": Habitacion.objects.all(), "horario": HORARIO})


def servicios(request):
    return render(request, "sitio/servicios.html", {"horario": HORARIO})


def quienes_somos(request):
    return render(request, "sitio/quienes_somos.html")


def como_llegar(request):
    return render(request, "sitio/como_llegar.html")


def reservar(request):
    form = ReservaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Recibimos tu solicitud. Te contactaremos para confirmar la reserva.")
        return redirect("reservar")
    return render(request, "sitio/reservar.html", {"form": form})


def contacto(request):
    form = MensajeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mensaje enviado. Te responderemos pronto.")
        return redirect("contacto")
    return render(request, "sitio/contacto.html", {"form": form})
