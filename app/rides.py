
from flask import Blueprint, request, jsonify, session
from app.db import get_db_connection
from app.route_embeddings import create_request_embedding
from app.route_embeddings import create_route_embedding

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

def calculate_detour_km(original_stops, modified_stops):
    """
    Compare original and modified route distances.
    Stops are ordered (latitude, longitude) pairs.
    """
    original_distance = calculate_route_distance(original_stops)
    modified_distance = calculate_route_distance(modified_stops)

    return {
        "original_route_km": round(original_distance, 2),
        "modified_route_km": round(modified_distance, 2),
        "detour_km": round(
            modified_distance - original_distance, 2
        )
    }
    
def find_nearest_stop(stops, point, threshold_km=1.0):
    """
    Return the nearest stop index if it is within the threshold.
    Otherwise, return None.
    """
    nearest_index = None
    nearest_distance = float("inf")

    for i, (lat, lon) in enumerate(stops):
        distance = calculate_distance_km(
            lat, lon, point[0], point[1]
        )

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_index = i

    if nearest_distance <= threshold_km:
        return nearest_index

    return None


def insert_passenger_stops(
    original_stops,
    pickup_stop,
    drop_stop,
    pickup_index,
    drop_index,
    threshold_km=1.0
):
    """
    Reuse nearby existing stops or insert new coordinates after
    the specified original-route indices.

    Indices refer to positions in original_stops.
    """
    if len(original_stops) < 2:
        raise ValueError("Route must contain at least two stops")

    if not 0 <= pickup_index < drop_index < len(original_stops):
        raise ValueError("Invalid pickup/drop-off indices")

    pickup_existing = find_nearest_stop(
        original_stops, pickup_stop, threshold_km
    )
    drop_existing = find_nearest_stop(
        original_stops, drop_stop, threshold_km
    )

    effective_pickup_index = (
        pickup_existing if pickup_existing is not None else pickup_index
    )
    effective_drop_index = (
        drop_existing if drop_existing is not None else drop_index
    )

    if effective_pickup_index >= effective_drop_index:
        raise ValueError(
            "Pickup must occur before drop-off on the route"
        )

    additions = {}

    if pickup_existing is None:
        additions.setdefault(pickup_index, []).append(pickup_stop)

    if drop_existing is None:
        additions.setdefault(drop_index, []).append(drop_stop)

    modified_stops = []

    for i, stop in enumerate(original_stops):
        modified_stops.append(stop)
        modified_stops.extend(additions.get(i, []))

    return modified_stops
    

