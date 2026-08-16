"""Admin routes — dashboard, daily log, staff review, and exports.

All routes require an authenticated admin user.
"""

from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from services.admin_service import AdminService
from services.report_service import ReportService

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
_admin_svc = AdminService()
_report_svc = ReportService()


def _require_admin():
    """Abort with 403 if the current user is not an admin."""
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


def _require_superuser():
    """Abort with 403 if the current user is not a superuser."""
    if not current_user.is_authenticated or not current_user.is_superuser:
        abort(403)


# ------------------------------------------------------------------ #
# Dashboard                                                           #
# ------------------------------------------------------------------ #


@admin_bp.get("/")
@login_required
def index():
    return redirect(url_for("admin.dashboard"))


@admin_bp.get("/dashboard")
@login_required
def dashboard():
    _require_admin()
    stats = _admin_svc.get_dashboard_stats()
    active_sessions = _admin_svc.get_active_sessions_view()
    room_occupancy = _admin_svc.get_room_occupancy()
    return render_template(
        "admin_dashboard.html",
        stats=stats,
        active_sessions=active_sessions,
        room_occupancy=room_occupancy,
    )


# ------------------------------------------------------------------ #
# Session management                                                  #
# ------------------------------------------------------------------ #


@admin_bp.post("/session/<int:record_id>/end")
@login_required
def end_session(record_id):
    """Admin action: manually end an active session (marks COMPLETED)."""
    _require_admin()
    from services.attendance_service import AttendanceService

    try:
        AttendanceService().manual_sign_out(record_id)
        flash("Session ended successfully.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("admin.dashboard"))


# ------------------------------------------------------------------ #
# Daily log                                                           #
# ------------------------------------------------------------------ #


@admin_bp.get("/daily-log")
@login_required
def daily_log():
    _require_admin()
    date_str = request.args.get("date", "")
    selected_date = None
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "warning")

    sessions = _admin_svc.get_daily_sessions(selected_date)
    label_date = selected_date or datetime.utcnow().date()
    return render_template(
        "admin_daily_log.html",
        sessions=sessions,
        selected_date=label_date.isoformat(),
        label_date=label_date.strftime("%B %d, %Y"),
    )


# ------------------------------------------------------------------ #
# Approval queue — admin authorization of pending room sign-ins       #
# ------------------------------------------------------------------ #


@admin_bp.get("/review-queue")
@login_required
def review_queue():
    _require_admin()
    pending_groups = _admin_svc.get_pending_auth_queue()
    return render_template("admin_review_queue.html", pending_groups=pending_groups)


@admin_bp.post("/authorize-room/<int:room_id>")
@login_required
def authorize_room(room_id):
    """Grant room access to the pending group (requires 2–6 students)."""
    _require_admin()
    from services.attendance_service import AttendanceService

    try:
        records = AttendanceService().authorize_room_group(room_id)
        flash(
            f"Access granted — {len(records)} student(s) can now use the room.",
            "success",
        )
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("admin.review_queue"))


@admin_bp.post("/reject-room/<int:room_id>")
@login_required
def reject_room(room_id):
    """Reject and clear the pending sign-in group for a room."""
    _require_admin()
    from services.attendance_service import AttendanceService

    try:
        count = AttendanceService().reject_room_group(room_id)
        flash(f"Sign-in request rejected — {count} pending record(s) removed.", "warning")
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("admin.review_queue"))


# ------------------------------------------------------------------ #
# Exports                                                             #
# ------------------------------------------------------------------ #


@admin_bp.get("/export/csv")
@login_required
def export_csv():
    _require_admin()
    selected_date = _parse_date_param(request.args.get("date", ""))
    label = (selected_date or datetime.utcnow().date()).strftime("%Y-%m-%d")

    csv_bytes = _report_svc.render_daily_csv(selected_date)
    response = make_response(csv_bytes)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="attendance_{label}.csv"'
    )
    return response


@admin_bp.get("/export/pdf")
@login_required
def export_pdf():
    _require_admin()
    selected_date = _parse_date_param(request.args.get("date", ""))
    label = (selected_date or datetime.utcnow().date()).strftime("%Y-%m-%d")

    try:
        pdf_bytes = _report_svc.render_daily_pdf(selected_date)
    except RuntimeError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin.daily_log"))

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="attendance_{label}.pdf"'
    )
    return response


# ------------------------------------------------------------------ #
# Room management                                                     #
# ------------------------------------------------------------------ #


@admin_bp.get("/rooms")
@login_required
def rooms():
    _require_admin()
    room_occupancy = _admin_svc.get_room_occupancy()
    return render_template("admin_rooms.html", rooms=room_occupancy)


@admin_bp.post("/rooms")
@login_required
def create_room():
    _require_superuser()
    from database.models import Room
    from extensions import db

    name = request.form.get("name", "").strip()
    room_code = request.form.get("room_code", "").strip().upper()
    capacity = request.form.get("capacity", "6").strip()

    if not name or not room_code:
        flash("Room name and code are required.", "danger")
        return redirect(url_for("admin.rooms"))

    try:
        cap = int(capacity)
        if cap < 1:
            raise ValueError
    except ValueError:
        cap = 6

    existing = db.session.execute(
        db.select(Room).where(Room.room_code == room_code)
    ).scalar_one_or_none()
    if existing:
        flash(f"Room code '{room_code}' is already in use.", "danger")
        return redirect(url_for("admin.rooms"))

    room = Room(name=name, room_code=room_code, capacity=cap)
    db.session.add(room)
    db.session.commit()
    flash(f"Room '{name}' created successfully.", "success")
    return redirect(url_for("admin.rooms"))


@admin_bp.post("/rooms/<int:room_id>/delete")
@login_required
def delete_room(room_id):
    _require_superuser()
    from database.models import AttendanceRecord, Room, Status
    from extensions import db

    room = db.session.get(Room, room_id)
    if room is None:
        flash("Room not found.", "danger")
        return redirect(url_for("admin.rooms"))

    # Block deletion while any session (active or pending) is in progress.
    occupied = db.session.execute(
        db.select(db.func.count(AttendanceRecord.id)).where(
            AttendanceRecord.room_id == room_id,
            AttendanceRecord.status.in_([Status.ACTIVE, Status.PENDING]),
        )
    ).scalar()

    if occupied:
        flash(
            f"Cannot delete '{room.name}': {occupied} active or pending session(s) in progress.",
            "danger",
        )
        return redirect(url_for("admin.rooms"))

    name = room.name
    db.session.delete(room)
    db.session.commit()
    flash(f"Room '{name}' deleted.", "success")
    return redirect(url_for("admin.rooms"))


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def _parse_date_param(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
