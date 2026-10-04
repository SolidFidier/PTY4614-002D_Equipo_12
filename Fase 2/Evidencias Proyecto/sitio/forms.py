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
        if data.get("llegada") and data.get("salida") and data["salida"] <= data["llegada"]:
            raise forms.ValidationError("La fecha de salida debe ser posterior a la de llegada.")
        return data
