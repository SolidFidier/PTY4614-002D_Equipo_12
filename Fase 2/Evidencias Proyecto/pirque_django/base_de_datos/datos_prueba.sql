-- ============ DATOS DE PRUEBA (clientes, reservas, mensajes y reseñas) ============
-- Servicio exclusivo: no hay habitaciones ni pagos en línea; el valor (monto) lo define la administradora.
-- Las fechas son relativas a HOY, así que el panel siempre tiene un grupo hospedado hoy, reservas próximas,
-- pendientes, terminadas y reseñas. Las reservas ACEPTADAS no se superponen entre sí (un grupo a la vez).
-- Cargar con:  python manage.py cargar_datos_prueba     (ejecutar UNA sola vez)
CREATE TEMP TABLE tmp_prueba AS
SELECT * FROM (VALUES
 ('123456785','Camila','Rojas','Chileno','+56911110001','camila.rojas@example.com',2,0,-280,3,-295,'aceptada','pagado',180000,'es','Celebración familiar'),
 ('234567896','Felipe','Muñoz','Chileno','+56911110002','felipe.munoz@example.com',2,0,-250,2,-262,'aceptada','pagado',120000,'es',''),
 ('139876547','Daniela','Soto','Chileno','+56911110003','daniela.soto@example.com',3,0,-220,4,-231,'aceptada','pagado',260000,'es','Incluye baños de luna'),
 ('16543210K','Javier','Pérez','Chileno','+56911110004','javier.perez@example.com',2,0,-190,2,-200,'aceptada','pagado',130000,'es',''),
 ('AR32456789','Sofía','Benítez','Extranjero','+5491155550005','sofia.benitez@example.com',2,0,-160,5,-175,'aceptada','pagado',350000,'en','Vienen de Argentina'),
 ('112223339','Matías','Torres','Chileno','+56911110006','matias.torres@example.com',2,0,-130,2,-140,'cancelada','cancelado',120000,'es','Canceló por WhatsApp'),
 ('176543213','Valentina','Castro','Chileno','+56911110007','valentina.castro@example.com',2,1,-100,3,-110,'aceptada','pagado',200000,'es',''),
 ('182345679','Andrés','Silva','Chileno','+56911110008','andres.silva@example.com',2,0,-75,2,-85,'cancelada','cancelado',0,'es','No confirmó asistencia'),
 ('158765438','Carolina','Vega','Chileno','+56911110009','carolina.vega@example.com',2,0,-50,3,-58,'aceptada','pagado',210000,'es',''),
 ('PE45678123','Pedro','Quispe','Extranjero','+51987650010','pedro.quispe@example.com',2,0,-35,2,-43,'aceptada','pagado',140000,'pt',''),
 ('193456782','Lucía','Herrera','Chileno','+56911110011','lucia.herrera@example.com',2,0,-20,2,-26,'aceptada','abonado',150000,'es','Falta saldo'),
 ('145678900','Tomás','Navarro','Chileno','+56911110012','tomas.navarro@example.com',3,0,-10,3,-15,'aceptada','pagado',190000,'es',''),
 ('BR987654321','Lucas','Almeida','Extranjero','+5511988880018','lucas.almeida@example.com',2,0,20,4,-6,'aceptada','abonado',280000,'pt',''),
 ('201234565','Ignacio','Paredes','Chileno','+56911110013','ignacio.paredes@example.com',2,0,-1,3,-5,'aceptada','abonado',200000,'es','Grupo hospedado actualmente'),
 ('217654327','María','González','Chileno','+56911110014','maria.gonzalez@example.com',2,0,4,2,-3,'aceptada','abonado',130000,'es',''),
 ('189012349','Jorge','Silva','Chileno','+56911110017','jorge.silva@example.com',2,0,12,2,-2,'aceptada','pendiente',140000,'es',''),
 ('134567899','Carlos','Ramírez','Chileno','+56911110015','carlos.ramirez@example.com',3,0,5,2,-1,'pendiente','pendiente',0,'es','Misma fecha que María González'),
 ('167890121','Ana','Torres','Chileno','+56911110016','ana.torres@example.com',2,0,9,3,0,'pendiente','pendiente',0,'es',''),
 ('120987658','Rodrigo','Díaz','Chileno','+56911110019','rodrigo.diaz@example.com',2,0,10,2,0,'pendiente','pendiente',0,'en','')
) AS v(doc, nombre, apellido, nac, tel, correo, adultos, ninos, off_e, noches, off_res, est_res, est_pago, monto, idioma, notas);

INSERT INTO clientes ("ID_cliente", nombre, apellido, nacionalidad, telefono, correo)
SELECT doc, nombre, apellido, nac, tel, correo FROM tmp_prueba
ON CONFLICT ("ID_cliente") DO NOTHING;

INSERT INTO reservas ("FK_cliente", nombre, apellido, correo, telefono, cant_adultos, cant_ninos, fecha_entrada, fecha_salida,
                      monto, estado_reserva, estado_pago, notas, idioma, fecha_reserva)
SELECT t.doc, t.nombre, t.apellido, t.correo, t.tel, t.adultos, t.ninos,
       CURRENT_DATE + t.off_e, CURRENT_DATE + t.off_e + t.noches,
       t.monto, t.est_res, t.est_pago, t.notas, t.idioma, (CURRENT_DATE + t.off_res) + TIME '10:00'
