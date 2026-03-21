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