def find_best_route_insertion(
    original_stops,
    pickup_stop,
    drop_stop,
    threshold_km=1.0,
    max_detour_km=None
):
    """
    Find a low-detour route by reusing nearby stops or inserting new ones.

    Coordinates use (latitude, longitude).
    New passenger stops are inserted between existing route stops.
    """
    if len(original_stops) < 2:
        raise ValueError("Route must contain at least two stops")

    if not 0 < threshold_km <= 50:
        raise ValueError("Threshold must be between 0 and 50 km")

    original_distance = calculate_route_distance(original_stops)
    n = len(original_stops)


    def get_choices(point):
        choices = []

        # Prefer reusing an existing stop when it is nearby.
        for i, stop in enumerate(original_stops):
            distance = calculate_distance_km(
                stop[0], stop[1], point[0], point[1]
            )
            if distance <= threshold_km:
                choices.append({
                    "type": "existing",
                    "index": i
                })

        # Only insert a new stop if no existing stop is close enough.
        if not choices:
            for boundary in range(1, n):
                choices.append({
                    "type": "new",
                    "boundary": boundary
                })

        return choices

    pickup_choices = get_choices(pickup_stop)
    drop_choices = get_choices(drop_stop)
    best_result = None

    for pickup_choice in pickup_choices:
        for drop_choice in drop_choices:
            route_entries = []

            for boundary in range(n + 1):
                # Keep pickup before drop if both use the same boundary.
                if (
                    pickup_choice["type"] == "new"
                    and pickup_choice["boundary"] == boundary
                ):
                    route_entries.append(("pickup", pickup_stop))

                if (
                    drop_choice["type"] == "new"
                    and drop_choice["boundary"] == boundary
                ):
                    route_entries.append(("drop", drop_stop))

                if boundary < n:
                    route_entries.append(
                        (f"existing_{boundary}", original_stops[boundary])
                    )

            def get_entry_index(entry_name):
                for index, (name, _) in enumerate(route_entries):
                    if name == entry_name:
                        return index
                return None

            pickup_name = (
                f"existing_{pickup_choice['index']}"
                if pickup_choice["type"] == "existing"
                else "pickup"
            )
            drop_name = (
                f"existing_{drop_choice['index']}"
                if drop_choice["type"] == "existing"
                else "drop"
            )

            pickup_index = get_entry_index(pickup_name)
            drop_index = get_entry_index(drop_name)

            # Passenger must board before leaving the ride.
            if pickup_index is None or drop_index is None:
                continue
            if pickup_index >= drop_index:
                continue

            modified_route = [
                coordinates for _, coordinates in route_entries
            ]
            modified_distance = calculate_route_distance(modified_route)
            detour = max(0.0, modified_distance - original_distance)

            if (
                max_detour_km is not None
                and detour > max_detour_km
            ):
                continue

            if (
                best_result is None
                or detour < best_result["detour_km"]
            ):
                best_result = {
                    "original_route_km": round(original_distance, 2),
                    "modified_route_km": round(modified_distance, 2),
                    "detour_km": round(detour, 2),
                    "pickup_stop_index": pickup_index,
                    "drop_stop_index": drop_index,
                    "modified_route": modified_route,
                    "pickup_inserted": pickup_choice["type"] == "new",
                    "drop_inserted": drop_choice["type"] == "new",
                    "pickup_existing_index": (
                        pickup_choice["index"]
                        if pickup_choice["type"] == "existing"
                        else None
                    ),
                    "drop_existing_index": (
                        drop_choice["index"]
                        if drop_choice["type"] == "existing"
                        else None
                    ),
                }

    return best_result

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

    source_lat = data.get("source_lat")
    source_lon = data.get("source_lon")
    destination_lat = data.get("destination_lat")
    destination_lon = data.get("destination_lon")

    if not all([
        vehicle_id, source, destination, departure_time,
        available_seats is not None, price_per_seat is not None,
        source_lat is not None, source_lon is not None,
        destination_lat is not None, destination_lon is not None
    ]):
        return jsonify({"error": "All ride fields are required"}), 400

    if source.lower() == destination.lower():
        return jsonify({"error": "Source and destination must differ"}), 400

    try:
        vehicle_id = int(vehicle_id)
        available_seats = int(available_seats)
        price_per_seat = float(price_per_seat)
        departure = datetime.fromisoformat(departure_time)

        source_lat = float(source_lat)
        source_lon = float(source_lon)
        destination_lat = float(destination_lat)
        destination_lon = float(destination_lon)

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid ride details or coordinates"}), 400

    # Validate coordinates
    if not (
        -90 <= source_lat <= 90
        and -90 <= destination_lat <= 90
        and -180 <= source_lon <= 180
        and -180 <= destination_lon <= 180
    ):
        return jsonify({"error": "Invalid geographic coordinates"}), 400

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

    # Initial route contains source and destination.
    initial_stops = [
        {"latitude": source_lat, "longitude": source_lon},
        {"latitude": destination_lat, "longitude": destination_lon}
    ]

    embedding = create_route_embedding(initial_stops)

    vector_literal = "[" + ",".join(
        str(value) for value in embedding
    ) + "]"

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

            # Create ride and save its embedding.
            cur.execute(
                """
                INSERT INTO rides (
                    driver_id, vehicle_id, source, destination,
                    departure_time, available_seats, price_per_seat,
                    route_embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                RETURNING ride_id, source, destination, departure_time,
                          available_seats, price_per_seat, status
                """,
                (
                    driver_id, vehicle_id, source, destination,
                    departure, available_seats, price_per_seat,
                    vector_literal
                )
            )

            ride = cur.fetchone()
            ride_id = ride[0]

            # Automatically create the initial route stops.
            cur.execute(
                """
                INSERT INTO stops (
                    ride_id, sequence_no, location_name,
                    latitude, longitude
                )
                VALUES
                    (%s, 1, %s, %s, %s),
                    (%s, 2, %s, %s, %s)
                """,
                (
                    ride_id, source, source_lat, source_lon,
                    ride_id, destination, destination_lat, destination_lon
                )
            )

    return jsonify({
        "message": "Ride created successfully",
        "ride": {
            "ride_id": ride[0],
            "source": ride[1],
            "destination": ride[2],
            "departure_time": ride[3].isoformat(),
            "available_seats": ride[4],
            "price_per_seat": float(ride[5]),
            "status": ride[6],
            "embedding_dimensions": len(embedding)
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

        max_detour_arg = request.args.get("max_detour_km")
        max_detour_km = (
            float(max_detour_arg)
            if max_detour_arg is not None
            else None
        )

    except (KeyError, ValueError):
        return jsonify({
            "error": (
                "Provide valid pickup_lat, pickup_lon, "
                "drop_lat and drop_lon"
            )
        }), 400

    if (
        not -90 <= pickup_lat <= 90
        or not -180 <= pickup_lon <= 180
        or not -90 <= drop_lat <= 90
        or not -180 <= drop_lon <= 180
        or not 0 < radius_km <= 50
        or (
            max_detour_km is not None
            and not 0 <= max_detour_km <= 500
        )
    ):
        return jsonify({
            "error": "Coordinates, radius or detour limit are out of range"
        }), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query_embedding = create_request_embedding(
                    (pickup_lat, pickup_lon),
                    (drop_lat, drop_lon)
                )

                vector_literal = "[" + ",".join(
                    str(value) for value in query_embedding
                ) + "]"

                cur.execute(
                    """
                    SELECT
                        r.ride_id,
                        r.source,
                        r.destination,
                        r.departure_time,
                        r.available_seats,
                        r.price_per_seat,
                        u.name
                    FROM rides r
                    JOIN users u ON u.user_id = r.driver_id
                    WHERE r.status = 'scheduled'
                      AND r.departure_time > CURRENT_TIMESTAMP
                      AND r.available_seats > 0
                      AND r.route_embedding IS NOT NULL
                    ORDER BY r.route_embedding <-> %s::vector
                    LIMIT 100
                    """,
                    (vector_literal,)
                )

                rides = cur.fetchall()

                matches = []

                for ride in rides:
                    (
                        ride_id,
                        source,
                        destination,
                        departure_time,
                        available_seats,
                        price_per_seat,
                        driver_name
                    ) = ride

                    cur.execute(
                        """
                        SELECT
                            location_name,
                            latitude,
                            longitude
                        FROM stops
                        WHERE ride_id = %s
                          AND latitude IS NOT NULL
                          AND longitude IS NOT NULL
                        ORDER BY sequence_no
                        """,
                        (ride_id,)
                    )

                    stop_rows = cur.fetchall()

                    if len(stop_rows) < 2:
                        continue

                    route = [
                        (float(row[1]), float(row[2]))
                        for row in stop_rows
                    ]

                    # Find the best insertion or reuse nearby stops.
                    
                    result = find_best_route_insertion(
                        route,
                        (pickup_lat, pickup_lon),
                        (drop_lat, drop_lon),
                        threshold_km=min(1.0, radius_km),
                        max_detour_km=max_detour_km
                    )

                    if result is None:
                        continue

                    pickup_existing_index = result["pickup_existing_index"]
                    drop_existing_index = result["drop_existing_index"]

                    pickup_distance = (
                        0.0 if pickup_existing_index is None
                        else calculate_distance_km(
                            *route[pickup_existing_index], pickup_lat, pickup_lon
                        )
                    )

                    drop_distance = (
                        0.0 if drop_existing_index is None
                        else calculate_distance_km(
                            *route[drop_existing_index], drop_lat, drop_lon
                        )
                    )

                    matches.append({
                        "ride_id": ride_id,
                        "source": source,
                        "destination": destination,
                        "departure_time": departure_time.isoformat(),
                        "available_seats": available_seats,
                        "price_per_seat": float(price_per_seat),
                        "driver_name": driver_name,
                        "matched_pickup_stop": (
                            stop_rows[pickup_existing_index][0]
                            if pickup_existing_index is not None
                            else "New pickup stop"
                        ),
                        "matched_drop_stop": (
                            stop_rows[drop_existing_index][0]
                            if drop_existing_index is not None
                            else "New drop-off stop"
                        ),
                        "proposed_route": [
                            {
                                "latitude": lat,
                                "longitude": lon
                            }
                            for lat, lon in result["modified_route"]
                        ],
                        "pickup_stop_inserted": result["pickup_inserted"],
                        "drop_stop_inserted": result["drop_inserted"],
                        "pickup_distance_km": round(pickup_distance, 2),
                        "drop_distance_km": round(drop_distance, 2),
                        "original_route_km": result["original_route_km"],
                        "modified_route_km": result["modified_route_km"],
                        "detour_km": result["detour_km"]
                    })

        matches.sort(
            key=lambda item: (
                item["detour_km"],
                item["departure_time"]
            )
        )

        return jsonify({
            "count": len(matches),
            "matches": matches
        }), 200

    except Exception:
        app.logger.exception("Nearby ride matching failed")
        return jsonify({
            "error": "Could not search for nearby rides"
        }), 500
        

@rides_bp.route("/my-rides", methods=["GET"])
def list_my_rides():
    driver_id = session.get("user_id")

    if not driver_id:
        return jsonify({"error": "Please log in first"}), 401

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ride_id, source, destination, departure_time,
                       available_seats, price_per_seat, status
                FROM rides
                WHERE driver_id = %s
                ORDER BY departure_time DESC
                """,
                (driver_id,)
            )

            rows = cur.fetchall()

    return jsonify({
        "rides": [
            {
                "ride_id": row[0],
                "source": row[1],
                "destination": row[2],
                "departure_time": row[3].isoformat(),
                "available_seats": row[4],
                "price_per_seat": float(row[5]),
                "status": row[6]
            }
            for row in rows
        ]
    }), 200


@rides_bp.route("/rides/<int:ride_id>/details", methods=["GET"])
def get_ride_details(ride_id):
    if not session.get("user_id"):
        return jsonify({"error": "Please log in first"}), 401

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    r.ride_id,
                    r.driver_id,
                    r.source,
                    r.destination,
                    r.departure_time,
                    r.available_seats,
                    r.price_per_seat,
                    r.status,
                    u.name,
                    v.make,
                    v.model,
                    v.plate_number,
                    v.capacity,
                    v.color
                FROM rides r
                JOIN users u ON u.user_id = r.driver_id
                JOIN vehicles v ON v.vehicle_id = r.vehicle_id
                WHERE r.ride_id = %s
                """,
                (ride_id,)
            )

            ride = cur.fetchone()

            if not ride:
                return jsonify({"error": "Ride not found"}), 404

            cur.execute(
                """
                SELECT location_name, latitude, longitude, sequence_no
                FROM stops
                WHERE ride_id = %s
                ORDER BY sequence_no
                """,
                (ride_id,)
            )

            stops = cur.fetchall()

    return jsonify({
        "ride": {
            "ride_id": ride[0],
            "driver_id": ride[1],
            "source": ride[2],
            "destination": ride[3],
            "departure_time": ride[4].isoformat(),
            "available_seats": ride[5],
            "price_per_seat": float(ride[6]),
            "status": ride[7],
            "driver_name": ride[8],
            "vehicle": {
                "make": ride[9],
                "model": ride[10],
                "plate_number": ride[11],
                "capacity": ride[12],
                "color": ride[13]
            },
            "stops": [
                {
                    "name": stop[0],
                    "latitude": float(stop[1]),
                    "longitude": float(stop[2]),
                    "sequence": stop[3]
                }
                for stop in stops
            ]
        }
    }), 200
