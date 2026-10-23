
from flask import Blueprint, request, jsonify, session
from app.db import get_db_connection

rides_bp = Blueprint("rides", __name__, url_prefix="/api")


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
        return jsonify({"error": "Missing required vehicle fields"}), 400

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
                return jsonify({"error": "Driver account required"}), 403

            cur.execute(
                """
                INSERT INTO vehicles
                    (driver_id, make, model, plate_number, capacity, color)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING vehicle_id, make, model, plate_number, capacity
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
            "capacity": vehicle[4]
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

    return jsonify([
        {
            "vehicle_id": v[0],
            "make": v[1],
            "model": v[2],
            "plate_number": v[3],
            "capacity": v[4],
            "color": v[5]
        }
        for v in vehicles
    ])
