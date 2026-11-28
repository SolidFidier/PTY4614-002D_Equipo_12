-- =====================================================================================================
-- Migración a la estructura actual. Es SEGURO ejecutarlo varias veces y sobre una base nueva o antigua.
-- Se ejecuta con:  python manage.py preparar_bd   (después de hospedaje_pirque_bd.sql)
-- Conserva clientes, reservas y mensajes. ELIMINA lo que ya no existe en el sistema: las tablas
-- habitaciones, pago e historial_precios y las columnas de habitación/cancelación de reservas.
-- =====================================================================================================

-- 1) RUT/DNI como texto (puede llevar K o letras)
ALTER TABLE reservas DROP CONSTRAINT IF EXISTS "FK_cliente";
DO $$
BEGIN
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'clientes' AND column_name = 'ID_cliente') = 'integer' THEN
    ALTER TABLE clientes ALTER COLUMN "ID_cliente" TYPE varchar(20) USING "ID_cliente"::varchar;
  END IF;
  IF (SELECT data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'reservas' AND column_name = 'FK_cliente') = 'integer' THEN
    ALTER TABLE reservas ALTER COLUMN "FK_cliente" TYPE varchar(20) USING "FK_cliente"::varchar;
  END IF;
END $$;
ALTER TABLE reservas ADD CONSTRAINT "FK_cliente" FOREIGN KEY ("FK_cliente") REFERENCES clientes("ID_cliente") ON UPDATE CASCADE;

-- 2) Mensajes: un mensaje pendiente aún no tiene administrador
ALTER TABLE mensajes ALTER COLUMN "FK_admin" DROP NOT NULL;

-- 3) Reservas: columnas nuevas
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS estado_reserva varchar(15)  NOT NULL DEFAULT 'pendiente';
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS estado_pago    varchar(15)  NOT NULL DEFAULT 'pendiente';
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS notas          varchar(500) NOT NULL DEFAULT '';
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS idioma         varchar(2)   NOT NULL DEFAULT 'es';
-- vista: las reservas que ya existen se consideran revisadas; las nuevas del sitio nacen como no vistas (se destacan)
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS vista          boolean      NOT NULL DEFAULT true;
ALTER TABLE reservas ALTER COLUMN vista SET DEFAULT false;
-- Trazabilidad (H16): último administrador que cambió la reserva, cuándo, y copia de los datos originales
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS "FK_admin"         integer;
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS fecha_modificacion timestamp;
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS datos_originales   jsonb;
-- Consentimiento de la Política de privacidad (Ley 21.719)
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS fecha_consentimiento timestamp;
ALTER TABLE reservas ALTER COLUMN monto SET DEFAULT 0;
ALTER TABLE reservas ALTER COLUMN cant_ninos SET DEFAULT 0;
ALTER TABLE reservas ALTER COLUMN fecha_reserva SET DEFAULT now();

-- 4) Traspasa el estado del antiguo pago a la reserva (solo si todavía existe la tabla pago)
DO $$
BEGIN
  IF to_regclass('public.pago') IS NOT NULL THEN
    UPDATE reservas r SET
      estado_reserva = CASE p.estado_transaccion WHEN 'confirmado' THEN 'aceptada' WHEN 'pendiente' THEN 'pendiente' ELSE 'cancelada' END,
      estado_pago    = CASE p.estado_transaccion WHEN 'confirmado' THEN 'pagado'   WHEN 'pendiente' THEN 'pendiente' ELSE 'cancelado' END
    FROM (SELECT DISTINCT ON ("FK_reserva") "FK_reserva", estado_transaccion FROM pago ORDER BY "FK_reserva", "ID_pago" DESC) p
    WHERE p."FK_reserva" = r."ID_reserva";
  END IF;
END $$;

-- 5) Elimina lo que ya no se usa
DROP TABLE IF EXISTS pago CASCADE;
DROP TABLE IF EXISTS historial_precios CASCADE;
ALTER TABLE reservas DROP COLUMN IF EXISTS "FK_habitacion" CASCADE;
ALTER TABLE reservas DROP COLUMN IF EXISTS tipo_habitacion;
ALTER TABLE reservas DROP COLUMN IF EXISTS motivo_cancelacion;
ALTER TABLE reservas DROP COLUMN IF EXISTS fecha_cancelacion;
DROP TABLE IF EXISTS habitaciones CASCADE;

-- 6) Restricciones de los estados (y fechas coherentes; NOT VALID para no fallar con datos antiguos)
ALTER TABLE reservas DROP CONSTRAINT IF EXISTS chk_reservas_estado_reserva;
ALTER TABLE reservas ADD CONSTRAINT chk_reservas_estado_reserva CHECK (estado_reserva IN ('pendiente', 'aceptada', 'cancelada'));
ALTER TABLE reservas DROP CONSTRAINT IF EXISTS chk_reservas_estado_pago;
ALTER TABLE reservas ADD CONSTRAINT chk_reservas_estado_pago CHECK (estado_pago IN ('pendiente', 'abonado', 'pagado', 'cancelado'));
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_reservas_fechas') THEN
    ALTER TABLE reservas ADD CONSTRAINT chk_reservas_fechas CHECK (fecha_salida > fecha_entrada) NOT VALID;
  END IF;
END $$;

-- 6b) Un solo grupo a la vez, garantizado por la base de datos: no puede haber dos reservas ACEPTADAS con fechas cruzadas.
--     Si la base ya tiene reservas aceptadas que se cruzan, NO se agrega (para no detener la migración) y se avisa:
--     corrige esas reservas desde el panel y vuelve a ejecutar  python manage.py preparar_bd
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'excl_reservas_aceptadas_sin_cruce') THEN
    IF EXISTS (SELECT 1 FROM reservas a JOIN reservas b ON a."ID_reserva" < b."ID_reserva"
               WHERE a.estado_reserva = 'aceptada' AND b.estado_reserva = 'aceptada'
                 AND a.fecha_entrada < b.fecha_salida AND b.fecha_entrada < a.fecha_salida) THEN
      RAISE NOTICE 'Hay reservas ACEPTADAS con fechas cruzadas: no se agregó la restricción excl_reservas_aceptadas_sin_cruce.';
    ELSE
      ALTER TABLE reservas ADD CONSTRAINT excl_reservas_aceptadas_sin_cruce
        EXCLUDE USING gist (daterange(fecha_entrada, fecha_salida) WITH &&) WHERE (estado_reserva = 'aceptada');
    END IF;
  END IF;
END $$;

-- 7) Índices
CREATE INDEX IF NOT EXISTS idx_reservas_estado_fecha ON reservas (estado_reserva, fecha_entrada);
CREATE INDEX IF NOT EXISTS idx_mensajes_pendientes   ON mensajes (fecha_gestion);
