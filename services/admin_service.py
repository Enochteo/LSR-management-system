"""Admin service — dashboard queries and staff review operations.

All queries here are read-optimised and return plain dicts or
lightweight data structures for easy template consumption.
"""

from datetime import datetime, date

from sqlalchemy import func

from database.models import AttendanceRecord, Room, Status, Student
from extensions import db
from utils import central_day_bounds, fmt_central, today_central


class AdminService:
    """Dashboard data preparation and admin operations."""

    def get_active_sessions_view(self) -> list[dict]:
        """Return all ACTIVE sessions with computed elapsed time."""
        records = db.session.execute(
            db.select(AttendanceRecord)
            .where(AttendanceRecord.status == Status.ACTIVE)
            .order_by(AttendanceRecord.sign_in_time)
        ).scalars().all()

        return [self._format_active_record(r) for r in records]

    def get_room_occupancy(self) -> list[dict]:
        """Return occupancy summary for every room."""
        rooms = db.session.execute(db.select(Room).order_by(Room.name)).scalars().all()

        active_counts = dict(
            db.session.execute(
                db.select(
                    AttendanceRecord.room_id,
                    func.count(AttendanceRecord.id),
                )
                .where(AttendanceRecord.status == Status.ACTIVE)
                .group_by(AttendanceRecord.room_id)
            ).all()
        )

        return [
            {
                "id": room.id,
                "name": room.name,
                "room_code": room.room_code,
                "capacity": room.capacity,
                "active_count": active_counts.get(room.id, 0),
                "qr_code_path": room.qr_code_path,
            }
            for room in rooms
        ]

    def get_daily_sessions(self, target_date: date | None = None) -> list[dict]:
        """Return all sessions whose sign-in falls on *target_date* (Central Time).

        Defaults to today in Central Time if no date is given.
        """
        if target_date is None:
            target_date = today_central()

        day_start, day_end = central_day_bounds(target_date)

        records = db.session.execute(
            db.select(AttendanceRecord)
            .where(
                AttendanceRecord.sign_in_time >= day_start,
                AttendanceRecord.sign_in_time <= day_end,
            )
            .order_by(AttendanceRecord.sign_in_time)
        ).scalars().all()

        return [self._format_record(r) for r in records]

    def get_pending_auth_queue(self) -> list[dict]:
        """Return rooms with pending sign-in groups awaiting admin authorization.

        Groups PENDING records by room and annotates each group with occupant
        details and whether the group meets the minimum size requirement.
        """
        records = db.session.execute(
            db.select(AttendanceRecord)
            .where(AttendanceRecord.status == Status.PENDING)
            .order_by(AttendanceRecord.room_id, AttendanceRecord.sign_in_time)
        ).scalars().all()

        # Group by room_id, preserving insertion order.
        room_groups: dict[int, dict] = {}
        for r in records:
            if r.room_id not in room_groups:
                room_groups[r.room_id] = {
                    "room_id": r.room_id,
                    "room_name": r.room.name,
                    "room_code": r.room.room_code,
                    "capacity": r.room.capacity,
                    "students": [],
                    "earliest_request": r.sign_in_time,
                }
            room_groups[r.room_id]["students"].append({
                "record_id": r.id,
                "name": r.student.full_name,
                "student_id": r.student.student_id,
                "email": r.student.email,
                "requested_at": fmt_central(r.sign_in_time, "%I:%M %p CT"),
            })
            if r.sign_in_time < room_groups[r.room_id]["earliest_request"]:
                room_groups[r.room_id]["earliest_request"] = r.sign_in_time

        result = []
        for group in room_groups.values():
            count = len(group["students"])
            result.append({
                **group,
                "student_count": count,
                "can_authorize": count >= 2,
                "waiting_since": fmt_central(group["earliest_request"], "%I:%M %p CT"),
            })

        # Sort by who has been waiting longest.
        result.sort(key=lambda x: x["earliest_request"])
        return result

    def get_staff_review_queue(self) -> list[dict]:
        """Return auto-expired sessions pending staff review."""
        records = db.session.execute(
            db.select(AttendanceRecord)
            .where(
                AttendanceRecord.staff_review_required == True,  # noqa: E712
                AttendanceRecord.staff_reviewed_at == None,  # noqa: E711
            )
            .order_by(AttendanceRecord.sign_out_time.desc())
        ).scalars().all()

        return [self._format_record(r) for r in records]

    def mark_reviewed(
        self, attendance_id: int, notes: str = ""
    ) -> AttendanceRecord:
        """Mark a session as staff-reviewed."""
        record = db.session.get(AttendanceRecord, attendance_id)
        if record is None:
            raise ValueError("Session not found.")
        if not record.staff_review_required:
            raise ValueError("This session does not require staff review.")

        record.staff_reviewed_at = datetime.utcnow()
        record.staff_review_notes = notes.strip() or None
        db.session.commit()
        return record

    def get_dashboard_stats(self) -> dict:
        """Return high-level metrics for the dashboard header."""
        active_count = db.session.execute(
            db.select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.status == Status.ACTIVE
            )
        ).scalar()

        review_count = db.session.execute(
            db.select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.staff_review_required == True,  # noqa: E712
                AttendanceRecord.staff_reviewed_at == None,  # noqa: E711
            )
        ).scalar()

        pending_auth_count = db.session.execute(
            db.select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.status == Status.PENDING
            )
        ).scalar()

        day_start, _ = central_day_bounds(today_central())
        today_count = db.session.execute(
            db.select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.sign_in_time >= day_start
            )
        ).scalar()

        total_rooms = db.session.execute(
            db.select(func.count(Room.id))
        ).scalar()

        return {
            "active_sessions": active_count,
            "pending_auth": pending_auth_count,
            "review_pending": review_count,
            "today_signins": today_count,
            "total_rooms": total_rooms,
        }

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _format_active_record(self, r: AttendanceRecord) -> dict:
        elapsed = int(r.elapsed_seconds / 60)
        remaining = max(0, int(r.remaining_seconds / 60))
        return {
            "id": r.id,
            "student_name": r.student.full_name,
            "student_id": r.student.student_id,
            "room_name": r.room.name,
            "sign_in_time": fmt_central(r.sign_in_time, "%b %d, %I:%M %p CT"),
            "elapsed_minutes": elapsed,
            "remaining_minutes": remaining,
            "expiry_time": fmt_central(r.expiry_time, "%I:%M %p CT"),
            "alert_30_sent": r.alert_30_sent,
            "alert_10_sent": r.alert_10_sent,
        }

    def _format_record(self, r: AttendanceRecord) -> dict:
        return {
            "id": r.id,
            "student_name": r.student.full_name,
            "student_id": r.student.student_id,
            "student_email": r.student.email,
            "room_name": r.room.name,
            "room_code": r.room.room_code,
            "sign_in_time": fmt_central(r.sign_in_time, "%Y-%m-%d %I:%M %p CT"),
            "sign_out_time": fmt_central(r.sign_out_time, "%Y-%m-%d %I:%M %p CT"),
            "duration": r.duration,
            "status": r.status.value,
            "staff_review_required": r.staff_review_required,
            "staff_reviewed_at": fmt_central(r.staff_reviewed_at, "%Y-%m-%d %I:%M %p CT"),
            "staff_review_notes": r.staff_review_notes,
        }
