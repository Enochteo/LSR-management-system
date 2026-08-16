"""Attendance routes — student sign-in and session countdown."""

from datetime import timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import limiter
from services.attendance_service import AttendanceService

attendance_bp = Blueprint("attendance", __name__)
_svc = AttendanceService()


@attendance_bp.get("/")
def index():
    """Landing page — redirect to sign-in with no room pre-selected."""
    return redirect(url_for("attendance.signin_page"))


@attendance_bp.get("/signin")
def signin_page():
    """Render the sign-in form, optionally pre-filling the room."""
    room_code = request.args.get("room", "").strip().upper()
    room = None

    if room_code:
        try:
            room = _svc.validate_room(room_code)
        except ValueError:
            flash(f"Room code '{room_code}' is not recognised.", "warning")

    return render_template("signin.html", room=room, room_code=room_code)


@attendance_bp.post("/signin")
@limiter.limit("20 per minute")
def signin_submit():
    """Validate form data, create a session, and redirect to the countdown page."""
    name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    student_id = request.form.get("student_id", "").strip()
    room_identifier = request.form.get("room_id", "").strip()

    try:
        record = _svc.sign_in(name, email, student_id, room_identifier)
    except ValueError as exc:
        flash(str(exc), "danger")
        # Preserve room context so the form pre-fills again.
        return redirect(url_for("attendance.signin_page", room=room_identifier))

    return redirect(url_for("attendance.session_status", attendance_id=record.id))


@attendance_bp.get("/session/<int:attendance_id>")
def session_status(attendance_id):
    """Show the countdown page for an active (or completed) session."""
    from database.models import AttendanceRecord

    from extensions import db

    record = db.session.get(AttendanceRecord, attendance_id)
    if record is None:
        flash("Session not found.", "danger")
        return redirect(url_for("attendance.signin_page"))

    from flask import current_app

    max_duration = current_app.config.get("SESSION_DURATION_SECONDS", 10800)
    print(max_duration)
    return render_template(
        "countdown.html",
        record=record,
        max_duration_seconds=max_duration,
        # Convert the UTC-naive datetime to a UTC Unix timestamp (ms) for the JS timer.
        # Using .replace(tzinfo=timezone.utc) prevents Python from interpreting the
        # naive datetime as local time, which would make the countdown wrong.
        sign_in_time_ms=int(
            record.sign_in_time.replace(tzinfo=timezone.utc).timestamp() * 1000
        ),
    )


@attendance_bp.post("/session/lookup")
@limiter.limit("20 per minute")
def session_lookup():
    """Let a student retrieve their active session by email or student ID."""
    identifier = request.form.get("identifier", "").strip().lower()

    if not identifier:
        flash("Please enter your email address or student ID.", "warning")
        return redirect(url_for("attendance.signin_page"))

    from database.models import Student

    from extensions import db

    # Match by email or student_id (case-insensitive).
    student = db.session.execute(
        db.select(Student).where(
            db.or_(
                Student.email == identifier,
                db.func.lower(Student.student_id) == identifier,
            )
        )
    ).scalar_one_or_none()

    if student is None:
        flash("No account found for that email or student ID.", "danger")
        return redirect(url_for("attendance.signin_page"))

    record = _svc.get_active_session_for_student(student.id)

    if record is None:
        flash("You don't have an active session right now.", "info")
        return redirect(url_for("attendance.signin_page"))

    return redirect(url_for("attendance.session_status", attendance_id=record.id))


@attendance_bp.post("/session/<int:attendance_id>/cancel-pending")
def cancel_pending(attendance_id):
    """Cancel a student's own PENDING sign-in request."""
    try:
        _svc.cancel_pending_session(attendance_id)
        flash("Your sign-in request has been cancelled.", "info")
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("attendance.signin_page"))


@attendance_bp.post("/session/<int:attendance_id>/signout")
def sign_out(attendance_id):
    """Manual early sign-out for a student."""
    try:
        _svc.manual_sign_out(attendance_id)
        flash("You have been signed out successfully.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("attendance.signin_page"))
