import re
from django import forms
from .models import Mensaje, Reserva

class MensajeForm(forms.ModelForm):
    class Meta:
        model = Mensaje
        fields = ["nombre", "correo", "mensaje"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre y apellido"}),
            "correo": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo"}),
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Mensaje"}),
        }


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ["llegada", "salida", "adultos", "ninos"]
        widgets = {
            "llegada": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "salida": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "adultos": forms.NumberInput(attrs={"class": "form-control text-center", "min": 1}),
            "ninos": forms.NumberInput(attrs={"class": "form-control text-center", "min": 0}),
        }

    def clean(self):
        data = super().clean()
        if data.get("llegada") and data.get("salida") and data.get("salida") <= data.get("llegada"):
            raise forms.ValidationError("La fecha de salida debe ser posterior a la de llegada.")
        return data


# Formulario de Identificación con validación real de RUT y Teléfono
class ClienteLoginForm(forms.Form):
    nombre = forms.CharField(
        max_length=120, 
        error_messages={'required': 'Campo obligatorio'},
        widget=forms.TextInput(attrs={"class": "form-control bg-dark text-light border-secondary", "placeholder": "Ej: Juan Pérez"})
    )
    correo = forms.EmailField(
        error_messages={'required': 'Campo obligatorio', 'invalid': 'Ingrese un correo electrónico válido'},
        widget=forms.EmailInput(attrs={"class": "form-control bg-dark text-light border-secondary", "placeholder": "ejemplo@correo.com"})
    )
    rut = forms.CharField(
        max_length=12, 
        error_messages={'required': 'Campo obligatorio'},
        widget=forms.TextInput(attrs={"class": "form-control bg-dark text-light border-secondary", "placeholder": "12345678-9"})
    )
    telefono = forms.CharField(
        max_length=15, 
        error_messages={'required': 'Campo obligatorio'},
        widget=forms.TextInput(attrs={"class": "form-control bg-dark text-light border-secondary", "placeholder": "+56912345678"})
    )

    # Validador automático para el RUT Chileno (Módulo 11)
    def clean_rut(self):
        rut_raw = self.cleaned_data.get('rut', '').upper().replace(".", "").replace("-", "")
        if len(rut_raw) < 2:
            raise forms.ValidationError("RUT demasiado corto.")
        
        cuerpo = rut_raw[:-1]
        dv = rut_raw[-1]
        
        if not cuerpo.isdigit():
            raise forms.ValidationError("El RUT contiene caracteres inválidos.")

        # Algoritmo Módulo 11
        suma = 0
        multiplo = 2
        for r in reversed(cuerpo):
            suma += int(r) * multiplo
            multiplo += 1
            if multiplo == 8:
                multiplo = 2
                
        esperado = 11 - (suma % 11)
        if esperado == 11:
            dv_esperado = '0'
        elif esperado == 10:
            dv_esperado = 'K'
        else:
            dv_esperado = str(esperado)
            
        if dv != dv_esperado:
            raise forms.ValidationError("RUT inválido (Dígito verificador incorrecto).")
            
        return self.cleaned_data.get('rut')

    # Validador para el Teléfono (asegura que tenga números reales)
    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono', '')
        # Limpiar espacios o símbolos comunes
        tel_limpio = re.sub(r'[\s\-\+\(\)]', '', tel)
        
        if not tel_limpio.isdigit() or len(tel_limpio) < 8:
            raise forms.ValidationError("Ingrese un número de teléfono válido (ej: +56912345678).")
        return tel