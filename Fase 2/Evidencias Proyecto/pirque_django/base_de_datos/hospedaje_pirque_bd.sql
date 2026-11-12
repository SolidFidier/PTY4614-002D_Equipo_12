-- =====================================================================================================
-- Hospedaje Rural Pirque · script PRINCIPAL de la base de datos (PostgreSQL)
-- Crea la estructura completa. Es repetible (CREATE ... IF NOT EXISTS): no borra ni cambia lo existente.
-- Uso recomendado:  python manage.py preparar_bd      (ejecuta este archivo y luego cambios_bd.sql)
-- Uso manual:       sobre una base vacía llamada hospedaje_pirque_bd (pgAdmin → Query Tool, o psql -f).
-- Servicio exclusivo: cada reserva es del grupo completo (no hay habitaciones ni cobro en línea);
-- el valor de la estadía lo ingresa la administradora en `monto`.
-- =====================================================================================================

CREATE TABLE IF NOT EXISTS clientes (
    "ID_cliente"  varchar(20)  PRIMARY KEY,           -- RUT/DNI sin puntos ni guion
    nombre        varchar(100) NOT NULL,
    apellido      varchar(100) NOT NULL,
    nacionalidad  varchar(50)  NOT NULL,              -- Chileno | Extranjero
    telefono      varchar(100) NOT NULL,
    correo        varchar(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS reservas (
    "ID_reserva"    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "FK_cliente"    varchar(20)  NOT NULL CONSTRAINT "FK_cliente" REFERENCES clientes("ID_cliente") ON UPDATE CASCADE,
    nombre          varchar(100) NOT NULL,
    apellido        varchar(100) NOT NULL,
    correo          varchar(100) NOT NULL,
    telefono        varchar(100) NOT NULL,
    cant_adultos    integer      NOT NULL DEFAULT 1,
    cant_ninos      integer      NOT NULL DEFAULT 0,
    fecha_entrada   date         NOT NULL,
    fecha_salida    date         NOT NULL,
    monto           integer      NOT NULL DEFAULT 0,  -- valor de la estadía (CLP), lo ingresa la administradora
    estado_reserva  varchar(15)  NOT NULL DEFAULT 'pendiente',   -- pendiente | aceptada | cancelada
    estado_pago     varchar(15)  NOT NULL DEFAULT 'pendiente',   -- pendiente | abonado | pagado | cancelado
    notas           varchar(500) NOT NULL DEFAULT '',
    vista           boolean      NOT NULL DEFAULT false,         -- false = solicitud nueva que la administradora aún no revisa (se destaca en el panel)
    idioma          varchar(2)   NOT NULL DEFAULT 'es',          -- idioma del cliente (es | en | pt) para los correos
    fecha_reserva   timestamp    NOT NULL DEFAULT now(),         -- cuándo se creó la reserva
    CONSTRAINT chk_reservas_estado_reserva CHECK (estado_reserva IN ('pendiente', 'aceptada', 'cancelada')),
    CONSTRAINT chk_reservas_estado_pago    CHECK (estado_pago IN ('pendiente', 'abonado', 'pagado', 'cancelado'))
);

CREATE TABLE IF NOT EXISTS mensajes (
    "ID_mensaje"   integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre         varchar(100)  NOT NULL,
    correo         varchar(100)  NOT NULL,
    contenido      varchar(1000) NOT NULL,
    fecha_envio    timestamptz   NOT NULL DEFAULT now(),
    fecha_gestion  timestamp,                          -- NULL = pendiente
    "FK_admin"     integer                             -- usuario de Django que lo gestionó
);

-- Reseñas: una por reserva. El enlace del correo lleva `token` (único, imposible de adivinar) y sirve una sola vez.
CREATE TABLE IF NOT EXISTS resenas (
    "ID_resena"      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "FK_reserva"     integer      NOT NULL UNIQUE REFERENCES reservas("ID_reserva") ON DELETE CASCADE,
    token            varchar(64)  NOT NULL UNIQUE,
    fecha_solicitud  timestamp,                        -- cuándo se envió el correo (NULL = aún no enviado)
    fecha_resena     timestamp,                        -- cuándo respondió (NULL = sin responder)
    calificacion     smallint CHECK (calificacion BETWEEN 1 AND 5),
    comentario       varchar(1000) NOT NULL DEFAULT '',
    nombre_publico   varchar(100)  NOT NULL DEFAULT '',
    visible          boolean       NOT NULL DEFAULT false   -- la administradora elige cuáles se muestran en el inicio
);
