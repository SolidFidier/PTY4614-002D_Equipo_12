import json
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from .forms import MensajeForm, ReservaForm, ClienteLoginForm
from .models import Habitacion, Reserva

HORARIO = [
    ("Lun", "Cerrado"),
    ("Mar", "13:00 - 16:00 / 20:00 - 24:00"),
    ("Mié", "13:00 - 16:00 / 20:00 - 24:00"),
    ("Jue", "13:00 - 16:00 / 20:00 - 24:00"),
    ("Vie", "13:00 - 16:00 / 20:00 - 01:00"),
    ("Sáb", "13:00 - 16:00 / 20:00 - 01:00"),
    ("Dom", "13:00 - 16:00"),
]

def inicio(request):
    return render(request, "sitio/inicio.html")

def habitaciones(request):
    return render(request, "sitio/habitaciones.html", {"habitaciones": Habitacion.objects.all(), "horario": HORARIO})

def servicios(request):
    return render(request, "sitio/servicios.html", {"horario": HORARIO})

def quienes_somos(request):
    return render(request, "sitio/quienes_somos.html")

def como_llegar(request):
    return render(request, "sitio/como_llegar.html")


# --- IDENTIFICACIÓN / LOGIN DEL CLIENTE ---
def login_cliente(request):
    form = ClienteLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        nombre = form.cleaned_data['nombre']
        correo = form.cleaned_data['correo']
        rut = form.cleaned_data['rut']
        telefono = form.cleaned_data['telefono']

        user, created = User.objects.get_or_create(
            username=correo, 
            defaults={'email': correo, 'first_name': nombre}
        )
        
        login(request, user)
        
        request.session['cliente_nombre'] = nombre
        request.session['cliente_rut'] = rut
        request.session['cliente_telefono'] = telefono

        return redirect('reservar')

    return render(request, 'sitio/login_cliente.html', {'form': form})


# --- CERRAR SESIÓN ---
def logout_cliente(request):
    logout(request)
    request.session.flush()
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio')


# --- CALENDARIO DE RESERVA (OBLIGA A ESTAR LOGEADO) ---
@login_required(login_url='login_cliente')
def reservar(request):
    reservas_pagadas = Reserva.objects.filter(estado='PAGADA')
    fechas_bloqueadas = []
    
    for r in reservas_pagadas:
        dia_actual = r.llegada
        while dia_actual < r.salida:
            fechas_bloqueadas.append(dia_actual.strftime("%Y-%m-%d"))
            dia_actual += timedelta(days=1)

    form = ReservaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reserva = form.save(commit=False)
        reserva.usuario = request.user
        reserva.nombre = request.session.get('cliente_nombre', request.user.first_name)
        reserva.contacto = f"RUT: {request.session.get('cliente_rut', '')} | Tel: {request.session.get('cliente_telefono', '')}"
        reserva.estado = 'PENDIENTE'
        reserva.save()
        
        return redirect("checkout_reserva", reserva_id=reserva.id)
        
    context = {
        "form": form,
        "fechas_bloqueadas_json": json.dumps(fechas_bloqueadas)
    }
    return render(request, "sitio/reservar.html", context)


# --- CHECKOUT / PAGO TIPO AIRBNB ---
@login_required(login_url='login_cliente')
def checkout_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    precio_noche = 25000
    noches = (reserva.salida - reserva.llegada).days
    if noches < 1:
        noches = 1
    total_clp = noches * precio_noche

    context = {
        "reserva": reserva,
        "noches": noches,
        "precio_noche": precio_noche,
        "total_clp": total_clp,
    }
    return render(request, "sitio/checkout.html", context)


# --- SIMULAR PAGO EXITOSO Y BLOQUEAR DÍAS ---
@login_required(login_url='login_cliente')
def simular_pago(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    reserva.estado = 'PAGADA'
    reserva.save()
    
    messages.success(request, "¡Pago confirmado con éxito! Tu estadía ha quedado reservada.")
    return redirect("reservar")


def contacto(request):
    form = MensajeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mensaje enviado. Te responderemos pronto.")
        return redirect("contacto")
    return render(request, "sitio/contacto.html", {"form": form})