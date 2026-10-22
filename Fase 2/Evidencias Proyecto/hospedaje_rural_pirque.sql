--
-- PostgreSQL database dump
--

\restrict v3gVHdvhe2MxmJnXHeIdCvWSx6aKbpFXqmN9BWOHiFn3L7JGrGuyhNDMlOKNMiV

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

-- Started on 2026-10-22 02:29:12

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 4 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- TOC entry 4950 (class 0 OID 0)
-- Dependencies: 4
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 219 (class 1259 OID 16388)
-- Name: clientes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clientes (
    "ID_cliente" integer NOT NULL,
    nombre character varying(100) NOT NULL,
    apellido character varying(100) NOT NULL,
    nacionalidad character varying(50) NOT NULL,
    contacto character varying(100) NOT NULL
);


--
-- TOC entry 225 (class 1259 OID 16462)
-- Name: clientes_ID_cliente_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.clientes ALTER COLUMN "ID_cliente" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."clientes_ID_cliente_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 220 (class 1259 OID 16398)
-- Name: habitaciones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.habitaciones (
    "ID_habitacion" integer CONSTRAINT "Habitacion_ID_habitacion_not_null" NOT NULL,
    ruta_imagen character varying(100) CONSTRAINT "Habitacion_ruta_imagen_not_null" NOT NULL,
    tipo_habitacion character varying(50) CONSTRAINT "Habitacion_tipo_habitacion_not_null" NOT NULL,
    valor_x_noche integer CONSTRAINT "Habitacion_valor_x_noche_not_null" NOT NULL
);


--
-- TOC entry 226 (class 1259 OID 16463)
-- Name: habitaciones_ID_habitacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.habitaciones ALTER COLUMN "ID_habitacion" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."habitaciones_ID_habitacion_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 228 (class 1259 OID 16465)
-- Name: mensajes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mensajes (
    "ID_mensaje" integer NOT NULL,
    nombre character varying(100) NOT NULL,
    correo character varying(100) NOT NULL,
    contenido character varying(1000) NOT NULL,
    fecha_envio timestamp with time zone NOT NULL,
    fecha_gestion timestamp without time zone NOT NULL,
    "FK_admin" integer NOT NULL
);


--
-- TOC entry 227 (class 1259 OID 16464)
-- Name: mensajes_ID_mensaje_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.mensajes ALTER COLUMN "ID_mensaje" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."mensajes_ID_mensaje_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 223 (class 1259 OID 16445)
-- Name: pago; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pago (
    "ID_pago" integer NOT NULL,
    "FK_reserva" integer NOT NULL,
    monto integer NOT NULL,
    estado_transaccion character varying(30) NOT NULL,
    metodo_pago character varying(30) NOT NULL,
    fecha_pago time without time zone NOT NULL
);


--
-- TOC entry 222 (class 1259 OID 16443)
-- Name: pago_ID_pago_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.pago ALTER COLUMN "ID_pago" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."pago_ID_pago_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 221 (class 1259 OID 16407)
-- Name: reservas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reservas (
    "ID_reserva" integer NOT NULL,
    "FK_cliente" integer NOT NULL,
    contacto character varying(100) NOT NULL,
    monto integer NOT NULL,
    "FK_habitacion" integer NOT NULL,
    tipo_habitacion character varying(50) NOT NULL,
    cant_adultos integer NOT NULL,
    cant_ninos integer NOT NULL,
    fecha_entrada date NOT NULL,
    fecha_salida date NOT NULL,
    nombre_cliente character varying(100) NOT NULL,
    apellido_cliente character varying(100) NOT NULL,
    fecha_reserva timestamp without time zone NOT NULL
);


--
-- TOC entry 224 (class 1259 OID 16461)
-- Name: reservas_ID_reserva_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.reservas ALTER COLUMN "ID_reserva" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."reservas_ID_reserva_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 4935 (class 0 OID 16388)
-- Dependencies: 219
-- Data for Name: clientes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.clientes ("ID_cliente", nombre, apellido, nacionalidad, contacto) FROM stdin;
\.