FROM tmp_prueba t
WHERE NOT EXISTS (SELECT 1 FROM reservas r WHERE r."FK_cliente" = t.doc AND r.fecha_entrada = CURRENT_DATE + t.off_e)
ORDER BY t.off_res, t.off_e;   -- así el número de reserva sigue el orden de creación

-- Sin revisar (se destacan como «Nueva»): las pendientes y las creadas en los últimos 2 días
UPDATE reservas r SET vista = (t.est_res <> 'pendiente' AND t.off_res < -2)
FROM tmp_prueba t WHERE r."FK_cliente" = t.doc AND r.fecha_entrada = CURRENT_DATE + t.off_e;

DROP TABLE tmp_prueba;

-- Reseñas: respondidas (visibles y ocultas) y una solicitud enviada sin respuesta.
-- Las estadías terminadas de Lucía y Tomás no tienen fila: python manage.py enviar_resenas les enviará el correo.
INSERT INTO resenas ("FK_reserva", token, fecha_solicitud, fecha_resena, calificacion, comentario, nombre_publico, visible)
SELECT r."ID_reserva", substr(md5(random()::text || r."ID_reserva"::text) || md5(clock_timestamp()::text || r."ID_reserva"::text), 1, 43),
       (CURRENT_DATE + v.off_e + v.noches + 1) + TIME '09:00',
       CASE WHEN v.nota IS NULL THEN NULL ELSE (CURRENT_DATE + v.off_e + v.noches + 2) + TIME '18:30' END,
       v.nota, v.comentario, v.publico, v.visible
FROM (VALUES
 ('123456785', -280, 3, 5, 'Un lugar mágico para desconectarse. La atención de la familia fue excelente y los baños de luna una experiencia única.', 'Camila R.', true),
 ('234567896', -250, 2, 4, 'Muy tranquilo y la comida casera deliciosa. Volveremos.', 'Felipe M.', false),
 ('139876547', -220, 4, 5, 'Fuimos en grupo y tuvimos todo el lugar para nosotros, ideal para descansar. Súper recomendado.', 'Daniela S.', true),
 ('16543210K', -190, 2, 4, 'Excelente ubicación, a pasos de las viñas.', 'Javier P.', false),
 ('AR32456789', -160, 5, 5, 'Una experiencia inolvidable. La arena volcánica y las piedras calientes fueron lo mejor del viaje.', 'Sofía B.', true),
 ('176543213', -100, 3, 3, 'Muy lindo entorno, aunque llegamos tarde y hubo que coordinar por WhatsApp.', 'Valentina C.', false),
 ('158765438', -50, 3, 5, 'Perfecto para una escapada en pareja. Todo muy limpio y silencioso.', 'Carolina V.', true),
 ('PE45678123', -35, 2, NULL, '', 'Pedro Q.', false)
) AS v(doc, off_e, noches, nota, comentario, publico, visible)
JOIN reservas r ON r."FK_cliente" = v.doc AND r.fecha_entrada = CURRENT_DATE + v.off_e
WHERE NOT EXISTS (SELECT 1 FROM resenas x WHERE x."FK_reserva" = r."ID_reserva");

-- Mensajes de contacto (3 gestionados por el administrador con id 1 y 3 pendientes)
INSERT INTO mensajes (nombre, correo, contenido, fecha_envio, fecha_gestion, "FK_admin")
SELECT m.nombre, m.correo, m.contenido, m.fecha_envio, m.fecha_gestion, m.adm FROM (VALUES
 ('Camila Rojas','camila.rojas@example.com','Buenos días, quisiera consultar si tienen disponibilidad para alojar a mi familia durante el fin de semana del 14 al 16 de noviembre. También me gustaría saber qué servicios incluye la estadía. Muchas gracias.', now() - interval '6 days', (now() - interval '6 days' + interval '25 minutes')::timestamp, 1),
 ('Felipe Muñoz','felipe.munoz@example.com','Hola, ¿aceptan mascotas pequeñas? Viajaríamos con un perro de 5 kg.', now() - interval '5 days', NULL, NULL),
 ('Daniela Soto','daniela.soto@example.com','Quería confirmar el horario de llegada. Llegaríamos pasadas las 22:00, ¿hay problema?', now() - interval '4 days', (now() - interval '4 days' + interval '2 hours')::timestamp, 1),
 ('Javier Pérez','javier.perez@example.com','¿Tienen disponibilidad de pensión completa para 4 personas en diciembre?', now() - interval '3 days', NULL, NULL),
 ('John Miller','john.miller@example.com','Hello, do you offer airport pick-up from Santiago? We are 2 adults arriving in January.', now() - interval '2 days', NULL, NULL),
 ('Marta Alvarado','marta.alvarado@example.com','Muchas gracias por la atención, el fin de semana pasado fue maravilloso. Volveremos pronto.', now() - interval '1 day', (now() - interval '20 hours')::timestamp, 1)
) AS m(nombre, correo, contenido, fecha_envio, fecha_gestion, adm)
WHERE NOT EXISTS (SELECT 1 FROM mensajes x WHERE x.correo = m.correo AND x.contenido = m.contenido);
