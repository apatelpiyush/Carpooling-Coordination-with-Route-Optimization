
# from dotenv import load_dotenv
# from app import create_app
# from app.db import test_db_connection
# from flask import jsonify

# load_dotenv()
# app = create_app()


# @app.route("/")
# def home():
#     return "Carpooling Coordination System is running!"


# @app.route("/db-test")
# def db_test():
#     database, user, version = test_db_connection()
#     return jsonify({
#         "status": "success",
#         "database": database,
#         "user": user,
#         "postgresql_version": version,
#     })


# if __name__ == "__main__":
#     app.run(debug=True)

from dotenv import load_dotenv
from app import create_app
from app.db import test_db_connection
from flask import jsonify

load_dotenv()

app = create_app()


@app.route("/db-test")
def db_test():
    database, user, version = test_db_connection()

    return jsonify({
        "status": "success",
        "database": database,
        "user": user,
        "postgresql_version": version
    })


if __name__ == "__main__":
    app.run(debug=True)