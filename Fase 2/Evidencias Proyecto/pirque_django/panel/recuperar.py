"""
Recuperación de contraseña del panel de administración (H15).

Usa las vistas de Django (django.contrib.auth.views) con plantillas propias del panel.
- Solo envía el enlace a cuentas activas del personal (is_staff), no a otros usuarios.
- El mensaje de "Revisa tu correo" es el mismo exista o no el correo, para no revelar qué cuentas existen.
- El enlace vale 1 hora (PASSWORD_RESET_TIMEOUT en settings.py) y sirve una sola vez.

Se activa en panel/urls.py (*urls_recuperar). El correo usa la misma configuración de correo del proyecto (EMAIL_BACKEND).
"""
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.urls import path, reverse_lazy


class RecuperarForm(PasswordResetForm):
    """Igual que el formulario de Django, pero solo para cuentas del personal del panel."""

    def get_users(self, email):
        return (u for u in super().get_users(email) if u.is_staff)


urls_recuperar = [
    path(
        "recuperar/",
        auth_views.PasswordResetView.as_view(
            form_class=RecuperarForm,
            template_name="panel/recuperar.html",
            email_template_name="panel/correo_recuperar.txt",
            subject_template_name="panel/asunto_recuperar.txt",
            success_url=reverse_lazy("panel:recuperar_enviado"),
        ),
        name="recuperar",
    ),
    path(
        "recuperar/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="panel/recuperar_enviado.html"),
        name="recuperar_enviado",
    ),
    path(
        "recuperar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="panel/recuperar_nueva.html",
            success_url=reverse_lazy("panel:recuperar_listo"),
        ),
        name="recuperar_confirmar",
    ),
    path(
        "recuperar/listo/",
        auth_views.PasswordResetCompleteView.as_view(template_name="panel/recuperar_listo.html"),
        name="recuperar_listo",
    ),
]
