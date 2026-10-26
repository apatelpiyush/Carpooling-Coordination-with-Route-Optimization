DROP DATABASE IF EXISTS carpool;
CREATE DATABASE carpool;

\c carpool

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. USERS
CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    email           VARCHAR(120) UNIQUE NOT NULL,
    phone           VARCHAR(15) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    is_driver       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. VEHICLES (owned by a driver)
CREATE TABLE vehicles (
    vehicle_id      SERIAL PRIMARY KEY,
    driver_id       INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    make            VARCHAR(50) NOT NULL,
    model           VARCHAR(50) NOT NULL,
    plate_number    VARCHAR(15) UNIQUE NOT NULL,
    capacity        SMALLINT NOT NULL CHECK (capacity BETWEEN 1 AND 8),
    color           VARCHAR(30)
);

-- 3. RIDES (offered by a driver, using a vehicle)
CREATE TABLE rides (
    ride_id             SERIAL PRIMARY KEY,
    driver_id           INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    vehicle_id          INTEGER NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    source              VARCHAR(150) NOT NULL,
    destination         VARCHAR(150) NOT NULL,
    departure_time      TIMESTAMP NOT NULL,
    available_seats     SMALLINT NOT NULL CHECK (available_seats >= 0),
    price_per_seat      NUMERIC(8,2) NOT NULL CHECK (price_per_seat >= 0),
    status              VARCHAR(20) DEFAULT 'scheduled'
                         CHECK (status IN ('scheduled','ongoing','completed','cancelled')),
    route_embedding     vector(16),   -- pgvector: encodes route shape/checkpoints for similarity search
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. STOPS (ordered checkpoints belonging to a ride)
CREATE TABLE stops (
    stop_id         SERIAL PRIMARY KEY,
    ride_id         INTEGER NOT NULL REFERENCES rides(ride_id) ON DELETE CASCADE,
    sequence_no     SMALLINT NOT NULL,
    location_name   VARCHAR(150) NOT NULL,
    latitude        DECIMAL(9,6) NOT NULL,
    longitude       DECIMAL(9,6) NOT NULL,
    UNIQUE (ride_id, sequence_no)
);

-- 5. BOOKINGS (rider books seats on a ride, choosing pickup/drop stops)
CREATE TABLE bookings (
    booking_id      SERIAL PRIMARY KEY,
    ride_id         INTEGER NOT NULL REFERENCES rides(ride_id) ON DELETE CASCADE,
    rider_id        INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    pickup_stop_id  INTEGER NOT NULL REFERENCES stops(stop_id),
    drop_stop_id    INTEGER NOT NULL REFERENCES stops(stop_id),
    seats_booked    SMALLINT NOT NULL CHECK (seats_booked > 0),
    booking_status  VARCHAR(20) DEFAULT 'pending'
                    CHECK (booking_status IN ('pending','confirmed','cancelled','completed')),
    booked_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (pickup_stop_id <> drop_stop_id)
);

-- 6. RATINGS (one rating per booking, rider <-> driver)
CREATE TABLE ratings (
    rating_id       SERIAL PRIMARY KEY,
    booking_id      INTEGER UNIQUE NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    rated_by        INTEGER NOT NULL REFERENCES users(user_id),
    rated_user      INTEGER NOT NULL REFERENCES users(user_id),
    score           SMALLINT NOT NULL CHECK (score BETWEEN 1 AND 5),
    comment         VARCHAR(300),
    rated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (rated_by <> rated_user)
);


CREATE INDEX idx_rides_driver ON rides(driver_id);
CREATE INDEX idx_rides_status ON rides(status);
CREATE INDEX idx_stops_ride ON stops(ride_id);
CREATE INDEX idx_bookings_ride ON bookings(ride_id);
CREATE INDEX idx_bookings_rider ON bookings(rider_id);

CREATE INDEX idx_rides_route_embedding ON rides
    USING ivfflat (route_embedding vector_l2_ops) WITH (lists = 50);

CREATE OR REPLACE FUNCTION fn_update_seats() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.booking_status = 'confirmed' THEN
        UPDATE rides
        SET available_seats = available_seats - NEW.seats_booked
        WHERE ride_id = NEW.ride_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_booking_seats
AFTER INSERT ON bookings
FOR EACH ROW
EXECUTE FUNCTION fn_update_seats();
