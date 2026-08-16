"""Attendance service — session lifecycle business logic.

All policy checks live here so route handlers stay thin.
Every public method raises ValueError with a human-readable message
on any business rule violation.
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from database.models import AttendanceRecord, Room, Status, Student
from extensions import db

# Minimum and maximum group size for room authorization.
MIN_GROUP_SIZE = 2
MAX_GROUP_SIZE = 6


class AttendanceService:
    """Business rules for sign-in, sign-out, and session enforcement."""

    # ------------------------------------------------------------------ #
    # Student resolution                                                   #
    # ------------------------------------------------------------------ #

    def resolve_or_create_student(
        self, name: str, email: str, student_id: str
    ) -> Student:
        """Return an existing Student or create a new one.

        Normalizes inputs, detects ID/email conflicts, and fills any
        missing fields on existing records before returning.
        """
        name = (name or "").strip()
        email = (email or "").strip().lower()
        student_id = (student_id or "").strip().upper()

        if not name:
            raise ValueError("Full name is required.")
        if not email:
            raise ValueError("Email address is required.")
        if not student_id:
            raise ValueError("Student ID (G-number) is required.")

        by_email = db.session.execute(
            db.select(Student).where(Student.email == email)
        ).scalar_one_or_none()

        by_sid = db.session.execute(
            db.select(Student).where(Student.student_id == student_id)
        ).scalar_one_or_none()

        # Conflict: email and student_id point to different records.
        if by_email and by_sid and by_email.id != by_sid.id:
            raise ValueError(
                "The provided email and student ID belong to different accounts. "
                "Please verify your information."
            )

        student = by_email or by_sid

        if student:
            # Backfill any missing fields without overwriting existing ones.
            if not student.email:
                student.email = email
            if not student.student_id:
                student.student_id = student_id
            if not student.full_name:
                student.full_name = name
            db.session.commit()
        else:
            student = Student(full_name=name, email=email, student_id=student_id)
            try:
                db.session.add(student)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                raise ValueError(
                    "A student with this email or student ID already exists."
                )

        return student

    # ------------------------------------------------------------------ #
    # Room validation                                                      #
    # ------------------------------------------------------------------ #

    def validate_room(self, room_identifier: str) -> Room:
        """Resolve a Room from an integer ID or a room_code string.

        Raises ValueError if the identifier is missing or the room is not found.
        """
        if not room_identifier:
            raise ValueError("Room identifier is required.")

        # Try numeric ID first, then fall back to room_code lookup.
        room = None
        try:
            rid = int(room_identifier)
            room = db.session.get(Room, rid)
        except (ValueError, TypeError):
            pass

        if room is None:
            room = db.session.execute(
                db.select(Room).where(Room.room_code == str(room_identifier).upper())
            ).scalar_one_or_none()

        if room is None:
            raise ValueError(f"Room '{room_identifier}' was not found.")

        return room

    # ------------------------------------------------------------------ #
    # Session queries                                                      #
    # ------------------------------------------------------------------ #

    def get_active_session_for_student(self, student_id: int) -> AttendanceRecord | None:
        """Return the ACTIVE session for a student, or None."""
        return db.session.execute(
            db.select(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == Status.ACTIVE,
            )
            .order_by(AttendanceRecord.sign_in_time.desc())
            .limit(1)
        ).scalar_one_or_none()

    def get_pending_session_for_student(self, student_id: int) -> AttendanceRecord | None:
        """Return the PENDING session for a student, or None."""
        return db.session.execute(
            db.select(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == Status.PENDING,
            )
            .order_by(AttendanceRecord.sign_in_time.desc())
            .limit(1)
        ).scalar_one_or_none()

    def get_active_room_session_count(self, room_id: int) -> int:
        """Return number of currently ACTIVE sessions in a room."""
        return db.session.execute(
            db.select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.status == Status.ACTIVE,
            )
        ).scalar()

    def get_pending_room_session_count(self, room_id: int) -> int:
        """Return number of currently PENDING sessions in a room."""
        return db.session.execute(
            db.select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.status == Status.PENDING,
            )
        ).scalar()

    def get_pending_sessions_for_room(self, room_id: int) -> list[AttendanceRecord]:
        """Return all PENDING sessions for a room, ordered by sign-in time."""
        return db.session.execute(
            db.select(AttendanceRecord)
            .where(
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.status == Status.PENDING,
            )
            .order_by(AttendanceRecord.sign_in_time)
        ).scalars().all()

    def get_active_sessions(self) -> list[AttendanceRecord]:
        """Return all ACTIVE sessions ordered by sign-in time."""
        return db.session.execute(
            db.select(AttendanceRecord)
            .where(AttendanceRecord.status == Status.ACTIVE)
            .order_by(AttendanceRecord.sign_in_time)
        ).scalars().all()

    # ------------------------------------------------------------------ #
    # Sign-in (creates PENDING — awaiting admin authorization)            #
    # ------------------------------------------------------------------ #

    def sign_in(
        self, name: str, email: str, student_id: str, room_identifier: str
    ) -> AttendanceRecord:
        """Main sign-in entry point. Creates a PENDING session awaiting admin authorization.

        Invariants enforced:
        1. Room must exist.
        2. Student must have no existing ACTIVE or PENDING session.
        3. Room must have room for more students (active + pending < capacity).

        Returns the new PENDING AttendanceRecord on success.
        """
        room = self.validate_room(room_identifier)
        student = self.resolve_or_create_student(name, email, student_id)

        existing_active = self.get_active_session_for_student(student.id)
        if existing_active:
            raise ValueError(
                f"You already have an active session in {existing_active.room.name}. "
                "Please sign out before signing in again."
            )

        existing_pending = self.get_pending_session_for_student(student.id)
        if existing_pending:
            raise ValueError(
                f"You already have a pending sign-in request for {existing_pending.room.name}. "
                "Please wait for admin authorization or cancel your request."
            )

        max_capacity = room.capacity or MAX_GROUP_SIZE
        active_count = self.get_active_room_session_count(room.id)
        pending_count = self.get_pending_room_session_count(room.id)

        if active_count >= max_capacity:
            raise ValueError(
                f"{room.name} is currently full ({active_count}/{max_capacity} students). "
                "Please try again later or choose a different room."
            )

        if active_count + pending_count >= max_capacity:
            raise ValueError(
                f"{room.name} already has {active_count + pending_count} students "
                f"waiting or active (max {max_capacity}). "
                "Please try again later or choose a different room."
            )

        return self._create_pending_session(student, room, datetime.utcnow())

    def _create_pending_session(
        self, student: Student, room: Room, now: datetime
    ) -> AttendanceRecord:
        """Insert a new PENDING attendance record. Internal use only."""
        record = AttendanceRecord(
            student_id=student.id,
            room_id=room.id,
            status=Status.PENDING,
            sign_in_time=now,
        )
        try:
            db.session.add(record)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError(
                "You already have a pending request. "
                "This may be a concurrent sign-in attempt."
            )
        return record

    # ------------------------------------------------------------------ #
    # Admin authorization                                                  #
    # ------------------------------------------------------------------ #

    def authorize_room_group(self, room_id: int) -> list[AttendanceRecord]:
        """Authorize all pending sign-ins for a room.

        Requires between MIN_GROUP_SIZE and room capacity students.
        Transitions all PENDING records to ACTIVE and starts their timers.
        """
        records = self.get_pending_sessions_for_room(room_id)

        if not records:
            raise ValueError("No pending sign-ins found for this room.")

        count = len(records)
        room = records[0].room
        max_capacity = room.capacity or MAX_GROUP_SIZE

        if count < MIN_GROUP_SIZE:
            raise ValueError(
                f"At least {MIN_GROUP_SIZE} students must sign in together. "
                f"Only {count} student{'s are' if count != 1 else ' is'} waiting."
            )

        if count > max_capacity:
            raise ValueError(
                f"Group size ({count}) exceeds room capacity ({max_capacity})."
            )

        now = datetime.utcnow()
        for r in records:
            r.status = Status.ACTIVE
            r.sign_in_time = now  # Timer starts from authorization time
            r.admin_authorized_at = now

        db.session.commit()
        return records

    def reject_room_group(self, room_id: int) -> int:
        """Cancel and delete all pending sign-ins for a room.

        Returns the number of records deleted.
        """
        records = self.get_pending_sessions_for_room(room_id)

        if not records:
            raise ValueError("No pending sign-ins found for this room.")

        count = len(records)
        for r in records:
            db.session.delete(r)
        db.session.commit()
        return count

    def cancel_pending_session(self, attendance_id: int) -> None:
        """Allow a student to cancel their own PENDING sign-in request."""
        record = db.session.get(AttendanceRecord, attendance_id)
        if record is None:
            raise ValueError("Session not found.")
        if record.status != Status.PENDING:
            raise ValueError("Only pending sign-in requests can be cancelled.")
        db.session.delete(record)
        db.session.commit()

    # ------------------------------------------------------------------ #
    # Sign-out                                                             #
    # ------------------------------------------------------------------ #

    def manual_sign_out(self, attendance_id: int) -> AttendanceRecord:
        """Manually sign out an ACTIVE session (COMPLETED status)."""
        record = db.session.get(AttendanceRecord, attendance_id)
        if record is None:
            raise ValueError("Session not found.")
        if record.status != Status.ACTIVE:
            raise ValueError("Only active sessions can be signed out.")

        now = datetime.utcnow()
        record.sign_out_time = now
        record.status = Status.COMPLETED
        record.duration = int((now - record.sign_in_time).total_seconds() / 60)
        db.session.commit()
        return record

    def complete_session(
        self,
        attendance_record: AttendanceRecord,
        end_time: datetime,
        status: Status,
    ) -> AttendanceRecord:
        """Transition an ACTIVE session to COMPLETED or EXPIRED.

        Called by the enforcement cycle. Sets duration and flags
        staff_review_required for auto-expired sessions.
        """
        if attendance_record.status != Status.ACTIVE:
            raise ValueError("Only ACTIVE sessions can be completed or expired.")
        if end_time <= attendance_record.sign_in_time:
            raise ValueError("End time must be after sign-in time.")
        if status not in (Status.COMPLETED, Status.EXPIRED):
            raise ValueError("Target status must be COMPLETED or EXPIRED.")

        attendance_record.sign_out_time = end_time
        attendance_record.status = status
        attendance_record.duration = int(
            (end_time - attendance_record.sign_in_time).total_seconds() / 60
        )

        if status == Status.EXPIRED:
            attendance_record.staff_review_required = True

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Failed to update session record.")

        return attendance_record
