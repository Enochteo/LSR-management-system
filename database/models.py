from extensions import db


class Student(db.Model):
    __tablename__ = "students"

    # TODO: Add model columns and relationships.
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, index=True, nullable=False)
    student_id = db.Column(db.String, unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    attendance_records = db.relationship("AttendanceRecord", back_populates="student")


class Room(db.Model):
    """Represents a study room that can be signed into.

    Suggested fields to implement:
    - id: Integer primary key
    - name: String, required
    - capacity: Integer, optional
    - room_code: String/UUID, unique; used in QR URLs
    - qr_code_path: String, optional persisted image path

    Suggested relationships:
    - attendance_records: one-to-many AttendanceRecord
    """

    __tablename__ = "rooms"

    # TODO: Add model columns and relationships.
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer)
    room_code = db.Column(db.String, unique=True)
    qr_code_path = db.Column(db.String)
    
    attendance_redords = db.relationship("AttendanceRecord", back_populates="room")



class AttendanceRecord(db.Model):
    """Tracks sign-in/out sessions and enforcement flags.

    Suggested fields to implement:
    - id: Integer primary key
    - student_id: FK -> students.id
    - room_id: FK -> rooms.id
    - sign_in_time: DateTime, required
    - sign_out_time: DateTime, nullable
    - status: Enum/String (ACTIVE, COMPLETED, EXPIRED)
    - duration_minutes: Integer or computed property
    - alert_30_sent: Boolean default False
    - alert_10_sent: Boolean default False

    Suggested constraints/indexes:
    - Prevent >1 ACTIVE record per student
    - sign_out_time > sign_in_time when present
    - indexes on (student_id, status), (room_id, sign_in_time), sign_in_time
    """

    __tablename__ = "attendance_records"

    # TODO: Add model columns, constraints, and helper properties.
    pass
