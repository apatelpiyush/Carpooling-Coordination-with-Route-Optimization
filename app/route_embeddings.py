
from app.db import get_db_connection


def create_route_embedding(stops):
    """
    Convert ordered route stops into a 16-dimensional
    geographic feature vector.

    Each stop is a dictionary containing latitude and longitude.
    """
    if len(stops) < 2:
        raise ValueError("A route needs at least two stops")

    # Normalize latitude and longitude to roughly 0..1.
    coordinates = []

    for stop in stops:
        latitude = float(stop["latitude"])
        longitude = float(stop["longitude"])

        if not -90 <= latitude <= 90:
            raise ValueError("Invalid latitude")

        if not -180 <= longitude <= 180:
            raise ValueError("Invalid longitude")

        coordinates.extend([
            (latitude + 90) / 180,
            (longitude + 180) / 360
        ])

    # Sample 8 positions along the ordered coordinate sequence.
    # Each position contributes latitude and longitude.
    vector = []

    for i in range(8):
        position = round(
            i * (len(coordinates) // 2 - 1) / 7
        )

        vector.extend([
            coordinates[position * 2],
            coordinates[position * 2 + 1]
        ])

    return vector


def update_route_embedding(ride_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT latitude, longitude
                FROM stops
                WHERE ride_id = %s
                ORDER BY sequence_no
                """,
                (ride_id,)
            )

            rows = cur.fetchall()

            if len(rows) < 2:
                raise ValueError(
                    "Ride must have at least two stops"
                )

            stops = [
                {"latitude": row[0], "longitude": row[1]}
                for row in rows
            ]

            embedding = create_route_embedding(stops)

            # pgvector accepts its vector literal format.
            vector_literal = "[" + ",".join(
                str(value) for value in embedding
            ) + "]"

            cur.execute(
                """
                UPDATE rides
                SET route_embedding = %s::vector
                WHERE ride_id = %s
                """,
                (vector_literal, ride_id)
            )

            if cur.rowcount == 0:
                raise ValueError("Ride not found")

    return embedding
