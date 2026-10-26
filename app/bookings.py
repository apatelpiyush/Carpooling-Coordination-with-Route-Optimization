
from flask import Blueprint, request, jsonify, session
from app.db import get_db_connection
from math import isfinite
from .rides import (
    find_best_route_insertion,
    calculate_distance_km,
)

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api")


def save_modified_route(cur, ride_id, original_stops, result,
                        pickup, drop):
    """
    Save the proposed route and return the saved pickup/drop stop IDs.

    original_stops contains dictionaries with stop_id, location_name,
    latitude and longitude.
    """
    route_entries = []
    pickup_index = result["pickup_stop_index"]
    drop_index = result["drop_stop_index"]

    original_index = 0

    for i, coordinates in enumerate(result["modified_route"]):
        if result["pickup_inserted"] and i == pickup_index:
            route_entries.append({
                "type": "new",
                "name": pickup["name"],
                "latitude": pickup["latitude"],
                "longitude": pickup["longitude"],
                "kind": "pickup",
            })
        elif result["drop_inserted"] and i == drop_index:
            route_entries.append({
                "type": "new",
                "name": drop["name"],
                "latitude": drop["latitude"],
                "longitude": drop["longitude"],
                "kind": "drop",
            })
        else:
            if original_index >= len(original_stops):
                raise ValueError("Could not map the proposed route")

            stop = original_stops[original_index]
            original_index += 1

            route_entries.append({
                "type": "existing",
                "stop_id": stop["stop_id"],
                "kind": None,
            })

    if original_index != len(original_stops):
        raise ValueError("Proposed route does not preserve all existing stops")

    # Move existing sequence numbers to distinct negative values first.
    cur.execute(
        """
        SELECT stop_id, sequence_no
        FROM stops
        WHERE ride_id = %s
        ORDER BY sequence_no
        FOR UPDATE
        """,
        (ride_id,)
    )
    existing_rows = cur.fetchall()

    for stop_id, sequence_no in existing_rows:
        cur.execute(
            """
            UPDATE stops
            SET sequence_no = %s
            WHERE stop_id = %s
            """,
            (-sequence_no, stop_id)
        )

    # Add new stops with temporary sequence numbers.
    for i, entry in enumerate(route_entries):
        if entry["type"] == "new":
            cur.execute(
                """
                INSERT INTO stops
                    (ride_id, sequence_no, location_name, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING stop_id
                """,
                (
                    ride_id,
                    -1000 - i,
                    entry["name"],
                    entry["latitude"],
                    entry["longitude"],
                )
            )
            entry["stop_id"] = cur.fetchone()[0]

    # Assign final positive sequence numbers.
    for sequence, entry in enumerate(route_entries, start=1):
        cur.execute(
            """
            UPDATE stops
            SET sequence_no = %s
            WHERE stop_id = %s
            """,
            (sequence, entry["stop_id"])
        )

    pickup_id = next(
        entry["stop_id"]
        for entry in route_entries
        if entry["kind"] == "pickup"
    ) if result["pickup_inserted"] else original_stops[
        result["pickup_existing_index"]
    ]["stop_id"]

    drop_id = next(
        entry["stop_id"]
        for entry in route_entries
        if entry["kind"] == "drop"
    ) if result["drop_inserted"] else original_stops[
        result["drop_existing_index"]
    ]["stop_id"]

    return pickup_id, drop_id



