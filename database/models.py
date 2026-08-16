import enum
from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class Status(enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class Student(UserMixin, db.Model):
    """Represents a student or admin user in the system."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, index=True, nullable=False)
    student_id = db.Column(db.String, unique=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)
    password_hash = db.Column(db.String, nullable=True)  # Only set for admin users

    attendance_records = db.relationship(
        "AttendanceRecord", back_populates="student", lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Room(db.Model):
    """Represents a library study room that students sign into."""

    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer, default=6, nullable=False)
    room_code = db.Column(db.String, unique=True, nullable=False)
    qr_code_path = db.Column(db.String, nullable=True)

    attendance_records = db.relationship(
        "AttendanceRecord", back_populates="room", lazy="dynamic"
    )


class AttendanceRecord(db.Model):
    """Tracks sign-in/out sessions with enforcement flags and review state."""

    __tablename__ = "attendance_records"

    __table_args__ = (
        # sign_out_time, when present, must come after sign_in_time.
        db.CheckConstraint(
            "sign_out_time IS NULL OR sign_out_time > sign_in_time",
            name="ck_attendance_signout_after_signin",
        ),
        # Duration, when set, must be non-negative.
        db.CheckConstraint(
            "duration IS NULL OR duration >= 0",
            name="ck_attendance_duration_non_negative",
        ),
        # Enforce at most one ACTIVE record per student.
        db.Index(
            "uq_attendance_one_active_per_student",
            "student_id",
            unique=True,
            sqlite_where=db.text("status = 'ACTIVE'"),
            postgresql_where=db.text("status = 'ACTIVE'"),
        ),
        # Enforce at most one PENDING record per student.
        db.Index(
            "uq_attendance_one_pending_per_student",
            "student_id",
            unique=True,
            sqlite_where=db.text("status = 'PENDING'"),
            postgresql_where=db.text("status = 'PENDING'"),
        ),
        # Query-performance indexes.
        db.Index("ix_attendance_student_status", "student_id", "status"),
        db.Index("ix_attendance_room_signin", "room_id", "sign_in_time"),
        db.Index("ix_attendance_sign_in_time", "sign_in_time"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    sign_in_time = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    sign_out_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.Enum(Status, name="status_enum"),
        nullable=False,
        default=Status.ACTIVE,
    )
    duration = db.Column(db.Integer, nullable=True)  # Session length in minutes

    # One-time alert flags — prevent duplicate notifications.
    alert_30_sent = db.Column(db.Boolean, default=False, nullable=False)
    alert_10_sent = db.Column(db.Boolean, default=False, nullable=False)
    alert_final_sent = db.Column(db.Boolean, default=False, nullable=False)

    # Admin authorization — set when an admin approves a pending room group.
    admin_authorized_at = db.Column(db.DateTime, nullable=True)

    # Staff review fields for auto-expired sessions.
    staff_review_required = db.Column(db.Boolean, default=False, nullable=False)
    staff_reviewed_at = db.Column(db.DateTime, nullable=True)
    staff_review_notes = db.Column(db.Text, nullable=True)

    student = db.relationship("Student", back_populates="attendance_records")
    room = db.relationship("Room", back_populates="attendance_records")

    @property
    def elapsed_seconds(self) -> float:
        """Seconds elapsed since sign-in (uses sign_out_time if session ended)."""
        end = self.sign_out_time or datetime.utcnow()
        return (end - self.sign_in_time).total_seconds()

    @property
    def remaining_seconds(self) -> float:
        """Seconds remaining in the 3-hour window. Negative once expired."""
        from flask import current_app
        max_duration = current_app.config.get("SESSION_DURATION_SECONDS", 10800)
        return max_duration - self.elapsed_seconds

    @property
    def expiry_time(self):
        """UTC datetime when this session is scheduled to expire."""
        from flask import current_app
        max_duration = current_app.config.get("SESSION_DURATION_SECONDS", 10800)
        return self.sign_in_time + timedelta(seconds=max_duration)
