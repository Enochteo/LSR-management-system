"""QR code generation service.

Generates PNG QR images encoding the room sign-in URL and
persists them under static/qr/ so Flask can serve them directly.
"""

import logging
import os

import qrcode
import qrcode.constants

from extensions import db

logger = logging.getLogger(__name__)


class QRService:
    """Generate and persist QR images for room sign-in URLs."""

    def build_room_signin_url(self, room_code: str) -> str:
        """Return the full sign-in URL for a given room code."""
        from flask import current_app

        base_url = current_app.config.get("APP_BASE_URL", "http://localhost:5000")
        return f"{base_url}/signin?room={room_code}"

    def generate_room_qr_image(self, room, output_dir: str) -> str:
        """Create a QR PNG for *room* and save it to *output_dir*.

        Updates room.qr_code_path in the database and returns the
        relative path suitable for url_for('static', filename=...).
        """
        url = self.build_room_signin_url(room.room_code)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        os.makedirs(output_dir, exist_ok=True)
        filename = f"room_{room.room_code}.png"
        filepath = os.path.join(output_dir, filename)
        img.save(filepath)

        relative_path = f"qr/{filename}"
        room.qr_code_path = relative_path
        db.session.commit()

        logger.info("QR code generated for room '%s' → %s", room.room_code, filepath)
        return relative_path
