# Hospedaje Rural Pirque (Django + Bootstrap 5 + PostgreSQL)
Apps: `sitio` (sitio público es/en/pt) · `panel` (administración en /panel/, español) · `config` (ajustes)

**Servicio exclusivo:** cada estadía es para un solo grupo; no hay habitaciones ni cobro en línea. El cliente solicita fechas y el
sitio lo lleva a WhatsApp con un mensaje prearmado; la administradora confirma, define el valor y gestiona el pago desde el panel.

## Puesta en marcha
1. `python -m venv venv` → `venv\Scripts\activate` → `pip install -r requirements.txt`
2. Crea la BD `hospedaje_pirque_bd` en PostgreSQL (vacía) y ajusta la clave en `config/settings.py` (o variables DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT).
3. **`python manage.py preparar_bd`** (vuelve a ejecutarlo cada vez que actualices el proyecto: agrega columnas nuevas, p. ej. `vista`) → crea las tablas (`base_de_datos/hospedaje_pirque_bd.sql`) y migra una base antigua
   (`base_de_datos/cambios_bd.sql`: conserva clientes, reservas y mensajes; elimina habitaciones, pagos y precios). Es repetible.
4. `python manage.py migrate` · `python manage.py createsuperuser` · `python manage.py runserver`
5. (Opcional) `python manage.py cargar_datos_prueba` → clientes, reservas, mensajes y reseñas de ejemplo.

Sitio: http://127.0.0.1:8000/ · Panel: /panel/login/ (correo o usuario) · Django Admin: /admin/

## Flujo de una reserva
1. El cliente se identifica (nombre, apellido, correo, RUT/DNI y teléfono) y elige fechas en el calendario (las fechas ocupadas se ven en rojo).
   El RUT acepta cualquier valor de 8 o 9 caracteres (números y K final); el dígito verificador solo genera un aviso, no bloquea. Con «Soy extranjero» se acepta cualquier pasaporte/DNI.
   El mensaje de WhatsApp incluye nombre, fechas, personas, correo y el número de solicitud (no el RUT/DNI).
2. Se crea/actualiza el **cliente** (si el RUT/DNI ya existe se actualizan sus datos) y una **reserva PENDIENTE**; los administradores reciben un correo y el cliente es enviado a WhatsApp con el mensaje armado.
3. En el panel → Reservas: las solicitudes **nuevas** se destacan hasta que se abren o se aceptan; botón **Actualizar** (y actualización automática cada 30 s); se ordena por fecha de entrada (más cercanas o más lejanas primero) o por fecha de creación (más recientes o más antiguas primero). En **Pendientes** se acepta (✓) o se edita. Al **aceptar**, el cliente recibe un correo de confirmación.
4. Estados: reserva = pendiente / aceptada / cancelada (+ *terminada* = aceptada con salida ya pasada); pago = pendiente / abonado / pagado / cancelado.
   El **valor de la estadía** lo ingresa la administradora a mano. Solo una reserva aceptada puede ocupar una fecha.
5. La **cancelación** se comunica por WhatsApp (botón en «Mis Reservas»); la administradora la registra en el panel.

## Panel pensado para uso fácil
Letra grande, botones con texto, página **Ayuda** con pasos simples, cuadro «Qué necesita tu atención hoy» y avisos claros. Las reservas SIN aceptar con fechas repetidas se advierten (recuadro amarillo) en la pantalla de Reservas.
Reportes: sin filtros muestran **todos los registros**; hay atajos «Este mes», «Últimos 3 meses», «Este año». El de Ingresos lista los IDs de las reservas aún no pagadas.

## Reseñas
Cuando una estadía aceptada termina, el huésped recibe un correo con un enlace **personal** (token único de esa reserva, un solo uso, vence a los 60 días).
Las reseñas llegan **ocultas**: en el panel → Reseñas se elige cuáles se muestran al final del inicio, o se eliminan.
Las invitaciones se envían solas al abrir el panel (como máximo cada 6 h) o con `python manage.py enviar_resenas`
(prográmalo una vez al día con el Programador de tareas de Windows o cron).

## Correos
Por defecto los correos **se imprimen en la terminal** del servidor. Para enviarlos de verdad (ejemplo Gmail, PowerShell):
```
$env:EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
$env:EMAIL_HOST_USER="tu_correo@gmail.com"
$env:EMAIL_HOST_PASSWORD="contraseña-de-aplicación"   # se crea en la cuenta de Google; no es la contraseña normal
$env:SITE_URL="https://tudominio.cl"                   # para los enlaces de los correos enviados por comando
```
Avisos a administradores: `NOTIFICAR_A` en `config/settings.py` + usuarios del Django Admin con «Es staff» y correo.

## Datos del hospedaje y personalización
- Teléfono, correo, Instagram y dirección: `SITIO` en `config/settings.py` (el WhatsApp usa `SITIO["whatsapp"]`).
- Horario: `HORAS` en `sitio/views.py`. Carrusel de Servicios: cualquier imagen de `static/img/` con «carrusel» en el nombre.
- Idiomas: textos en las plantillas (`{% t "es" "en" "pt" %}` de `sitio/templatetags/idioma_tags.py`) y `L(es, en, pt)` en Python. El panel siempre está en español.
- Si aparece «403 CSRF»: el proyecto usa cookies propias (`pirque_csrftoken`, `pirque_sessionid`, `pirque_idioma`); recarga la página (F5) y reintenta.