--
-- TOC entry 4936 (class 0 OID 16398)
-- Dependencies: 220
-- Data for Name: habitaciones; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.habitaciones ("ID_habitacion", ruta_imagen, tipo_habitacion, valor_x_noche) FROM stdin;
\.


--
-- TOC entry 4944 (class 0 OID 16465)
-- Dependencies: 228
-- Data for Name: mensajes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.mensajes ("ID_mensaje", nombre, correo, contenido, fecha_envio, fecha_gestion, "FK_admin") FROM stdin;
\.


--
-- TOC entry 4939 (class 0 OID 16445)
-- Dependencies: 223
-- Data for Name: pago; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.pago ("ID_pago", "FK_reserva", monto, estado_transaccion, metodo_pago, fecha_pago) FROM stdin;
\.


--
-- TOC entry 4937 (class 0 OID 16407)
-- Dependencies: 221
-- Data for Name: reservas; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.reservas ("ID_reserva", "FK_cliente", contacto, monto, "FK_habitacion", tipo_habitacion, cant_adultos, cant_ninos, fecha_entrada, fecha_salida, nombre_cliente, apellido_cliente, fecha_reserva) FROM stdin;
\.


--
-- TOC entry 4951 (class 0 OID 0)
-- Dependencies: 225
-- Name: clientes_ID_cliente_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public."clientes_ID_cliente_seq"', 1, false);


--
-- TOC entry 4952 (class 0 OID 0)
-- Dependencies: 226
-- Name: habitaciones_ID_habitacion_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public."habitaciones_ID_habitacion_seq"', 1, false);


--
-- TOC entry 4953 (class 0 OID 0)
-- Dependencies: 227
-- Name: mensajes_ID_mensaje_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public."mensajes_ID_mensaje_seq"', 1, false);


--
-- TOC entry 4954 (class 0 OID 0)
-- Dependencies: 222
-- Name: pago_ID_pago_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public."pago_ID_pago_seq"', 1, false);


--
-- TOC entry 4955 (class 0 OID 0)
-- Dependencies: 224
-- Name: reservas_ID_reserva_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public."reservas_ID_reserva_seq"', 1, false);


--
-- TOC entry 4778 (class 2606 OID 16406)
-- Name: habitaciones Habitacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.habitaciones
    ADD CONSTRAINT "Habitacion_pkey" PRIMARY KEY ("ID_habitacion");


--
-- TOC entry 4776 (class 2606 OID 16397)
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_pkey PRIMARY KEY ("ID_cliente");


--
-- TOC entry 4784 (class 2606 OID 16478)
-- Name: mensajes mensajes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes
    ADD CONSTRAINT mensajes_pkey PRIMARY KEY ("ID_mensaje");


--
-- TOC entry 4782 (class 2606 OID 16455)
-- Name: pago pago_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_pkey PRIMARY KEY ("ID_pago");


--
-- TOC entry 4780 (class 2606 OID 16432)
-- Name: reservas reservas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservas
    ADD CONSTRAINT reservas_pkey PRIMARY KEY ("ID_reserva");


--
-- TOC entry 4785 (class 2606 OID 16433)
-- Name: reservas FK_cliente; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservas
    ADD CONSTRAINT "FK_cliente" FOREIGN KEY ("FK_cliente") REFERENCES public.clientes("ID_cliente") NOT VALID;


--
-- TOC entry 4786 (class 2606 OID 16438)
-- Name: reservas FK_habitacion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservas
    ADD CONSTRAINT "FK_habitacion" FOREIGN KEY ("FK_habitacion") REFERENCES public.habitaciones("ID_habitacion") NOT VALID;


--
-- TOC entry 4787 (class 2606 OID 16456)
-- Name: pago FK_reserva; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT "FK_reserva" FOREIGN KEY ("FK_reserva") REFERENCES public.reservas("ID_reserva");


-- Completed on 2026-10-22 02:29:13

--
-- PostgreSQL database dump complete
--

\unrestrict v3gVHdvhe2MxmJnXHeIdCvWSx6aKbpFXqmN9BWOHiFn3L7JGrGuyhNDMlOKNMiV

