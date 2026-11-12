import re
from django import forms
from django.utils import timezone
from panel.models import Cliente, Reserva
from .idioma import L, L_lazy


class MensajeForm(forms.Form):
    nombre = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre y apellido"}))
    correo = forms.EmailField(max_length=100, widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo"}))
    mensaje = forms.CharField(max_length=1000, widget=forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Mensaje"}))


class ReservaForm(forms.Form):
    """Solicitud de estadía: fechas y cantidad de personas (servicio exclusivo: sin habitaciones ni precios)."""
    llegada = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    salida = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    adultos = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": 1}))
    ninos = forms.IntegerField(min_value=0, initial=0, required=False, widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": 0}))

    def clean_ninos(self):
        return self.cleaned_data.get("ninos") or 0

    def clean(self):
        d = super().clean()
        e, s = d.get("llegada"), d.get("salida")
        if not (e and s):
            raise forms.ValidationError(L("Selecciona las fechas de llegada y salida.", "Please select your check-in and check-out dates.", "Selecione as datas de chegada e saída."))
        if e < timezone.localdate():
            raise forms.ValidationError(L("La fecha de llegada no puede ser pasada.", "The check-in date cannot be in the past.", "A data de chegada não pode ser passada."))
        if s <= e:
            raise forms.ValidationError(L("La fecha de salida debe ser posterior a la de llegada.", "The check-out date must be after check-in.", "A data de saída deve ser posterior à de chegada."))
        if Reserva.objects.filter(estado_reserva="aceptada", fecha_entrada__lt=s, fecha_salida__gt=e).exists():
            raise forms.ValidationError(L("Esas fechas ya están ocupadas. Elige otras (las fechas ocupadas se ven en rojo).",
                                          "Those dates are already taken. Please choose others (taken dates are shown in red).",
                                          "Essas datas já estão ocupadas. Escolha outras (as datas ocupadas aparecem em vermelho)."))
        return d


def _clase(extra=""):
    return {"class": ("form-control bg-dark text-light border-secondary " + extra).strip()}


def _obligatorio():
    return {"required": L_lazy("Campo obligatorio", "Required", "Obrigatório")}


# Formulario de Identificación con validación real de RUT y Teléfono
class ClienteLoginForm(forms.Form):
    nombre = forms.CharField(max_length=100, label=L_lazy("Nombre", "First name", "Nome"), error_messages=_obligatorio(),
        widget=forms.TextInput(attrs={**_clase(), "placeholder": "Ej: Juan"}))
    apellido = forms.CharField(max_length=100, label=L_lazy("Apellido", "Last name", "Sobrenome"), error_messages=_obligatorio(),
        widget=forms.TextInput(attrs={**_clase(), "placeholder": "Ej: Pérez"}))
    correo = forms.EmailField(max_length=100, label=L_lazy("Correo", "Email", "E-mail"),
        error_messages={**_obligatorio(), "invalid": L_lazy("Correo electrónico inválido", "Invalid email", "E-mail inválido")},
        widget=forms.EmailInput(attrs={**_clase(), "placeholder": "ejemplo@correo.com"}))
    extranjero = forms.BooleanField(required=False,
        label=L_lazy("Soy extranjero (uso pasaporte/DNI)", "I'm a foreigner (I use a passport/ID)", "Sou estrangeiro (uso passaporte/documento)"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input ms-1"}))
    # Solo números (y K final) para RUT; letras y números si es extranjero. js/sitio.js filtra lo que se escribe.
    rut = forms.CharField(max_length=25, label=L_lazy("RUT / Documento", "RUT / ID number", "RUT / Documento"), error_messages=_obligatorio(),
        widget=forms.TextInput(attrs={**_clase(), "placeholder": "123456785", "autocomplete": "off", "maxlength": "9"}))
    telefono = forms.CharField(max_length=25, label=L_lazy("Teléfono", "Phone", "Telefone"), error_messages=_obligatorio(),
        widget=forms.TextInput(attrs={**_clase(), "placeholder": "56912345678", "inputmode": "numeric", "autocomplete": "tel", "maxlength": "15"}))

    # RUT / DNI. Para chilenos se acepta CUALQUIER RUT de 8 o 9 caracteres (números y, solo al final, una K):
    # el dígito verificador (módulo 11) NO bloquea, porque hay RUT reales o de prueba que no lo cumplen.
    # Con «Soy extranjero» se acepta cualquier pasaporte/DNI alfanumérico.
    def clean_rut(self):
        doc = re.sub(r"[.\-\s]", "", self.cleaned_data.get("rut", "").upper())
        if not doc:
            raise forms.ValidationError(L("Ingresa tu documento.", "Enter your ID number.", "Informe seu documento."))
        if self.cleaned_data.get("extranjero"):
            if not re.fullmatch(r"[0-9A-Z]{4,20}", doc):
                raise forms.ValidationError(L("El documento solo puede tener letras y números (4 a 20 caracteres).",
                                              "The ID can only contain letters and numbers (4 to 20 characters).",
                                              "O documento só pode ter letras e números (4 a 20 caracteres)."))
            return doc
        if not re.fullmatch(r"\d{7,8}[\dK]", doc):
            raise forms.ValidationError(L(
                "Ingresa tu RUT con 8 o 9 caracteres (solo números; la K solo al final) o marca «Soy extranjero».",
                "Enter your RUT with 8 or 9 characters (digits only; K only at the end) or tick “I'm a foreigner”.",
                "Informe seu RUT com 8 ou 9 caracteres (somente números; K só no final) ou marque «Sou estrangeiro»."))
        return doc

    # Teléfono: solo números (se descartan +, espacios y guiones)
    def clean_telefono(self):
        limpio = re.sub(r"\D", "", self.cleaned_data.get("telefono", ""))
        if not 8 <= len(limpio) <= 15:
            raise forms.ValidationError(L("Ingrese un número de teléfono válido, solo números (ej: 56912345678).",
                                          "Enter a valid phone number, digits only (e.g. 56912345678).",
                                          "Informe um número de telefone válido, somente números (ex.: 56912345678)."))
        return limpio