@bookings_bp.route("/bookings", methods=["POST"])
def create_booking():
    rider_id = session.get("user_id")

    if not rider_id:
        return jsonify({"error": "Please log in first"}), 401

    data = request.get_json(silent=True) or {}

    try:
        ride_id = int(data.get("ride_id"))
        seats = int(data.get("seats_booked", 1))

        pickup = {
            "name": str(data.get("pickup_name", "Pickup location")).strip(),
            "latitude": float(data.get("pickup_lat")),
            "longitude": float(data.get("pickup_lon")),
        }

        drop = {
            "name": str(data.get("drop_name", "Drop-off location")).strip(),
            "latitude": float(data.get("drop_lat")),
            "longitude": float(data.get("drop_lon")),
        }

        max_detour_km = float(data.get("max_detour_km", 20))

    except (ValueError, TypeError):
        return jsonify({
            "error": "Provide valid ride, seat, coordinate and detour values"
        }), 400

    if ride_id < 1 or seats < 1:
        return jsonify({
            "error": "Ride ID and seat count must be positive"
        }), 400

    for point in (pickup, drop):
        lat = point["latitude"]
        lon = point["longitude"]

        if (
            not isfinite(lat)
            or not isfinite(lon)
            or not -90 <= lat <= 90
            or not -180 <= lon <= 180
            or not point["name"]
            or len(point["name"]) > 150
        ):
            return jsonify({
                "error": "Invalid location name or coordinates"
            }), 400

    if (
        not isfinite(max_detour_km)
        or not 0 <= max_detour_km <= 500
    ):
        return jsonify({
            "error": "Detour limit must be between 0 and 500 km"
        }), 400

    if pickup["latitude"] == drop["latitude"] and (
        pickup["longitude"] == drop["longitude"]
    ):
        return jsonify({
            "error": "Pickup and drop-off cannot be the same location"
        }), 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Lock the ride to prevent simultaneous overbooking.
            cur.execute(
                """
                SELECT driver_id, available_seats, status
                FROM rides
                WHERE ride_id = %s
                FOR UPDATE
                """,
                (ride_id,)
            )
            ride = cur.fetchone()

            if not ride:
                return jsonify({"error": "Ride not found"}), 404

            driver_id, available_seats, status = ride

            if driver_id == rider_id:
                return jsonify({
                    "error": "You cannot book your own ride"
                }), 400

            if status != "scheduled":
                return jsonify({
                    "error": "This ride is not available for booking"
                }), 400

            if seats > available_seats:
                return jsonify({
                    "error": "Not enough seats available",
                    "available_seats": available_seats
                }), 400

            # Load the ride's current stops in their correct order.
            cur.execute(
                """
                SELECT stop_id, sequence_no, location_name,
                       latitude, longitude
                FROM stops
                WHERE ride_id = %s
                ORDER BY sequence_no
                FOR UPDATE
                """,
                (ride_id,)
            )

            rows = cur.fetchall()

            if len(rows) < 2:
                return jsonify({
                    "error": "This ride does not have a valid route"
                }), 400

            original_stops = [
                {
                    "stop_id": row[0],
                    "sequence_no": row[1],
                    "location_name": row[2],
                    "latitude": float(row[3]),
                    "longitude": float(row[4]),
                }
                for row in rows
            ]

            original_coordinates = [
                (stop["latitude"], stop["longitude"])
                for stop in original_stops
            ]

            # Calculate the best route using the existing algorithm.
            try:
                result = find_best_route_insertion(
                    original_coordinates,
                    (pickup["latitude"], pickup["longitude"]),
                    (drop["latitude"], drop["longitude"]),
                    threshold_km=1.0,
                    max_detour_km=max_detour_km,
                )
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

            if result is None:
                return jsonify({
                    "error": (
                        "No valid pickup and drop-off order "
                        "was found within the detour limit"
                    )
                }), 400

            # Save route changes and obtain the actual stop IDs.
            pickup_stop_id, drop_stop_id = save_modified_route(
                cur,
                ride_id,
                original_stops,
                result,
                pickup,
                drop,
            )

            # Create the booking using valid stop IDs.
            cur.execute(
                """
                INSERT INTO bookings
                    (ride_id, rider_id, pickup_stop_id, drop_stop_id,
                     seats_booked, booking_status)
                VALUES (%s, %s, %s, %s, %s, 'confirmed')
                RETURNING booking_id, booked_at
                """,
                (
                    ride_id,
                    rider_id,
                    pickup_stop_id,
                    drop_stop_id,
                    seats,
                )
            )

            booking = cur.fetchone()

            # Reduce seats in the same transaction.
            cur.execute(
                """
                UPDATE rides
                SET available_seats = available_seats - %s
                WHERE ride_id = %s
                  AND available_seats >= %s
                RETURNING available_seats
                """,
                (seats, ride_id, seats)
            )

            if cur.fetchone() is None:
                return jsonify({
                    "error": "Not enough seats available"
                }), 400

    return jsonify({
        "message": "Booking successful",
        "booking": {
            "booking_id": booking[0],
            "ride_id": ride_id,
            "seats_booked": seats,
            "booking_status": "confirmed",
            "booked_at": (
                booking[1].isoformat() if booking[1] else None
            ),
            "pickup_stop_id": pickup_stop_id,
            "drop_stop_id": drop_stop_id,
        },
        "route": {
            "original_route_km": result["original_route_km"],
            "modified_route_km": result["modified_route_km"],
            "detour_km": result["detour_km"],
            "pickup_inserted": result["pickup_inserted"],
            "drop_inserted": result["drop_inserted"],
        }
    }), 201


