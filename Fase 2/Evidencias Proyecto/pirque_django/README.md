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
Avisos a administradores: el correo del hospedaje (Configuraciones avanzadas) o, si se define `NOTIFICAR_A` en el servidor, esas direcciones, + usuarios del Django Admin con «Es staff» y correo.

## Datos del hospedaje y personalización
- **Teléfono, WhatsApp, correo e Instagram:** se cambian desde el panel → *Configuraciones avanzadas* → «Datos de contacto del sitio». Se guardan en la tabla `configuracion`
  (la crea `python manage.py preparar_bd`) y se ven al instante en el pie de página, la pantalla Contacto, los botones de WhatsApp y los correos a los clientes.
  Los avisos de mensajes y solicitudes nuevas llegan al correo configurado (salvo que se defina `NOTIFICAR_A` en el servidor).
  Si no se ha guardado nada, se usan los valores originales de `SITIO` en `config/settings.py`; el botón «Volver a los datos originales» borra lo guardado.
  El WhatsApp se guarda solo con números y código de país (ej. 56997710934); un móvil chileno de 9 dígitos recibe el 56 automáticamente.
- Nombre y dirección: `SITIO` en `config/settings.py`.
- Horario: `HORAS` en `sitio/views.py`. Carrusel de Servicios: cualquier imagen de `static/img/` con «carrusel» en el nombre.
- Idiomas: textos en las plantillas (`{% t "es" "en" "pt" %}` de `sitio/templatetags/idioma_tags.py`) y `L(es, en, pt)` en Python. El panel siempre está en español.
- Si aparece «403 CSRF»: el proyecto usa cookies propias (`pirque_csrftoken`, `pirque_sessionid`, `pirque_idioma`); recarga la página (F5) y reintenta.


# Cambios al sistema registrados

- Se cambia el formato de la imagen "banoarenavolcanica.png" a .jpg
- Se corrige la locacion del mapa de la pantalla "Como llegar", ahora si muestra el punto exacto del hospedaje
- Se corrige el numero de whatsapp y el correo de settings.py, antes estaban contactos personales para hacer pruebas
- Configuraciones avanzadas del panel: ahora permite cambiar teléfono, WhatsApp, correo e Instagram (tabla nueva `configuracion`; ejecutar `python manage.py preparar_bd`). Los cambios se reflejan en el sitio público, en los enlaces de WhatsApp y en los correos
- Pruebas: nuevas P81 a P93, S16 a S18 y R11; las pruebas P36, P37 y P38 ahora leen el número vigente en lugar de settings.py; `actualizar_plan.py` agrega al Excel las filas de pruebas nuevas

Se realizaron pruebas automatizadas de funciones, seguridad, compatibilidad y rendimiento.

Se registra resultados en excel plan de pruebas
de forma automatica ejecutando `python actualizar_plan.py Plan_de_pruebas.xlsx`
(debe estar el archivo excel en la carpeta raiz del proyecto para poder actualizar el resultado obtenido
y el estado) 

# Pruebas
- Funciones: 93 pruebas (P81 a P93: configuración de datos de contacto)
- Seguridad: 18 pruebas (S16 a S18: configuración)
- Compatibilidad: 16 pruebas
- Rendimiento: 11 pruebas (R11: consulta de configuración)

- Pruebas que requieren intervencion manual: 2 (P58, S15)
- Pruebas manuales: 13 (P39, P93, R10 y C7 hasta C16)
- Pruebas automatizadas: 125
- Pruebas que fallaron: 2 (R9 y C3)
- Pruebas pendientes: 3 (S15, C10, C16)

`Para poder ejecutar la prueba S15 se requiere:`

Ejecutar en la terminal:
1. `Obtener clave secreta temporal` `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
2. `Definir variables`
- $env:DJANGO_SECRET_KEY = 'la_clave_que_se_genero'
- $env:DJANGO_DEBUG = '0'
- $env:DJANGO_ALLOWED_HOSTS = '127.0.0.1,localhost'
3. `Ejecutar revision de seguridad` > `python manage.py check --deploy`

Para ejecutar pruebas automaticas insertar el siguiente script en la terminal con el entorno virtual activo
- `python manage.py test panel --testrunner=panel.test_runner.PlanRunner`

## Nota
Para probar el sitio desde un dispositivo movil
se requiere agregar al settings.py:

- Agregar al archivo: CSRF_TRUSTED_ORIGINS = ['http://direccion_IP:8000']
- Iniciar el la pagina como `python manage.py runserver 0.0.0.0:8000`

## Obtener el diagrama de clases

Para obtener el diagrama de clases se utilizo graphviz y se uso los siguientes comandos

`pip install django-extensions pydot`
`winget install graphviz` 
`dot -V`
`python manage.py graph_models panel -o modelos.png`

Y se agrego a INSTALLED_APPS en settings.py: `django_extensions`

Una vez obtenido el diagrama se le cambio el nombre a Vista logica - Diagrama de clases