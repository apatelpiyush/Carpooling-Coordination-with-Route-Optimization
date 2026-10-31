from app.bookings import bookings_bp
from app.rides import rides_bp
import os
from flask import Flask
from app.auth import auth
from app.pages import pages


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
    app.register_blueprint(auth)
    app.register_blueprint(rides_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(pages)
    return app

