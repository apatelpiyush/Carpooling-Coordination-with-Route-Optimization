
from flask import Blueprint, request, jsonify, session
from app.db import get_db_connection

rides_bp = Blueprint("rides", __name__, url_prefix="/api")

from math import radians, sin, cos, asin, sqrt


def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Calculate straight-line distance between two coordinates."""
    earth_radius_km = 6371.0

    lat1, lon1, lat2, lon2 = map(
        radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 2 * earth_radius_km * asin(sqrt(min(1.0, a)))
    
def calculate_route_distance(stops):
    """
    Calculate total straight-line distance for an ordered route.

    Each stop must contain latitude and longitude.
    """
    total_distance = 0.0

    for i in range(len(stops) - 1):
        lat1, lon1 = stops[i]
        lat2, lon2 = stops[i + 1]

        total_distance += calculate_distance_km(
            lat1, lon1, lat2, lon2
        )

    return total_distance


@rides_bp.route("/vehicles", methods=["POST"])
def add_vehicle():
    driver_id = session.get("user_id")

    if not driver_id:
        return jsonify({"error": "Please log in first"}), 401

    data = request.get_json(silent=True) or {}

    make = data.get("make", "").strip()
    model = data.get("model", "").strip()
    plate_number = data.get("plate_number", "").strip().upper()
    color = data.get("color")
    capacity = data.get("capacity")

    if not make or not model or not plate_number or capacity is None:
        return jsonify({"error": "Make, model, plate number and capacity are required"}), 400

    try:
        capacity = int(capacity)
    except (ValueError, TypeError):
        return jsonify({"error": "Capacity must be a number"}), 400

    if not 1 <= capacity <= 8:
        return jsonify({"error": "Capacity must be between 1 and 8"}), 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_driver FROM users WHERE user_id = %s",
                (driver_id,)
            )
            user = cur.fetchone()

            if not user or not user[0]:
                return jsonify({"error": "Only registered drivers can add vehicles"}), 403

            cur.execute(
                """
                INSERT INTO vehicles
                    (driver_id, make, model, plate_number, capacity, color)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING vehicle_id, make, model, plate_number, capacity, color
                """,
                (driver_id, make, model, plate_number, capacity, color)
            )

            vehicle = cur.fetchone()

    return jsonify({
        "message": "Vehicle added successfully",
        "vehicle": {
            "vehicle_id": vehicle[0],
            "make": vehicle[1],
            "model": vehicle[2],
            "plate_number": vehicle[3],
            "capacity": vehicle[4],
            "color": vehicle[5]
        }
    }), 201


@rides_bp.route("/vehicles", methods=["GET"])
def list_my_vehicles():
    driver_id = session.get("user_id")

    if not driver_id:
        return jsonify({"error": "Please log in first"}), 401

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT vehicle_id, make, model, plate_number, capacity, color
                FROM vehicles
                WHERE driver_id = %s
                ORDER BY vehicle_id DESC
                """,
                (driver_id,)
            )
            vehicles = cur.fetchall()

    return jsonify({
        "vehicles": [
            {
                "vehicle_id": v[0],
                "make": v[1],
                "model": v[2],
                "plate_number": v[3],
                "capacity": v[4],
                "color": v[5]
            }
            for v in vehicles
        ]
    }), 200


from datetime import datetime


