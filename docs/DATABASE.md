# Database Design

## 1. Database platform

- RDBMS: PostgreSQL
- Vector extension: pgvector (`vector`)
- Python driver: Psycopg 3
- Route vector dimension: 16

The supplied `sql/TEAM_03_DDL.sql` is the readable schema definition. `sql/schema.sql` is a PostgreSQL dump. `sql/seed.sql` contains seed data. `sql/indexes.sql` is empty in the supplied ZIP; index definitions are included in the DDL and schema dump.

## 2. Entity overview

```text
users 1 ─── many vehicles
users 1 ─── many rides (as driver)
vehicles 1 ─── many rides
rides 1 ─── many stops
rides 1 ─── many bookings
users 1 ─── many bookings (as rider)
bookings 1 ─── 0..1 ratings
users 1 ─── many ratings (as rater)
users 1 ─── many ratings (as rated user)
```

`notifications` is also used by the running application, but its DDL is absent from the supplied SQL scripts.

## 3. Tables

### users

| Column | Type | Rules / purpose |
|---|---|---|
| `user_id` | SERIAL | Primary key |
| `name` | VARCHAR(100) | Required |
| `email` | VARCHAR(120) | Required, unique |
| `phone` | VARCHAR(15) | Required, unique |
| `password_hash` | VARCHAR(255) | Required; stores password hash |
| `is_driver` | BOOLEAN | Defaults to false |
| `created_at` | TIMESTAMP | Defaults to current timestamp |

### vehicles

| Column | Type | Rules / purpose |
|---|---|---|
| `vehicle_id` | SERIAL | Primary key |
| `driver_id` | INTEGER | FK to users; cascade delete |
| `make`, `model` | VARCHAR | Required |
| `plate_number` | VARCHAR(15) | Unique, required |
| `capacity` | SMALLINT | CHECK: 1 through 8 |
| `color` | VARCHAR(30) | Optional |

### rides

| Column | Type | Rules / purpose |
|---|---|---|
| `ride_id` | SERIAL | Primary key |
| `driver_id` | INTEGER | FK to users; cascade delete |
| `vehicle_id` | INTEGER | FK to vehicles; cascade delete |
| `source`, `destination` | VARCHAR(150) | Required |
| `departure_time` | TIMESTAMP | Required |
| `available_seats` | SMALLINT | CHECK: non-negative |
| `price_per_seat` | NUMERIC(8,2) | CHECK: non-negative |
| `status` | VARCHAR(20) | scheduled/ongoing/completed/cancelled |
| `route_embedding` | vector(16) | pgvector geographic route representation |
| `created_at` | TIMESTAMP | Defaults to current timestamp |

### stops

| Column | Type | Rules / purpose |
|---|---|---|
| `stop_id` | SERIAL | Primary key |
| `ride_id` | INTEGER | FK to rides; cascade delete |
| `sequence_no` | SMALLINT | Ordered position |
| `location_name` | VARCHAR(150) | Required |
| `latitude` | DECIMAL(9,6) | Required |
| `longitude` | DECIMAL(9,6) | Required |

Unique constraint: `(ride_id, sequence_no)`.

### bookings

| Column | Type | Rules / purpose |
|---|---|---|
| `booking_id` | SERIAL | Primary key |
| `ride_id` | INTEGER | FK to rides; cascade delete |
| `rider_id` | INTEGER | FK to users; cascade delete |
| `pickup_stop_id` | INTEGER | FK to stops |
| `drop_stop_id` | INTEGER | FK to stops |
| `seats_booked` | SMALLINT | CHECK: greater than zero |
| `booking_status` | VARCHAR(20) | pending/confirmed/cancelled/completed; defaults to pending |
| `booked_at` | TIMESTAMP | Defaults to current timestamp |

Additional check: pickup and drop stop IDs must differ. The current application also writes `pickup_stop_inserted` and `drop_stop_inserted` flags; these columns are present in the live development schema used by the application but are absent from the supplied `TEAM_03_DDL.sql` and schema dump excerpt. Add them to the reproducible migration.

