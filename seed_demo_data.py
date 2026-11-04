"""
CarpoolConnect demo data seeder
--------------------------------
Adds:
  * 6 demo users (4 drivers + 2 passengers)
  * 4 vehicles
  * 55 rides using 110 Indian city locations
  * 110 route stops (source + destination for each ride)
  * 12 confirmed demo bookings
  * Notification rows automatically, if the notification trigger is installed

Safe to rerun: a registry marker prevents duplicate seeding.
Does NOT delete or overwrite existing project records.
Does NOT create or use a Ratings feature/table.

Run from the project root:
    source env/bin/activate
    python seed_demo_data.py

Demo password for all seeded accounts: Demo@12345
"""

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from app.db import get_db_connection
from app.route_embeddings import create_route_embedding

load_dotenv()

DEMO_PASSWORD = "Demo@12345"
SEED_KEY = "carpoolconnect_demo_seed_v1"

# Approximate city-centre coordinates (latitude, longitude).
# The app stores route locations in stops; it does not currently have
# a dedicated cities/places table. These 110 places become route stops.
CITIES = [
    ("Delhi, Delhi", 28.6139, 77.2090),
    ("Jaipur, Rajasthan", 26.9124, 75.7873),
    ("Agra, Uttar Pradesh", 27.1767, 78.0081),
    ("Lucknow, Uttar Pradesh", 26.8467, 80.9462),
    ("Kanpur, Uttar Pradesh", 26.4499, 80.3319),
    ("Varanasi, Uttar Pradesh", 25.3176, 82.9739),
    ("Prayagraj, Uttar Pradesh", 25.4358, 81.8463),
    ("Gorakhpur, Uttar Pradesh", 26.7606, 83.3732),
    ("Dehradun, Uttarakhand", 30.3165, 78.0322),
    ("Haridwar, Uttarakhand", 29.9457, 78.1642),
    ("Chandigarh, Chandigarh", 30.7333, 76.7794),
    ("Amritsar, Punjab", 31.6340, 74.8723),
    ("Ludhiana, Punjab", 30.9010, 75.8573),
    ("Jalandhar, Punjab", 31.3260, 75.5762),
    ("Shimla, Himachal Pradesh", 31.1048, 77.1734),
    ("Manali, Himachal Pradesh", 32.2396, 77.1887),
    ("Jammu, Jammu and Kashmir", 32.7266, 74.8570),
    ("Srinagar, Jammu and Kashmir", 34.0837, 74.7973),
    ("Leh, Ladakh", 34.1526, 77.5771),
    ("Rishikesh, Uttarakhand", 30.0869, 78.2676),
    ("Ahmedabad, Gujarat", 23.0225, 72.5714),
    ("Surat, Gujarat", 21.1702, 72.8311),
    ("Vadodara, Gujarat", 22.3072, 73.1812),
    ("Rajkot, Gujarat", 22.3039, 70.8022),
    ("Bhavnagar, Gujarat", 21.7645, 72.1519),
    ("Mumbai, Maharashtra", 19.0760, 72.8777),
    ("Pune, Maharashtra", 18.5204, 73.8567),
    ("Nashik, Maharashtra", 19.9975, 73.7898),
    ("Nagpur, Maharashtra", 21.1458, 79.0882),
    ("Aurangabad, Maharashtra", 19.8762, 75.3433),
    ("Kolhapur, Maharashtra", 16.7050, 74.2433),
    ("Solapur, Maharashtra", 17.6599, 75.9064),
    ("Thane, Maharashtra", 19.2183, 72.9781),
    ("Panaji, Goa", 15.4909, 73.8278),
    ("Bengaluru, Karnataka", 12.9716, 77.5946),
    ("Mysuru, Karnataka", 12.2958, 76.6394),
    ("Mangaluru, Karnataka", 12.9141, 74.8560),
    ("Hubballi, Karnataka", 15.3647, 75.1240),
    ("Belagavi, Karnataka", 15.8497, 74.4977),
    ("Shivamogga, Karnataka", 13.9299, 75.5681),
    ("Chennai, Tamil Nadu", 13.0827, 80.2707),
    ("Coimbatore, Tamil Nadu", 11.0168, 76.9558),
    ("Madurai, Tamil Nadu", 9.9252, 78.1198),
    ("Tiruchirappalli, Tamil Nadu", 10.7905, 78.7047),
    ("Salem, Tamil Nadu", 11.6643, 78.1460),
    ("Tirunelveli, Tamil Nadu", 8.7139, 77.7567),
    ("Hyderabad, Telangana", 17.3850, 78.4867),
    ("Warangal, Telangana", 17.9689, 79.5941),
    ("Karimnagar, Telangana", 18.4386, 79.1288),
    ("Vijayawada, Andhra Pradesh", 16.5062, 80.6480),
    ("Visakhapatnam, Andhra Pradesh", 17.6868, 83.2185),
    ("Tirupati, Andhra Pradesh", 13.6288, 79.4192),
    ("Guntur, Andhra Pradesh", 16.3067, 80.4365),
    ("Kochi, Kerala", 9.9312, 76.2673),
    ("Thiruvananthapuram, Kerala", 8.5241, 76.9366),
    ("Kozhikode, Kerala", 11.2588, 75.7804),
    ("Thrissur, Kerala", 10.5276, 76.2144),
    ("Kollam, Kerala", 8.8932, 76.6141),
    ("Bhopal, Madhya Pradesh", 23.2599, 77.4126),
    ("Indore, Madhya Pradesh", 22.7196, 75.8577),
    ("Jabalpur, Madhya Pradesh", 23.1815, 79.9864),
    ("Gwalior, Madhya Pradesh", 26.2183, 78.1828),
    ("Ujjain, Madhya Pradesh", 23.1793, 75.7849),
    ("Raipur, Chhattisgarh", 21.2514, 81.6296),
    ("Bilaspur, Chhattisgarh", 22.0797, 82.1391),
    ("Ranchi, Jharkhand", 23.3441, 85.3096),
    ("Jamshedpur, Jharkhand", 22.8046, 86.2029),
    ("Dhanbad, Jharkhand", 23.7957, 86.4304),
    ("Patna, Bihar", 25.5941, 85.1376),
    ("Gaya, Bihar", 24.7914, 85.0002),
    ("Muzaffarpur, Bihar", 26.1209, 85.3647),
    ("Kolkata, West Bengal", 22.5726, 88.3639),
    ("Siliguri, West Bengal", 26.7271, 88.3953),
    ("Durgapur, West Bengal", 23.5204, 87.3119),
    ("Asansol, West Bengal", 23.6889, 86.9661),
    ("Bhubaneswar, Odisha", 20.2961, 85.8245),
    ("Cuttack, Odisha", 20.4625, 85.8830),
    ("Rourkela, Odisha", 22.2604, 84.8536),
    ("Puri, Odisha", 19.8135, 85.8312),
    ("Guwahati, Assam", 26.1445, 91.7362),
    ("Dibrugarh, Assam", 27.4728, 94.9120),
    ("Silchar, Assam", 24.8333, 92.7789),
    ("Shillong, Meghalaya", 25.5788, 91.8933),
    ("Imphal, Manipur", 24.8170, 93.9368),
    ("Aizawl, Mizoram", 23.7271, 92.7176),
    ("Kohima, Nagaland", 25.6751, 94.1086),
    ("Agartala, Tripura", 23.8315, 91.2868),
    ("Gangtok, Sikkim", 27.3389, 88.6065),
    ("Itanagar, Arunachal Pradesh", 27.0844, 93.6053),
    ("Jodhpur, Rajasthan", 26.2389, 73.0243),
    ("Udaipur, Rajasthan", 24.5854, 73.7125),
    ("Kota, Rajasthan", 25.2138, 75.8648),
    ("Bikaner, Rajasthan", 28.0229, 73.3119),
    ("Ajmer, Rajasthan", 26.4499, 74.6399),
    ("Karnal, Haryana", 29.6857, 76.9905),
    ("Gurugram, Haryana", 28.4595, 77.0266),
    ("Faridabad, Haryana", 28.4089, 77.3178),
    ("Panipat, Haryana", 29.3909, 76.9635),
    ("Hisar, Haryana", 29.1492, 75.7217),
    ("Bareilly, Uttar Pradesh", 28.3670, 79.4304),
    ("Meerut, Uttar Pradesh", 28.9845, 77.7064),
    ("Aligarh, Uttar Pradesh", 27.8974, 78.0880),
    ("Moradabad, Uttar Pradesh", 28.8386, 78.7733),
    ("Jhansi, Uttar Pradesh", 25.4484, 78.5685),
    ("Ooty, Tamil Nadu", 11.4102, 76.6950),
    ("Kanyakumari, Tamil Nadu", 8.0883, 77.5385),
    ("Kurnool, Andhra Pradesh", 15.8281, 78.0373),
    ("Anantapur, Andhra Pradesh", 14.6819, 77.6006),
    ("Kannur, Kerala", 11.8745, 75.3704),
    ("Alappuzha, Kerala", 9.4981, 76.3388),
    ("Latur, Maharashtra", 18.4088, 76.5604),
    ("Akola, Maharashtra", 20.7002, 77.0082),
    ("Amravati, Maharashtra", 20.9374, 77.7796),
    ("Dharwad, Karnataka", 15.4589, 75.0078),
]

