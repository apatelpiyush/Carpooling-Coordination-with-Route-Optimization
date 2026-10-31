
from flask import Blueprint, render_template, session, redirect, url_for

pages = Blueprint("pages", __name__)


@pages.route("/")
def home():
    return render_template("index.html")


@pages.route("/login")
def login_page():
    if session.get("user_id"):
        return redirect(url_for("pages.dashboard"))
    return render_template("login.html")


@pages.route("/register")
def register_page():
    if session.get("user_id"):
        return redirect(url_for("pages.dashboard"))
    return render_template("register.html")


@pages.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("pages.login_page"))
    return render_template("dashboard.html")


@pages.route("/rides")
def rides_page():
    if not session.get("user_id"):
        return redirect(url_for("pages.login_page"))
    return render_template("rides.html")


@pages.route("/rides/<int:ride_id>")
def ride_details_page(ride_id):
    if not session.get("user_id"):
        return redirect(url_for("pages.login_page"))
    return render_template("ride_details.html", ride_id=ride_id)
