"""Session enforcement worker.

Run once per minute via system cron or Flask CLI:
    * cron:  * * * * * cd /path/to/app && flask run-enforcement
    * manual: flask run-enforcement

Algorithm (idempotent — safe to re-run):
    1. Fetch all ACTIVE sessions in a single query.
    2. For each session, compute elapsed time on the server (UTC).
    3. Send 30-min warning once when elapsed >= 2h 30m (alert_30_sent flag).
    4. Send 10-min warning once when elapsed >= 2h 50m (alert_10_sent flag).
    5. When elapsed >= 3h:
       a. Send final expiration alert once (alert_final_sent flag).
       b. Set sign_out_time, status=EXPIRED, staff_review_required=True.
    6. Changes are committed per record to limit blast radius.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def run_enforcement_cycle(now: datetime | None = None) -> dict:
    """Execute one enforcement pass.

    *now* defaults to the current UTC time. Pass an explicit value in
    tests to exercise time-dependent branches deterministically.

    Returns a summary dict with counts of actions taken.
    """
    from database.models import AttendanceRecord, Status
    from extensions import db
    from flask import current_app
    from services.attendance_service import AttendanceService
    from services.email_service import EmailService

    now = now or datetime.utcnow()
    cfg = current_app.config

    warn_30_threshold = cfg.get("WARN_30_THRESHOLD_SECONDS", 9000)   # 2h30m
    warn_10_threshold = cfg.get("WARN_10_THRESHOLD_SECONDS", 10200)  # 2h50m
    max_duration = cfg.get("SESSION_DURATION_SECONDS", 10800)        # 3h

    attendance_svc = AttendanceService()
    email_svc = EmailService()

    active_records = attendance_svc.get_active_sessions()

    summary = {"checked": 0, "warn_30": 0, "warn_10": 0, "expired": 0, "errors": 0}

    for record in active_records:
        summary["checked"] += 1
        try:
            elapsed = (now - record.sign_in_time).total_seconds()

            # ---- 30-minute warning ---- #
            if elapsed >= warn_30_threshold and not record.alert_30_sent:
                sent = email_svc.send_30_min_warning(record)
                record.alert_30_sent = True
                db.session.commit()
                if sent:
                    summary["warn_30"] += 1
                logger.info(
                    "30-min warning sent for session %d (student=%s)",
                    record.id,
                    record.student.email,
                )

            # ---- 10-minute warning ---- #
            if elapsed >= warn_10_threshold and not record.alert_10_sent:
                sent = email_svc.send_10_min_warning(record)
                record.alert_10_sent = True
                db.session.commit()
                if sent:
                    summary["warn_10"] += 1
                logger.info(
                    "10-min warning sent for session %d (student=%s)",
                    record.id,
                    record.student.email,
                )

            # ---- Auto sign-out ---- #
            if elapsed >= max_duration:
                # Send final expiration alert (once).
                if not record.alert_final_sent:
                    record.alert_final_sent = True
                    db.session.commit()
                    email_svc.send_session_expired(record)
                    logger.info(
                        "Expiration alert sent for session %d (student=%s)",
                        record.id,
                        record.student.email,
                    )

                # Expire the session.
                attendance_svc.complete_session(record, now, Status.EXPIRED)
                summary["expired"] += 1
                logger.info(
                    "Session %d expired (student=%s, room=%s)",
                    record.id,
                    record.student.email,
                    record.room.name,
                )

        except Exception as exc:  # pylint: disable=broad-except
            db.session.rollback()
            summary["errors"] += 1
            logger.error(
                "Enforcement error for session %d: %s — %s",
                record.id,
                type(exc).__name__,
                exc,
            )

    logger.info("Enforcement cycle complete: %s", summary)
    return summary


if __name__ == "__main__":
    # Standalone execution: push the app context manually.
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from app import create_app

    flask_app = create_app()
    with flask_app.app_context():
        result = run_enforcement_cycle()
        print(result)