DEMO_USERS = [
    ("Demo Driver 01", "demo.driver01@carpoolconnect.test", "9000000101", True),
    ("Demo Driver 02", "demo.driver02@carpoolconnect.test", "9000000102", True),
    ("Demo Driver 03", "demo.driver03@carpoolconnect.test", "9000000103", True),
    ("Demo Driver 04", "demo.driver04@carpoolconnect.test", "9000000104", True),
    ("Demo Passenger 01", "demo.passenger01@carpoolconnect.test", "9000000105", False),
    ("Demo Passenger 02", "demo.passenger02@carpoolconnect.test", "9000000106", False),
]

VEHICLES = [
    ("Maruti Suzuki", "Swift", "DEMO-SW-0101", 4, "White"),
    ("Hyundai", "i20", "DEMO-I20-0102", 4, "Silver"),
    ("Tata", "Nexon", "DEMO-NX-0103", 5, "Blue"),
    ("Honda", "City", "DEMO-HC-0104", 4, "Grey"),
]


def table_columns(cur, table_name):
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
    """, (table_name,))
    return {row[0] for row in cur.fetchall()}


def get_or_create_user(cur, user):
    name, email, phone, is_driver = user
    cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute("""
        INSERT INTO users (name, email, phone, password_hash, is_driver)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING user_id
    """, (
        name, email, phone,
        generate_password_hash(DEMO_PASSWORD),
        is_driver,
    ))
    return cur.fetchone()[0]


def main():
    if len(CITIES) < 100:
        raise RuntimeError("City dataset must contain at least 100 entries.")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Registry table makes this script safe to run more than once.
            cur.execute("""
                SELECT to_regclass('public.demo_seed_registry')
            """)

            if cur.fetchone()[0] is None:
                raise RuntimeError(
                    "demo_seed_registry table does not exist. "
                    "Create it as PostgreSQL administrator first."
                )
            cur.execute(
                "SELECT 1 FROM demo_seed_registry WHERE seed_key = %s",
                (SEED_KEY,)
            )
            if cur.fetchone():
                print("Demo data already exists (seed marker found).")
                print("No rows were added. To inspect it, query users/rides/stops/bookings.")
                return

            booking_cols = table_columns(cur, "bookings")
            if not {"ride_id", "rider_id", "pickup_stop_id", "drop_stop_id",
                    "seats_booked", "booking_status"}.issubset(booking_cols):
                raise RuntimeError("The BOOKINGS table does not match the expected project schema.")

            # Add the six demo accounts, without changing existing users.
            user_ids = {
                email: get_or_create_user(cur, user)
                for user in DEMO_USERS
                for email in [user[1]]
            }
            driver_ids = [
                user_ids["demo.driver01@carpoolconnect.test"],
                user_ids["demo.driver02@carpoolconnect.test"],
                user_ids["demo.driver03@carpoolconnect.test"],
                user_ids["demo.driver04@carpoolconnect.test"],
            ]
            passenger_ids = [
                user_ids["demo.passenger01@carpoolconnect.test"],
                user_ids["demo.passenger02@carpoolconnect.test"],
            ]

            # Add one vehicle per demo driver, if it does not already exist.
            vehicle_ids = []
            for driver_id, vehicle in zip(driver_ids, VEHICLES):
                make, model, plate, capacity, color = vehicle
                cur.execute("SELECT vehicle_id FROM vehicles WHERE plate_number = %s", (plate,))
                existing = cur.fetchone()
                if existing:
                    vehicle_ids.append(existing[0])
                else:
                    cur.execute("""
                        INSERT INTO vehicles
                            (driver_id, make, model, plate_number, capacity, color)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING vehicle_id
                    """, (driver_id, make, model, plate, capacity, color))
                    vehicle_ids.append(cur.fetchone()[0])

            # Detect optional columns and legacy seat trigger.
            has_insert_flags = {
                "pickup_stop_inserted", "drop_stop_inserted"
            }.issubset(booking_cols)

            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_trigger t
                    JOIN pg_class c ON c.oid = t.tgrelid
                    WHERE c.relname = 'bookings'
                      AND t.tgname = 'trg_booking_seats'
                      AND NOT t.tgisinternal
                      AND t.tgenabled <> 'D'
                )
            """)
            seat_trigger_enabled = cur.fetchone()[0]

            # Build rides from all supplied Indian city locations (two cities per ride).
            ride_records = []
            now = datetime.now().replace(second=0, microsecond=0)
            for i in range(0, len(CITIES), 2):
                source = CITIES[i]
                destination = CITIES[i + 1]
                driver_index = (i // 2) % len(driver_ids)
                vehicle_id = vehicle_ids[driver_index]
                driver_id = driver_ids[driver_index]
                departure = now + timedelta(days=2 + ((i // 2) % 24), hours=8 + ((i // 2) % 9))
                capacity = VEHICLES[driver_index][3]
                available_seats = capacity
                price = Decimal(150 + ((i // 2) % 9) * 50)

                cur.execute("""
                    INSERT INTO rides
                        (driver_id, vehicle_id, source, destination,
                         departure_time, available_seats, price_per_seat,
                         status, route_embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'scheduled', %s::vector)
                    RETURNING ride_id
                """, (
                    driver_id, vehicle_id, source[0], destination[0],
                    departure, available_seats, price,
                    "[" + ",".join(map(str, create_route_embedding([
                        {"latitude": source[1], "longitude": source[2]},
                        {"latitude": destination[1], "longitude": destination[2]},
                    ]))) + "]",
                ))
                ride_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO stops
                        (ride_id, sequence_no, location_name, latitude, longitude)
                    VALUES
                        (%s, 1, %s, %s, %s),
                        (%s, 2, %s, %s, %s)
                    RETURNING stop_id
                """, (
                    ride_id, source[0], source[1], source[2],
                    ride_id, destination[0], destination[1], destination[2],
                ))
                stop_ids = [row[0] for row in cur.fetchall()]
                ride_records.append({
                    "ride_id": ride_id,
                    "driver_id": driver_id,
                    "source_stop_id": stop_ids[0],
                    "destination_stop_id": stop_ids[1],
                    "capacity": capacity,
                })

            # Add 12 confirmed bookings across the demo rides.
            # Bookings use the route's endpoint stops, so the stop references
            # always satisfy the current schema and no route mutation is needed.
            bookings_added = 0
            for j in range(12):
                ride = ride_records[j * 3]  # spread bookings across routes
                rider_id = passenger_ids[j % len(passenger_ids)]
                seats = 1

                insert_columns = [
                    "ride_id", "rider_id", "pickup_stop_id",
                    "drop_stop_id", "seats_booked", "booking_status"
                ]
                values = [
                    ride["ride_id"], rider_id,
                    ride["source_stop_id"], ride["destination_stop_id"],
                    seats, "confirmed"
                ]

                if has_insert_flags:
                    insert_columns.extend(["pickup_stop_inserted", "drop_stop_inserted"])
                    values.extend([False, False])

                placeholders = ", ".join(["%s"] * len(values))
                columns_sql = ", ".join(insert_columns)
                cur.execute(
                    f"INSERT INTO bookings ({columns_sql}) VALUES ({placeholders}) RETURNING booking_id",
                    values
                )
                cur.fetchone()
                bookings_added += 1

                # The live application currently adjusts seats in Python.
                # If a legacy DB trigger is enabled, it performs the decrement
                # itself; avoid decrementing a second time.
                if not seat_trigger_enabled:
                    cur.execute("""
                        UPDATE rides
                        SET available_seats = available_seats - %s
                        WHERE ride_id = %s
                    """, (seats, ride["ride_id"]))

            cur.execute("""
                INSERT INTO demo_seed_registry (seed_key, details)
                VALUES (%s, %s)
            """, (
                SEED_KEY,
                f"{len(DEMO_USERS)} users, {len(VEHICLES)} vehicles, "
                f"{len(ride_records)} rides, {len(CITIES)} city stops, "
                f"{bookings_added} confirmed bookings"
            ))

            print("\nDemo data inserted successfully.")
            print(f"Demo users:       {len(DEMO_USERS)}")
            print(f"Vehicles:         {len(VEHICLES)}")
            print(f"Rides:            {len(ride_records)}")
            print(f"Distinct cities:  {len(CITIES)}")
            print(f"Route stops:      {len(CITIES)}")
            print(f"Bookings:         {bookings_added}")
            print("\nDemo login password for all seeded accounts:", DEMO_PASSWORD)
            print("\nDemo accounts:")
            for name, email, phone, is_driver in DEMO_USERS:
                print(f"  {'DRIVER' if is_driver else 'PASSENGER':9} {email}")
            print("\nThe transaction will commit when this connection closes successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nDemo seeding failed: {exc}", file=sys.stderr)
        print("No partial transaction should be committed.", file=sys.stderr)
        raise
