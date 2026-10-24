
from flask import Blueprint, request, jsonify, session
from app.db import get_db_connection

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api")


@bookings_bp.route("/bookings", methods=["POST"])
def create_booking():
    rider_id = session.get("user_id")

    if not rider_id:
        return jsonify({"error": "Please log in first"}), 401

    data = request.get_json(silent=True) or {}

    try:
        ride_id = int(data.get("ride_id"))
        seats = int(data.get("seats_booked", 1))
        pickup_stop_id = int(data.get("pickup_stop_id"))
        drop_stop_id = int(data.get("drop_stop_id"))
    except (ValueError, TypeError):
        return jsonify({
            "error": "Valid ride, seat, pickup stop and drop-off stop IDs are required"
        }), 400

    if ride_id < 1 or seats < 1:
        return jsonify({"error": "Ride ID and seat count must be positive"}), 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Lock the ride row to prevent simultaneous overbooking.
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
                return jsonify({"error": "You cannot book your own ride"}), 400

            if status != "scheduled":
                return jsonify({"error": "This ride is not available for booking"}), 400

            if seats > available_seats:
                return jsonify({
                    "error": "Not enough seats available",
                    "available_seats": available_seats
                }), 400
            cur.execute(
                """
                SELECT stop_id, sequence_no
                FROM stops
                WHERE ride_id = %s
                  AND stop_id IN (%s, %s)
                """,
                (ride_id, pickup_stop_id, drop_stop_id)
            )

            stop_rows = cur.fetchall()
            stop_sequences = {row[0]: row[1] for row in stop_rows}

            if pickup_stop_id not in stop_sequences or drop_stop_id not in stop_sequences:
                return jsonify({
                    "error": "Pickup and drop-off stops must belong to this ride"
                }), 400

            if stop_sequences[pickup_stop_id] >= stop_sequences[drop_stop_id]:
                return jsonify({
                    "error": "Pickup must come before drop-off"
                }), 400
            # This initial version supports bookings without stop selection.
            cur.execute(
                """
                INSERT INTO bookings
                    (ride_id, rider_id, pickup_stop_id, drop_stop_id,
                     seats_booked, booking_status)
                VALUES (%s, %s, %s, %s, %s, 'confirmed')
                RETURNING booking_id, booked_at
                """,
                (ride_id, rider_id, pickup_stop_id, drop_stop_id, seats)
            )

            booking = cur.fetchone()

            cur.execute(
                """
                UPDATE rides
                SET available_seats = available_seats - %s
                WHERE ride_id = %s
                """,
                (seats, ride_id)
            )

    return jsonify({
        "message": "Booking successful",
        "booking": {
            "booking_id": booking[0],
            "ride_id": ride_id,
            "seats_booked": seats,
            "booking_status": "confirmed",
            "booked_at": booking[1].isoformat() if booking[1] else None
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
