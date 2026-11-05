# CarpoolConnect
### Carpooling Coordination with Route Optimization

CarpoolConnect is a web-based carpool coordination application. It allows users to register as riders or drivers, publish rides, search for rides, find geographically nearby route matches, book seats, and manage bookings. Drivers can manage their vehicles and view passenger bookings. The application also provides in-app notifications for booking events.

## Features

- User registration and login with hashed passwords.
- Session-based authentication.
- Driver vehicle registration and listing.
- Ride publishing, searching, editing, and cancellation.
- Exact source/destination ride matching.
- Nearby route matching using geographic coordinates and pgvector similarity search.
- Pickup/drop-off insertion into an existing ride route, subject to a detour limit.
- Booking creation and cancellation with seat availability updates.
- Separate My Bookings and Passenger Bookings views.
- In-app notifications and read/unread status.
- Leaflet/OpenStreetMap map presentation and location lookup through the frontend.

## Technology stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | PostgreSQL |
| Vector similarity | pgvector |
| Database driver | Psycopg 3 |
| Frontend | HTML, CSS, JavaScript |
| Maps | Leaflet, OpenStreetMap |
| Geocoding | Nominatim (frontend integration) |
| Password hashing | Werkzeug security utilities |

## Repository structure

```text
.
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── bookings.py
│   ├── db.py
│   ├── pages.py
│   ├── rides.py
│   └── route_embeddings.py
├── docs/
├── sql/
│   ├── TEAM_03_DDL.sql
│   ├── schema.sql
│   ├── seed.sql
│   └── indexes.sql
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
├── requirements.txt
└── run.py
```

## Prerequisites

- Python 3.10 or newer.
- PostgreSQL.
- The PostgreSQL `vector` extension (pgvector).
- A browser with JavaScript enabled.

## Installation

See [INSTALLATION.md](docs/INSTALLATION.md) for database and environment setup.

Quick start after configuration:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Documentation

- [System Architecture](docs/ARCHITECTURE.md)
- [Database Design](docs/DATABASE.md)
- [API Reference](docs/API.md)
- [Installation Guide](docs/INSTALLATION.md)
- [Testing Guide](docs/TESTING.md)
- [User Guide](docs/USER_GUIDE.md)

## Configuration

The application loads environment variables using `python-dotenv`.

| Variable | Purpose |
|---|---|
| `FLASK_SECRET_KEY` | Flask session signing secret |
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port; defaults to `5432` |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |

## Important implementation notes

- The booking endpoint locks the selected ride row with `SELECT ... FOR UPDATE`, validates availability, and performs seat reduction and booking insertion in the same database transaction.
- Route embeddings are 16-dimensional vectors generated from ordered stop coordinates.
- The current application code updates seat counts directly. The older `fn_update_seats` / `trg_booking_seats` definition in the supplied SQL dump should not be enabled with the current booking code, because it can decrement seats a second time.
- The notification API expects a `notifications` table and a booking-event trigger. Those objects were implemented and tested in the development database but are not included in the SQL files in this ZIP. Add the verified DDL/function/trigger to a version-controlled migration before treating the ZIP as a complete fresh-install package.
- Nearby route matching uses vector similarity to shortlist candidates and then applies geographic route-insertion/detour calculations. The frontend's displayed route line should not be described as turn-by-turn road routing unless a road-routing provider is integrated.

