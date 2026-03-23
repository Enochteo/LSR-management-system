from extensions import db
import enum

class Status(enum.Enum):
    ACTIVE = 'ACTIVE'
    COMPLETED = 'COMPLETED'
    EXPIRED = 'EXPIRED'

class Student(db.Model):
    """Represents each user from a regular student to an admin"""
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, index=True, nullable=False)
    student_id = db.Column(db.String, unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    attendance_records = db.relationship("AttendanceRecord", back_populates="student")


class Room(db.Model):
    """Represents a study room that can be signed into."""

    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer)
    room_code = db.Column(db.String, unique=True)
    qr_code_path = db.Column(db.String)
    
    attendance_records = db.relationship("AttendanceRecord", back_populates="room")


class AttendanceRecord(db.Model):
    """Tracks sign-in/out sessions and enforcement flags."""

    __tablename__ = "attendance_records"

    __table_args__ = (
        # Ensure sign-out, when present, is after sign-in.
        db.CheckConstraint(
            "sign_out_time IS NULL OR sign_out_time > sign_in_time",
            name="ck_attendance_signout_after_signin",
        ),
        # Optional duration value must be non-negative.
        db.CheckConstraint(
            "duration IS NULL OR duration >= 0",
            name="ck_attendance_duration_non_negative",
        ),
        # Prevent more than one ACTIVE record per student.
        db.Index(
            "uq_attendance_one_active_per_student",
            "student_id",
            unique=True,
            sqlite_where=db.text("status = 'ACTIVE'"),
            postgresql_where=db.text("status = 'ACTIVE'"),
        ),
        # Query-performance indexes.
        db.Index("ix_attendance_student_status", "student_id", "status"),
        db.Index("ix_attendance_room_signin", "room_id", "sign_in_time"),
        db.Index("ix_attendance_sign_in_time", "sign_in_time"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    sign_in_time = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    sign_out_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.Enum(Status, name="status_enum"),
        nullable=False,
        default=Status.ACTIVE,
    )
    duration = db.Column(db.Integer)
    alert_30_sent = db.Column(db.Boolean, default=False, nullable=False)
    alert_10_sent = db.Column(db.Boolean, default=False)
    student = db.relationship("Student", back_populates="attendance_records")
    room = db.relationship("Room", back_populates="attendance_records")