@rides_bp.route("/rides", methods=["POST"])
def create_ride():
    driver_id = session.get("user_id")

    if not driver_id:
        return jsonify({"error": "Please log in first"}), 401

    data = request.get_json(silent=True) or {}

    vehicle_id = data.get("vehicle_id")
    source = data.get("source", "").strip()
    destination = data.get("destination", "").strip()
    departure_time = data.get("departure_time")
    available_seats = data.get("available_seats")
    price_per_seat = data.get("price_per_seat")

    if not all([
        vehicle_id, source, destination, departure_time,
        available_seats is not None, price_per_seat is not None
    ]):
        return jsonify({"error": "All ride fields are required"}), 400

    if source.lower() == destination.lower():
        return jsonify({"error": "Source and destination must differ"}), 400

    try:
        vehicle_id = int(vehicle_id)
        available_seats = int(available_seats)
        price_per_seat = float(price_per_seat)
        departure = datetime.fromisoformat(departure_time)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid vehicle, time, seats or price"}), 400

    if departure.tzinfo is not None:
        return jsonify({
            "error": "Send departure_time without a timezone, in YYYY-MM-DDTHH:MM format"
        }), 400

    if departure <= datetime.now():
        return jsonify({"error": "Departure time must be in the future"}), 400

    if available_seats < 1:
        return jsonify({"error": "At least one seat must be available"}), 400

    if price_per_seat < 0:
        return jsonify({"error": "Price cannot be negative"}), 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT capacity
                FROM vehicles
                WHERE vehicle_id = %s AND driver_id = %s
                """,
                (vehicle_id, driver_id)
            )
            vehicle = cur.fetchone()

            if not vehicle:
                return jsonify({
                    "error": "Vehicle not found or it does not belong to you"
                }), 404

            if available_seats > vehicle[0]:
                return jsonify({
                    "error": "Available seats cannot exceed vehicle capacity"
                }), 400

            cur.execute(
                """
                INSERT INTO rides (
                    driver_id, vehicle_id, source, destination,
                    departure_time, available_seats, price_per_seat
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING ride_id, source, destination, departure_time,
                          available_seats, price_per_seat, status
                """,
                (
                    driver_id, vehicle_id, source, destination,
                    departure, available_seats, price_per_seat
                )
            )
            ride = cur.fetchone()

    return jsonify({
        "message": "Ride created successfully",
        "ride": {
            "ride_id": ride[0],
            "source": ride[1],
            "destination": ride[2],
            "departure_time": ride[3].isoformat(),
            "available_seats": ride[4],
            "price_per_seat": float(ride[5]),
            "status": ride[6]
        }
    }), 201


@rides_bp.route("/rides", methods=["GET"])
def search_rides():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()

    query = """
        SELECT r.ride_id, u.name, r.source, r.destination,
               r.departure_time, r.available_seats, r.price_per_seat
        FROM rides r
        JOIN users u ON u.user_id = r.driver_id
        WHERE r.status = 'scheduled'
          AND r.departure_time >= CURRENT_TIMESTAMP
          AND r.available_seats > 0
    """
    params = []

    if source:
        query += " AND r.source ILIKE %s"
        params.append(f"%{source}%")

    if destination:
        query += " AND r.destination ILIKE %s"
        params.append(f"%{destination}%")

    query += " ORDER BY r.departure_time ASC LIMIT 100"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    return jsonify({
        "rides": [
            {
                "ride_id": r[0],
                "driver_name": r[1],
                "source": r[2],
                "destination": r[3],
                "departure_time": r[4].isoformat(),
                "available_seats": r[5],
                "price_per_seat": float(r[6])
            }
            for r in rows
        ]
    }), 200


@rides_bp.route("/rides/match", methods=["GET"])
def match_rides():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()

    if not source or not destination:
        return jsonify({
            "error": "Source and destination are required"
        }), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        r.ride_id,
                        r.source,
                        r.destination,
                        r.departure_time,
                        r.available_seats,
                        r.price_per_seat,
                        u.name AS driver_name
                    FROM rides r
                    JOIN users u ON r.driver_id = u.user_id
                    WHERE LOWER(r.source) = LOWER(%s)
                      AND LOWER(r.destination) = LOWER(%s)
                      AND r.status = 'scheduled'
                      AND r.departure_time > CURRENT_TIMESTAMP
                      AND r.available_seats > 0
                    ORDER BY r.departure_time ASC
                    """,
                    (source, destination)
                )

                rows = cur.fetchall()

        matches = [
            {
                "ride_id": row[0],
                "source": row[1],
                "destination": row[2],
                "departure_time": row[3].isoformat(),
                "available_seats": row[4],
                "price_per_seat": float(row[5]),
                "driver_name": row[6]
            }
            for row in rows
        ]

        return jsonify({
            "count": len(matches),
            "matches": matches
        }), 200

    except Exception:
        return jsonify({
            "error": "Could not search for matching rides"
        }), 500


