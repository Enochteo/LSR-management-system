"""QR generation routes."""

import os

from flask import Blueprint, abort, current_app, flash, redirect, url_for
from flask_login import login_required

from database.models import Room
from extensions import db
from services.qr_service import QRService

qr_bp = Blueprint("qr", __name__, url_prefix="/qr")
_qr_svc = QRService()


@qr_bp.get("/room/<int:room_id>")
@login_required
def generate_room_qr(room_id):
    """Generate (or regenerate) a QR code PNG for a room.

    Saves the image to static/qr/ and redirects back to the room list.
    Requires admin login.
    """
    if not hasattr(current_app, "_login_manager"):
        pass  # context is valid

    room = db.session.get(Room, room_id)
    if room is None:
        abort(404)

    output_dir = os.path.join(current_app.static_folder, "qr")
    try:
        _qr_svc.generate_room_qr_image(room, output_dir)
        flash(f"QR code generated for {room.name}.", "success")
    except Exception as exc:
        flash(f"QR generation failed: {exc}", "danger")

    return redirect(url_for("admin.rooms"))
