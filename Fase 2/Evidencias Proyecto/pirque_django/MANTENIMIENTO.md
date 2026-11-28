# Manual técnico y de mantenimiento — Hospedaje Rural Pirque

Este documento es para quien mantenga el sistema después del Capstone (riesgo R09). Explica cómo publicarlo, qué revisar
cada día y cada mes, cómo respaldar y restaurar la base de datos y qué hacer ante un incidente.
La administradora no necesita leerlo: para ella está la página **Ayuda** del panel.

## 1. Publicar el sitio (servidor de producción)

Variables de entorno que se deben definir en el servidor (nunca en el código ni en GitHub):

| Variable | Para qué | Ejemplo |
|---|---|---|
| `DJANGO_DEBUG` | Siempre `0` en producción | `0` |
| `DJANGO_SECRET_KEY` | Clave secreta larga y aleatoria | generar con `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"` |
| `DJANGO_ALLOWED_HOSTS` | Dominios del sitio | `hospedajepirque.cl,www.hospedajepirque.cl` |
| `DJANGO_HTTPS` | `1` cuando el dominio tenga certificado (redirige a https, cookies seguras, HSTS) | `1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Dirección completa del sitio (necesaria con https) | `https://hospedajepirque.cl` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Base de datos PostgreSQL | |
| `EMAIL_BACKEND`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Envío real de correos (ver README) | |
| `SITE_URL` | Dirección pública, para los enlaces de los correos enviados por comando | `https://hospedajepirque.cl` |
| `DJANGO_LOG_SEGURIDAD` | (Opcional) archivo donde guardar el registro de seguridad | `/var/log/pirque/seguridad.log` |
| `RESPALDOS_DIR`, `RESPALDOS_CONSERVAR`, `PG_DUMP` | Respaldos (sección 3) | |

Comprobación antes de publicar: `python manage.py check --deploy`. Si falta algo, el sistema muestra avisos `pirque.W001`
(clave de ejemplo), `pirque.W002` (sin https) o `pirque.W003` (ALLOWED_HOSTS con `*`) al iniciar.

Pasos de cada publicación o actualización:
1. `pip install -r requirements.txt`
2. `python manage.py preparar_bd` (crea o actualiza las tablas; se puede repetir). Si muestra el aviso de «reservas ACEPTADAS
   con fechas cruzadas», corrígelas en el panel y vuelve a ejecutarlo para activar la regla de un solo grupo a la vez en la base de datos.
3. `python manage.py migrate`
4. `python manage.py collectstatic --noinput`
5. Reiniciar el servidor de la aplicación.

Recomendación: dejar el hosting, el dominio y la base de datos **a nombre del hospedaje**, con las credenciales guardadas
por la administradora.

## 2. Tareas programadas (una vez al día)

Programarlas con el Programador de tareas de Windows o con cron (por ejemplo a las 03:00):

```
python manage.py respaldar_bd          # respaldo de la base de datos (riesgo R03)
python manage.py enviar_resenas        # invitaciones de reseña a estadías terminadas
python manage.py expirar_solicitudes   # cancela solicitudes pendientes cuya fecha de llegada ya pasó (riesgo R08)
```

## 3. Respaldos de la base de datos

- `python manage.py respaldar_bd` crea `hospedaje_pirque_AAAAMMDD_HHMMSS.dump` (formato de `pg_dump`) en `RESPALDOS_DIR`
  y conserva los últimos `RESPALDOS_CONSERVAR` (14 por defecto). La carpeta por defecto es `respaldos_hospedaje_pirque` en la
  carpeta del usuario, **fuera del proyecto**, para que los datos personales nunca se suban a GitHub.
- Lo ideal es que `RESPALDOS_DIR` sea una carpeta sincronizada con la nube (Google Drive / OneDrive) o un disco externo:
  así hay una copia fuera del servidor.
- En Windows, si `pg_dump` no está en el PATH: `PG_DUMP=C:\Program Files\PostgreSQL\16\bin\pg_dump.exe`.

**Restaurar** (probarlo una vez al mes en una base de prueba):
```
createdb -U postgres hospedaje_pirque_prueba
pg_restore --clean --if-exists --no-owner -U postgres -d hospedaje_pirque_prueba hospedaje_pirque_20261126_030000.dump
```
Si hay que restaurar la base real: detener el sitio, restaurar sobre `hospedaje_pirque_bd` y revisar con la administradora las
reservas recibidas por WhatsApp después de la hora del respaldo.

## 4. Monitoreo (riesgo R07)

- `https://<dominio>/salud/` responde `{"estado": "ok"}` (200) si el sitio y la base de datos funcionan, y 503 si la base no responde.
- Configurar un monitor gratuito (por ejemplo UptimeRobot) que revise esa dirección cada 5 minutos y avise por correo.
- Si el hosting falla por mucho tiempo: publicar en otro proveedor siguiendo la sección 1 con el último respaldo, y mientras tanto
  los clientes pueden escribir directamente por WhatsApp.

## 5. Seguridad y registro de incidentes (riesgos R01 y R02)

- El registro `seguridad` anota ingresos al panel, intentos fallidos, bloqueos, reservas restauradas o eliminadas, clientes
  eliminados y formularios descartados por el campo trampa. Se ve en la consola del servidor y, si se define
  `DJANGO_LOG_SEGURIDAD`, también en ese archivo.
- Tras 5 contraseñas incorrectas seguidas para un usuario (o 20 desde una misma conexión) el ingreso al panel se bloquea por 15 minutos.
- La lista de reservas guarda quién hizo el último cambio de cada una y sus datos originales (columnas `FK_admin`,
  `fecha_modificacion` y `datos_originales`).
- **Ante un posible incidente** (acceso no autorizado, filtración, pérdida de datos):
  1. Cambiar las contraseñas del panel (y de la base de datos y del correo si corresponde) y cerrar las sesiones abiertas
     cambiando `DJANGO_SECRET_KEY`.
  2. Revisar el registro de seguridad para saber qué pasó, cuándo y qué datos se vieron afectados.
  3. Anotar el incidente (fecha, qué pasó, datos afectados, medidas tomadas).
  4. Si se vieron afectados datos personales, avisar a los clientes afectados y a la Agencia de Protección de Datos Personales
     según lo que exige la Ley 21.719.
- **Solicitudes de los titulares** (acceso, rectificación, supresión, etc.): llegan al correo del hospedaje. Rectificar desde
  Panel → Clientes; para suprimir, eliminar primero sus reservas (si ya no hay obligación legal de guardarlas) y luego el cliente.
- La Política de privacidad está en `sitio/templates/sitio/privacidad.html` (es/en/pt). Conviene que la administradora la revise
  y que se actualice si cambia la forma de tratar los datos.

## 6. Actualizaciones de dependencias (riesgo R10)

- `requirements.txt` fija los rangos de versión (Django 6.1.x, psycopg 3, reportlab 4).
- Una vez al mes: `pip install pip-audit` y `pip-audit -r requirements.txt` para ver si hay fallas de seguridad conocidas;
  `pip install -U -r requirements.txt` instala los parches dentro del mismo rango. Después, correr las pruebas.
- Si el proyecto está en GitHub, `.github/dependabot.yml` abre automáticamente un Pull Request cuando hay versiones nuevas.

## 7. Pruebas

```
pip install -r requirements-dev.txt
python manage.py test panel --testrunner=panel.test_runner.PlanRunner
python actualizar_plan.py Plan_de_pruebas.xlsx
```
La segunda línea ejecuta todas las pruebas automáticas y guarda `resultados_pruebas.json`; la tercera copia los resultados al Excel.