### ratings

| Column | Type | Rules / purpose |
|---|---|---|
| `rating_id` | SERIAL | Primary key |
| `booking_id` | INTEGER | Unique FK to bookings; cascade delete |
| `rated_by` | INTEGER | FK to users |
| `rated_user` | INTEGER | FK to users |
| `score` | SMALLINT | CHECK: 1 through 5 |
| `comment` | VARCHAR(300) | Optional |
| `rated_at` | TIMESTAMP | Defaults to current timestamp |

Additional check: `rated_by` and `rated_user` must differ. The ratings table exists in the schema, but no ratings API/UI is implemented in the supplied snapshot.

### notifications (development database)

The application expects these fields:

| Column | Purpose |
|---|---|
| `notification_id` | Primary key |
| `user_id` | Recipient user |
| `booking_id` | Related booking; nullable |
| `ride_id` | Related ride; nullable |
| `title` | Notification title |
| `message` | Notification body |
| `notification_type` | Event classification |
| `is_read` | Read state |
| `created_at` | Creation timestamp |

The development DDL used `BIGSERIAL` for `notification_id`, `user_id` references `users`, and nullable booking/ride references with `ON DELETE SET NULL`. The exact DDL/function/trigger should be committed as a SQL migration.

## 4. Constraints and integrity rules

- Primary keys identify each entity.
- Unique constraints prevent duplicate email, phone, vehicle plate, stop sequence per ride, and multiple ratings for one booking.
- Foreign keys preserve relationships between users, vehicles, rides, stops, bookings, and ratings.
- CHECK constraints validate seat counts, vehicle capacity, prices, rating scores, statuses, and distinct pickup/drop stops.
- NOT NULL constraints enforce required fields.

## 5. Indexes

The supplied DDL defines:

| Index | Table / column | Purpose |
|---|---|---|
| `idx_rides_driver` | rides(driver_id) | Driver ride lookup |
| `idx_rides_status` | rides(status) | Status filtering |
| `idx_stops_ride` | stops(ride_id) | Retrieve route stops |
| `idx_bookings_ride` | bookings(ride_id) | Ride booking lookup |
| `idx_bookings_rider` | bookings(rider_id) | Rider booking lookup |
| `idx_rides_route_embedding` | rides(route_embedding), IVFFlat | Vector similarity search |

The IVFFlat index uses 50 lists in the supplied DDL. The live development database also has `idx_notifications_user_created` on `(user_id, created_at DESC)` according to the development setup; add it to the migration.

## 6. Database functions and triggers

### Legacy seat trigger in supplied SQL

`fn_update_seats()` and `trg_booking_seats` decrement `rides.available_seats` after a booking insert when status is confirmed.

**Do not enable this trigger with the current application code.** `app/bookings.py` already decrements seats in the booking transaction before inserting the booking. Enabling both mechanisms would decrement seats twice.

For a fresh database following the current application implementation, omit the legacy trigger or replace the seat management strategy consistently in both database and application code.

### Booking notification trigger

The development database contains a PL/pgSQL function and trigger that create notifications when:
- a confirmed booking is inserted; and
- a confirmed booking changes to cancelled.

The trigger inserts a notification for the rider and the ride's driver. Its DDL is not included in this ZIP and must be version-controlled before a clean installation can reproduce this behavior.

## 7. Route embedding

Each ride has a 16-dimensional vector. `create_route_embedding()` normalizes latitude and longitude into approximately 0–1 ranges, samples eight positions from the ordered route coordinate sequence, and stores latitude/longitude pairs for those samples.

Nearby matching creates a request vector in the same format and uses pgvector's `<->` operator to rank route candidates.

## 8. Recommended database setup validation

After applying the finalized migration, verify:

```sql
SELECT extname FROM pg_extension WHERE extname = 'vector';

SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

SELECT trigger_name, event_object_table, action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public';
```

Before release, reconcile the schema differences noted above (`notifications`, booking stop-inserted flags, and the legacy seat trigger).
