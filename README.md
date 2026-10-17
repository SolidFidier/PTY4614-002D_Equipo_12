# PTY4614-002D_Equipo_12
Repositorio del equipo n°12 de la asignatura Capstone 002D



# Reservas HRP
#Descripción
Aplicación web con sistema automatizado de reservas y agendamiento para el Hospedaje Rural Pirque, ubicado en Parque Real 8 b, Pirque, Región Metropolitana, Chile.

El proyecto busca resolver los problemas de gestión manual de reservas y un sitio web poco confiable, que generan pérdida de clientes potenciales, errores en reservas, falta de seguimiento y una imagen poco profesional.

Este proyecto va dirigo a los administradores del hospedaje y a turistas interesados en hospedaje temporal en la zona (nacionales e internacionales).

# Tecnologías a utilizar
Lenguajes*: Python, HTML, JavaScript, y CSS

Frameworks: Django y Bootstrap

Base de datos: Postgresql


# Puesta en marcha
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

# Integrantes y roles

José Varela | Representante del cliente/ Tracker

Ezequel Lorca | Programador

Martín Ponce | Programador


# Metodología
La metodología a utilizar es una híbrida, Extreme Programming como metodo de desarrollo y enfoque mientras se realiza las entregas de manera Incremental.

# Arquitectura de la solución
Al utilizar Django la arquitectura que utiliza nuestra solución de software es una estructura MVT o Modelo Vista Plantilla (Template), donde el Modelo se encarga de manejar la estructura y interacción de los datos dentro de la aplicación, el componente de Vista procesa las solicitudes del usuario y devolver respuestas, siendo el intermediario entre el Modelo y la Plantilla, y finalmente la Plantilla renderiza la salida HTML, o la vista real que ve el usuario de la pagina.
