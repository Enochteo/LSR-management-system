"""Authentication routes — admin login and logout."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from database.models import Student
from extensions import db, limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    return render_template("login.html")


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Email and password are required.", "danger")
        return render_template("login.html"), 400

    student = db.session.execute(
        db.select(Student).where(Student.email == email, Student.is_admin == True)  # noqa: E712
    ).scalar_one_or_none()

    if student is None or not student.check_password(password):
        flash("Invalid email or password.", "danger")
        return render_template("login.html"), 401

    login_user(student, remember=False)
    next_page = request.args.get("next")
    return redirect(next_page or url_for("admin.dashboard"))


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
