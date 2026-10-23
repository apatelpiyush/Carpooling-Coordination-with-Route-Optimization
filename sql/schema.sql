--
-- PostgreSQL database dump
--

\restrict GKP0KUT5QzpArXtaW4zE4uYSj1DjXybVbaiAiPShkPmQgm5t81pW7yMTxmUXrdh

-- Dumped from database version 16.15 (Ubuntu 16.15-1.pgdg24.04+2)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-1.pgdg24.04+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: fn_update_seats(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_update_seats() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.booking_status = 'confirmed' THEN
        UPDATE rides
        SET available_seats = available_seats - NEW.seats_booked
        WHERE ride_id = NEW.ride_id;
    END IF;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bookings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bookings (
    booking_id integer NOT NULL,
    ride_id integer NOT NULL,
    rider_id integer NOT NULL,
    pickup_stop_id integer NOT NULL,
    drop_stop_id integer NOT NULL,
    seats_booked smallint NOT NULL,
    booking_status character varying(20) DEFAULT 'pending'::character varying,
    booked_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT bookings_booking_status_check CHECK (((booking_status)::text = ANY ((ARRAY['pending'::character varying, 'confirmed'::character varying, 'cancelled'::character varying, 'completed'::character varying])::text[]))),
    CONSTRAINT bookings_check CHECK ((pickup_stop_id <> drop_stop_id)),
    CONSTRAINT bookings_seats_booked_check CHECK ((seats_booked > 0))
);


--
-- Name: bookings_booking_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bookings_booking_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bookings_booking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bookings_booking_id_seq OWNED BY public.bookings.booking_id;


--
-- Name: ratings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ratings (
    rating_id integer NOT NULL,
    booking_id integer NOT NULL,
    rated_by integer NOT NULL,
    rated_user integer NOT NULL,
    score smallint NOT NULL,
    comment character varying(300),
    rated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ratings_check CHECK ((rated_by <> rated_user)),
    CONSTRAINT ratings_score_check CHECK (((score >= 1) AND (score <= 5)))
);


--
-- Name: ratings_rating_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ratings_rating_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ratings_rating_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ratings_rating_id_seq OWNED BY public.ratings.rating_id;


--
-- Name: rides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rides (
    ride_id integer NOT NULL,
    driver_id integer NOT NULL,
    vehicle_id integer NOT NULL,
    source character varying(150) NOT NULL,
    destination character varying(150) NOT NULL,
    departure_time timestamp without time zone NOT NULL,
    available_seats smallint NOT NULL,
    price_per_seat numeric(8,2) NOT NULL,
    status character varying(20) DEFAULT 'scheduled'::character varying,
    route_embedding public.vector(16),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT rides_available_seats_check CHECK ((available_seats >= 0)),
    CONSTRAINT rides_price_per_seat_check CHECK ((price_per_seat >= (0)::numeric)),
    CONSTRAINT rides_status_check CHECK (((status)::text = ANY ((ARRAY['scheduled'::character varying, 'ongoing'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: rides_ride_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rides_ride_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rides_ride_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rides_ride_id_seq OWNED BY public.rides.ride_id;


--
-- Name: stops; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stops (
    stop_id integer NOT NULL,
    ride_id integer NOT NULL,
    sequence_no smallint NOT NULL,
    location_name character varying(150) NOT NULL,
    latitude numeric(9,6) NOT NULL,
    longitude numeric(9,6) NOT NULL
);


--
-- Name: stops_stop_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stops_stop_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stops_stop_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stops_stop_id_seq OWNED BY public.stops.stop_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    name character varying(100) NOT NULL,
    email character varying(120) NOT NULL,
    phone character varying(15) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_driver boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vehicles (
    vehicle_id integer NOT NULL,
    driver_id integer NOT NULL,
    make character varying(50) NOT NULL,
    model character varying(50) NOT NULL,
    plate_number character varying(15) NOT NULL,
    capacity smallint NOT NULL,
    color character varying(30),
    CONSTRAINT vehicles_capacity_check CHECK (((capacity >= 1) AND (capacity <= 8)))
);


--
-- Name: vehicles_vehicle_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.vehicles_vehicle_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: vehicles_vehicle_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.vehicles_vehicle_id_seq OWNED BY public.vehicles.vehicle_id;


--
-- Name: bookings booking_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings ALTER COLUMN booking_id SET DEFAULT nextval('public.bookings_booking_id_seq'::regclass);


--
-- Name: ratings rating_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ratings ALTER COLUMN rating_id SET DEFAULT nextval('public.ratings_rating_id_seq'::regclass);


--
-- Name: rides ride_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rides ALTER COLUMN ride_id SET DEFAULT nextval('public.rides_ride_id_seq'::regclass);


--
-- Name: stops stop_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stops ALTER COLUMN stop_id SET DEFAULT nextval('public.stops_stop_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: vehicles vehicle_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehicles ALTER COLUMN vehicle_id SET DEFAULT nextval('public.vehicles_vehicle_id_seq'::regclass);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (booking_id);


--
-- Name: ratings ratings_booking_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_booking_id_key UNIQUE (booking_id);


--
-- Name: ratings ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_pkey PRIMARY KEY (rating_id);


--
-- Name: rides rides_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rides
    ADD CONSTRAINT rides_pkey PRIMARY KEY (ride_id);


--
-- Name: stops stops_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stops
    ADD CONSTRAINT stops_pkey PRIMARY KEY (stop_id);


--
-- Name: stops stops_ride_id_sequence_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stops
    ADD CONSTRAINT stops_ride_id_sequence_no_key UNIQUE (ride_id, sequence_no);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: vehicles vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_pkey PRIMARY KEY (vehicle_id);


--
-- Name: vehicles vehicles_plate_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_plate_number_key UNIQUE (plate_number);


--
-- Name: idx_bookings_ride; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bookings_ride ON public.bookings USING btree (ride_id);


--
-- Name: idx_bookings_rider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bookings_rider ON public.bookings USING btree (rider_id);


--
-- Name: idx_rides_driver; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rides_driver ON public.rides USING btree (driver_id);


--
-- Name: idx_rides_route_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rides_route_embedding ON public.rides USING ivfflat (route_embedding) WITH (lists='50');


--
-- Name: idx_rides_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rides_status ON public.rides USING btree (status);


--
-- Name: idx_stops_ride; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stops_ride ON public.stops USING btree (ride_id);


--
-- Name: bookings trg_booking_seats; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_booking_seats AFTER INSERT ON public.bookings FOR EACH ROW EXECUTE FUNCTION public.fn_update_seats();


--
-- Name: bookings bookings_drop_stop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_drop_stop_id_fkey FOREIGN KEY (drop_stop_id) REFERENCES public.stops(stop_id);


--
-- Name: bookings bookings_pickup_stop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pickup_stop_id_fkey FOREIGN KEY (pickup_stop_id) REFERENCES public.stops(stop_id);


--
-- Name: bookings bookings_ride_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_ride_id_fkey FOREIGN KEY (ride_id) REFERENCES public.rides(ride_id) ON DELETE CASCADE;


--
-- Name: bookings bookings_rider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_rider_id_fkey FOREIGN KEY (rider_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: ratings ratings_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(booking_id) ON DELETE CASCADE;


--
-- Name: ratings ratings_rated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_rated_by_fkey FOREIGN KEY (rated_by) REFERENCES public.users(user_id);


--
-- Name: ratings ratings_rated_user_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_rated_user_fkey FOREIGN KEY (rated_user) REFERENCES public.users(user_id);


--
-- Name: rides rides_driver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rides
    ADD CONSTRAINT rides_driver_id_fkey FOREIGN KEY (driver_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: rides rides_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rides
    ADD CONSTRAINT rides_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(vehicle_id) ON DELETE CASCADE;


--
-- Name: stops stops_ride_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stops
    ADD CONSTRAINT stops_ride_id_fkey FOREIGN KEY (ride_id) REFERENCES public.rides(ride_id) ON DELETE CASCADE;


--
-- Name: vehicles vehicles_driver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_driver_id_fkey FOREIGN KEY (driver_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict GKP0KUT5QzpArXtaW4zE4uYSj1DjXybVbaiAiPShkPmQgm5t81pW7yMTxmUXrdh

