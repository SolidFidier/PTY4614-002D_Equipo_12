# Hospedaje Rural Pirque (Django + Bootstrap 5)

## Puesta en marcha
```
# Crear entorno virtual

python -m venv venv

# Iniciar entorno virtual (env): venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations sitio
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Sitio: http://127.0.0.1:8000/  -  Panel: http://127.0.0.1:8000/admin/

## Imágenes (static/img/)
Las fotos de habitaciones se suben desde /admin => Habitaciones.

## Datos del hospedaje
Teléfono, correo, Instagram y dirección están en `config/settings.py` (diccionario SITIO).

## Reservas y mensajes

Las reservas y mensajes llegan al panel de administracion de django http://127.0.0.1:8000/admin/ en Mensajes y Reservas
