"""Email notification service.

Sends session lifecycle alerts to students via Flask-Mail.
All send failures are logged and silently swallowed so that
a broken mail config never blocks sign-in or enforcement.
"""

import logging
from datetime import timedelta

from flask import current_app
from flask_mail import Message

from extensions import mail

logger = logging.getLogger(__name__)


class EmailService:
    """Outbound notification logic for session events."""

    def send_30_min_warning(self, record) -> bool:
        """Send a 30-minute remaining warning to the student."""
        return self._send(
            recipient=record.student.email,
            subject="Library session reminder — 30 minutes remaining",
            body=self._build_warning_body(record, minutes_remaining=30),
        )

    def send_10_min_warning(self, record) -> bool:
        """Send a 10-minute remaining warning to the student."""
        return self._send(
            recipient=record.student.email,
            subject="Library session reminder — 10 minutes remaining",
            body=self._build_warning_body(record, minutes_remaining=10),
        )

    def send_session_expired(self, record) -> bool:
        """Notify the student that their session has been auto-expired."""
        expiry_str = record.sign_out_time.strftime("%I:%M %p") if record.sign_out_time else "now"
        html = f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto">
          <h2 style="color:#c0392b">Your library session has ended</h2>
          <p>Hi <strong>{record.student.full_name}</strong>,</p>
          <p>
            Your 3-hour study session in <strong>{record.room.name}</strong>
            ended at <strong>{expiry_str}</strong> and you have been
            automatically signed out.
          </p>
          <p>Thank you for using the library. You are welcome to sign in again
          when a spot is available.</p>
          <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
          <p style="font-size:12px;color:#888">Smart Digital Library System</p>
        </div>
        """
        return self._send(
            recipient=record.student.email,
            subject="Your library session has ended",
            body=html,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _build_warning_body(self, record, minutes_remaining: int) -> str:
        expiry_time = record.sign_in_time + timedelta(
            seconds=current_app.config.get("SESSION_DURATION_SECONDS", 10800)
        )
        expiry_str = expiry_time.strftime("%I:%M %p")
        color = "#e67e22" if minutes_remaining == 30 else "#c0392b"
        return f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto">
          <h2 style="color:{color}">Session ending in {minutes_remaining} minutes</h2>
          <p>Hi <strong>{record.student.full_name}</strong>,</p>
          <p>
            Your study session in <strong>{record.room.name}</strong>
            will expire at <strong>{expiry_str}</strong>
            — that's <strong>{minutes_remaining} minutes</strong> from now.
          </p>
          <p>Please save your work and prepare to leave the room on time.</p>
          <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
          <p style="font-size:12px;color:#888">Smart Digital Library System</p>
        </div>
        """

    def _send(self, recipient: str, subject: str, body: str) -> bool:
        """Send an HTML email. Returns True on success, False on failure."""
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient],
                html=body,
            )
            mail.send(msg)
            logger.info("Email sent to %s: %s", recipient, subject)
            return True
        except Exception as exc:
            logger.error(
                "Failed to send email to %s — %s: %s",
                recipient,
                type(exc).__name__,
                exc,
            )
            return False
