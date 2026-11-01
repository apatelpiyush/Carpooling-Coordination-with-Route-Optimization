# Installation and Setup

## 1. Prerequisites

- Linux, macOS, or Windows with a supported Python installation.
- Python 3.10+.
- PostgreSQL server and client tools.
- pgvector installed for the PostgreSQL server version in use.
- Git (optional).
- A modern browser.

## 2. Obtain the source

Clone the repository or extract the project ZIP, then change to the project root:

```bash
cd "Carpooling Coordination with Route Optimization"
```

## 3. Create and activate a virtual environment

Linux/macOS:

```bash
python3 -m venv env
source env/bin/activate
```

Windows PowerShell:

```powershell
py -m venv env
.\env\Scripts\Activate.ps1
```

## 4. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

The supplied requirements include Flask, Psycopg 3, python-dotenv, Flask-WTF, and their dependencies.

## 5. Configure PostgreSQL and pgvector

Create a database and application user. Example commands (adjust passwords and privileges for your environment):

```sql
CREATE DATABASE carpool;
CREATE USER carpool_app WITH PASSWORD 'replace-with-a-strong-password';
GRANT ALL PRIVILEGES ON DATABASE carpool TO carpool_app;
```

Connect to the `carpool` database as an administrative user and enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The application expects the schema in the SQL scripts. Before applying them to a clean database, read `DATABASE.md` and reconcile the migration issues:
- Include the booking `pickup_stop_inserted` and `drop_stop_inserted` columns used by the current Python code.
- Include the `notifications` table, notification function, and trigger used by the running application.
- Do not install the legacy seat-decrement trigger together with the current application-managed seat update logic.
- Ensure the app user has the required table and sequence privileges.

The supplied `TEAM_03_DDL.sql` begins with `DROP DATABASE IF EXISTS carpool;`. Review it before execution; do not run it against a database containing data you need to preserve.

## 6. Environment variables

Create a local `.env` file in the project root:

```dotenv
FLASK_SECRET_KEY=replace-with-a-long-random-secret
DB_HOST=localhost
DB_PORT=5432
DB_NAME=carpool
DB_USER=carpool_app
DB_PASSWORD=replace-with-your-database-password
```

Do not commit `.env` or share its contents. `app/__init__.py` requires `FLASK_SECRET_KEY`; database connection settings are read by `app/db.py`.

## 7. Start the application

```bash
python run.py
```

The development server runs at:

```text
http://127.0.0.1:5000
```

Database connectivity can be checked at:

```text
http://127.0.0.1:5000/db-test
```

The `/db-test` endpoint returns the connected database, database user, and PostgreSQL version. Restrict or remove this diagnostic endpoint in production.

## 8. Troubleshooting

| Symptom | Checks |
|---|---|
| Missing `FLASK_SECRET_KEY` | Confirm `.env` exists in project root and contains the variable |
| PostgreSQL connection refused | Check PostgreSQL service, host, and port |
| Password authentication failed | Verify `DB_USER` and `DB_PASSWORD` |
| `vector` type not found | Install pgvector for the server version and run `CREATE EXTENSION vector` |
| Permission denied | Grant the application role privileges on required tables and sequences |
| Notification endpoint fails | Verify notification table/function/trigger migration and privileges |
| Booking writes fail on stop flags | Add `pickup_stop_inserted` and `drop_stop_inserted` to bookings table |
| Seat count decreases twice | Ensure legacy `trg_booking_seats` is not active with current Python booking logic |

## 9. Production considerations

The supplied `run.py` enables Flask debug mode. Do not expose this development server or debug mode to the public internet. Use a production WSGI server, HTTPS, secure cookie settings, CSRF protection appropriate to the deployment, restricted database privileges, backups, and secret management before deployment.