@bookings_bp.route("/bookings", methods=["GET"])
def list_my_bookings():
    rider_id = session.get("user_id")

    if not rider_id:
        return jsonify({"error": "Please log in first"}), 401

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.booking_id, b.ride_id, b.seats_booked,
                       b.booking_status, b.booked_at,
                       r.source, r.destination, r.departure_time,
                       u.name AS driver_name
                FROM bookings b
                JOIN rides r ON r.ride_id = b.ride_id
                JOIN users u ON u.user_id = r.driver_id
                WHERE b.rider_id = %s
                ORDER BY b.booked_at DESC
                """,
                (rider_id,)
            )
            rows = cur.fetchall()

    return jsonify({
        "bookings": [
            {
                "booking_id": row[0],
                "ride_id": row[1],
                "seats_booked": row[2],
                "booking_status": row[3],
                "booked_at": row[4].isoformat() if row[4] else None,
                "source": row[5],
                "destination": row[6],
                "departure_time": row[7].isoformat(),
                "driver_name": row[8]
            }
            for row in rows
        ]
    }), 200


@bookings_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id):
    rider_id = session.get("user_id")

    if not rider_id:
        return jsonify({"error": "Please log in first"}), 401

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Find the booking belonging to this rider.
            cur.execute(
                """
                SELECT ride_id, seats_booked, booking_status
                FROM bookings
                WHERE booking_id = %s AND rider_id = %s
                """,
                (booking_id, rider_id)
            )
            booking = cur.fetchone()

            if not booking:
                return jsonify({"error": "Booking not found"}), 404

            ride_id, seats, booking_status = booking

            if booking_status != "confirmed":
                return jsonify({"error": "This booking cannot be cancelled"}), 400

            # Lock the ride before restoring seats.
            cur.execute(
                "SELECT status FROM rides WHERE ride_id = %s FOR UPDATE",
                (ride_id,)
            )
            ride = cur.fetchone()

            if not ride or ride[0] != "scheduled":
                return jsonify({
                    "error": "Only bookings for scheduled rides can be cancelled"
                }), 400

            cur.execute(
                """
                UPDATE bookings
                SET booking_status = 'cancelled'
                WHERE booking_id = %s AND rider_id = %s
                  AND booking_status = 'confirmed'
                RETURNING booking_id
                """,
                (booking_id, rider_id)
            )

            if not cur.fetchone():
                return jsonify({"error": "Booking has already changed"}), 409

            cur.execute(
                """
                UPDATE rides
                SET available_seats = available_seats + %s
                WHERE ride_id = %s
                """,
                (seats, ride_id)
            )

    return jsonify({"message": "Booking cancelled and seats restored"}), 200