@rides_bp.route("/rides/match-nearby", methods=["GET"])
def match_nearby_rides():
    try:
        pickup_lat = float(request.args["pickup_lat"])
        pickup_lon = float(request.args["pickup_lon"])
        drop_lat = float(request.args["drop_lat"])
        drop_lon = float(request.args["drop_lon"])
        radius_km = float(request.args.get("radius_km", 5))

    except (KeyError, ValueError):
        return jsonify({
            "error": "Provide valid pickup_lat, pickup_lon, drop_lat and drop_lon"
        }), 400

    if (
        not -90 <= pickup_lat <= 90
        or not -180 <= pickup_lon <= 180
        or not -90 <= drop_lat <= 90
        or not -180 <= drop_lon <= 180
        or not 0 < radius_km <= 50
    ):
        return jsonify({
            "error": "Coordinates or radius are out of range"
        }), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH stop_distances AS (
                        SELECT
                            s.stop_id,
                            s.ride_id,
                            s.sequence_no,
                            s.location_name,
                            s.latitude,
                            s.longitude,

                            6371 * 2 * ASIN(SQRT(LEAST(1.0,
                                POWER(SIN(RADIANS(
                                    s.latitude - %s
                                ) / 2), 2)
                                + COS(RADIANS(%s))
                                * COS(RADIANS(s.latitude))
                                * POWER(SIN(RADIANS(
                                    s.longitude - %s
                                ) / 2), 2)
                            ))) AS pickup_distance_km,

                            6371 * 2 * ASIN(SQRT(LEAST(1.0,
                                POWER(SIN(RADIANS(
                                    s.latitude - %s
                                ) / 2), 2)
                                + COS(RADIANS(%s))
                                * COS(RADIANS(s.latitude))
                                * POWER(SIN(RADIANS(
                                    s.longitude - %s
                                ) / 2), 2)
                            ))) AS drop_distance_km

                        FROM stops s
                        WHERE s.latitude IS NOT NULL
                          AND s.longitude IS NOT NULL
                    )

                    SELECT
                        r.ride_id,
                        r.source,
                        r.destination,
                        r.departure_time,
                        r.available_seats,
                        r.price_per_seat,
                        u.name,
                        p.location_name,
                        d.location_name,
                        ROUND(p.pickup_distance_km::numeric, 2),
                        ROUND(d.drop_distance_km::numeric, 2)

                    FROM rides r
                    JOIN users u
                      ON u.user_id = r.driver_id

                    JOIN stop_distances p
                      ON p.ride_id = r.ride_id

                    JOIN stop_distances d
                      ON d.ride_id = r.ride_id

                    WHERE p.sequence_no < d.sequence_no
                      AND p.pickup_distance_km <= %s
                      AND d.drop_distance_km <= %s
                      AND r.status = 'scheduled'
                      AND r.departure_time > CURRENT_TIMESTAMP
                      AND r.available_seats > 0

                    ORDER BY
                        p.pickup_distance_km
                        + d.drop_distance_km ASC,
                        r.departure_time ASC
                    """,
                    (
                        pickup_lat, pickup_lat, pickup_lon,
                        drop_lat, drop_lat, drop_lon,
                        radius_km, radius_km
                    )
                )

                rows = cur.fetchall()

        matches = [
            {
                "ride_id": row[0],
                "source": row[1],
                "destination": row[2],
                "departure_time": row[3].isoformat(),
                "available_seats": row[4],
                "price_per_seat": float(row[5]),
                "driver_name": row[6],
                "matched_pickup_stop": row[7],
                "matched_drop_stop": row[8],
                "pickup_distance_km": float(row[9]),
                "drop_distance_km": float(row[10])
            }
            for row in rows
        ]

        return jsonify({
            "count": len(matches),
            "matches": matches
        }), 200

    except Exception:
        return jsonify({
            "error": "Could not search for nearby rides"
        }), 500
