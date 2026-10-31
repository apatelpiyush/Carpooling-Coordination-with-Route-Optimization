
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import get_db_connection

auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")
    is_driver = data.get("is_driver", False)

    if not all([name, email, phone, password]):
        return jsonify({"error": "All fields are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    if not isinstance(is_driver, bool):
        return jsonify({"error": "is_driver must be true or false"}), 400

    password_hash = generate_password_hash(password)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users
                        (name, email, phone, password_hash, is_driver)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING user_id, name, email, is_driver
                    """,
                    (name, email, phone, password_hash, is_driver),
                )
                user = cur.fetchone()

        return jsonify({
            "message": "Registration successful",
            "user": {
                "user_id": user[0],
                "name": user[1],
                "email": user[2],
                "is_driver": user[3],
            },
        }), 201

    except Exception as exc:
        # PostgreSQL unique constraint violation: duplicate email or phone.
        if getattr(exc, "sqlstate", None) == "23505":
            return jsonify({
                "error": "Email or phone number is already registered"
            }), 409
        raise


@auth.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, name, email, password_hash, is_driver
                FROM users
                WHERE email = %s
                """,
                (email,),
            )
            user = cur.fetchone()

    if not user or not check_password_hash(user[3], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session.clear()
    session["user_id"] = user[0]

    return jsonify({
        "message": "Login successful",
        "user": {
            "user_id": user[0],
            "name": user[1],
            "email": user[2],
            "is_driver": user[4],
        },
    })


@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})
    

@auth.route("/me", methods=["GET"])
def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Please log in first"}), 401

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, name, email, phone, is_driver
                FROM users
                WHERE user_id = %s
                """,
                (user_id,)
            )
            user = cur.fetchone()

    if not user:
        session.clear()
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user": {
            "user_id": user[0],
            "name": user[1],
            "email": user[2],
            "phone": user[3],
            "is_driver": user[4]
        }
    }), 200

