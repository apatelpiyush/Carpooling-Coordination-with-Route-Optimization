# System Architecture

## 1. Overview

CarpoolConnect uses a conventional three-layer web architecture:

1. **Presentation layer:** Jinja templates, CSS, and browser-side JavaScript.
2. **Application layer:** Flask routes and business logic.
3. **Data layer:** PostgreSQL relational tables and pgvector route embeddings.

The browser communicates with Flask through HTTP page requests and JSON API requests. Flask uses Psycopg 3 to execute parameterized SQL statements against PostgreSQL.

## 2. Component structure

```text
Browser
  ├── Jinja-rendered pages
  ├── CSS stylesheets
  ├── JavaScript modules
  ├── Leaflet map
  └── Nominatim geocoding requests
          |
          | HTTP / JSON + session cookie
          v
Flask application (run.py)
  ├── app/pages.py       Page rendering and page access checks
  ├── app/auth.py        Registration, login, logout, current user
  ├── app/rides.py       Vehicles, rides, search, route matching
  ├── app/bookings.py    Booking, cancellation, notifications
  ├── app/route_embeddings.py
  └── app/db.py          PostgreSQL connection helper
          |
          | Psycopg 3 / SQL
          v
PostgreSQL + pgvector
  ├── users
  ├── vehicles
  ├── rides
  ├── stops
  ├── bookings
  ├── ratings
  └── notifications (development database object;
                     migration absent from supplied ZIP)
```

## 3. Backend modules

| Module | Responsibility |
|---|---|
| `app/__init__.py` | Creates Flask app and registers blueprints |
| `app/auth.py` | Registration, password hashing/checking, session login/logout, current-user API |
| `app/pages.py` | Renders pages and applies page-level login/driver checks |
| `app/rides.py` | Vehicle operations, ride creation/search, exact and nearby matching, driver ride management |
| `app/bookings.py` | Booking creation/listing/cancellation, driver booking listing, notification APIs |
| `app/route_embeddings.py` | Builds 16-dimensional route/request vectors |
| `app/db.py` | Creates PostgreSQL connections and tests DB connectivity |

The supplied `app/route_matching.py` and `app/ratings.py` files are empty in this ZIP snapshot. The active route insertion and matching helpers are in `app/rides.py`; do not attribute active functionality to the empty files.

## 4. Authentication and authorization

- Registration stores a Werkzeug-generated password hash rather than the plaintext password.
- Login retrieves the account by parameterized email query and checks the submitted password against the stored hash.
- On successful login, Flask session values `user_id` and `is_driver` are set.
- Logout clears the session.
- API endpoints check the session and, where needed, query the user's driver status from the database.
- A driver can also act as a passenger: My Bookings is available to both account types, while Passenger Bookings is driver-only.

## 5. Ride publishing flow

1. A logged-in driver registers a vehicle.
2. The driver submits ride details and source/destination coordinates.
3. The backend validates input and vehicle ownership/capacity.
4. The ride and its ordered stops are stored.
5. A 16-dimensional route embedding is generated from the ordered coordinates and stored in `rides.route_embedding`.

## 6. Route matching flow

### Exact matching

The `/api/rides/match` endpoint compares source and destination names case-insensitively and returns future scheduled rides with available seats.

### Nearby matching

1. The frontend obtains pickup and drop-off coordinates.
2. The backend validates coordinate ranges, search radius, and optional detour limit.
3. It creates a 16-dimensional request embedding.
4. PostgreSQL/pgvector ranks candidate ride embeddings using the `<->` distance operator.
5. The backend performs geographic checks and route insertion calculations against candidate stops.
6. Valid candidates are returned with route and detour information.

The embedding is a compact geographic representation used for candidate ranking. It is not a road-network route engine.

## 7. Booking transaction

The booking endpoint:

1. Requires a logged-in user.
2. Locks the target ride row using `SELECT ... FOR UPDATE`.
3. Checks ride ownership, scheduled status, departure time, and available seats.
4. Locks and reads the ordered route stops.
5. Finds a valid pickup/drop insertion subject to the detour limit.
6. Atomically decreases available seats.
7. Saves the modified stop sequence.
8. Regenerates the route embedding.
9. Inserts the confirmed booking.
10. Commits all changes together through the Psycopg connection context.

If an error occurs before commit, the transaction is rolled back by the connection context.

## 8. Cancellation flow

A rider can cancel only their own confirmed booking on a scheduled ride. The backend locks the ride, changes the booking status, restores the booked seat count, and removes only route stops inserted by that booking when they are no longer needed by another confirmed booking. The route embedding is refreshed after route changes.

## 9. Notification flow

The browser calls `/api/notifications` to retrieve the logged-in user's latest notifications and unread count. A notification can be marked read through `/api/notifications/<notification_id>/read`.

Booking-event notification creation is implemented in PostgreSQL using a PL/pgSQL trigger in the development database. The corresponding DDL is not present in the supplied ZIP and must be added to a migration for reproducible setup.

## 10. Transaction and consistency considerations

- Ride row locks serialize competing bookings against the same ride.
- Seat reduction uses a conditional update as an additional availability guard.
- Booking and route changes occur in one transaction.
- Cancellation checks ownership and current booking status before restoring seats.
- Parameterized SQL is used for user-provided values.

## 11. Known boundaries

- The frontend map uses Leaflet/OpenStreetMap and location lookup. Do not claim live turn-by-turn routing unless a routing service is added.
- The provided ZIP does not include the notification schema/trigger migration.
- The supplied SQL dump contains a legacy seat-decrement trigger that conflicts with application-managed seat updates. See [DATABASE.md](DATABASE.md).
