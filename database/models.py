from extensions import db


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
    
    attendance_redords = db.relationship("AttendanceRecord", back_populates="room")



