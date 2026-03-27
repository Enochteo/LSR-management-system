"""Attendance business-logic scaffold (Phase 2 + 4).

Keep route handlers thin and put policy checks here.
"""
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from database.models import Student
from extensions import db


class AttendanceService:
    """Service boundary for sign-in/sign-out/enforcement operations."""

    def resolve_or_create_student(self, name, email, student_id):
        """Find existing student or create a new one."""
        name = (name or "").strip()
        email = (email or "").strip().lower()
        student_id = (student_id or "").strip().lower()

        if not name:
            raise ValueError("Must provide a name for the student")
        if not email:
            raise ValueError("Student email must be provided")
        if not student_id:
            raise ValueError("Student must have an ID")

        existing = db.session.execute(
            db.select(Student).where(
                or_(Student.email == email, Student.student_id == student_id)
            )
        ).scalars().all()
        by_email = next((s for s in existing if s.email == email), None)
        by_student_id = next((s for s in existing if s.student_id == student_id), None)

        # If email and student ID point to different users
        if by_email and by_student_id and by_email.id != by_student_id.id:
            raise ValueError("Email and student ID belong to different students")
        
        # Use either of the two objects
        student = by_email or by_student_id

        # Check if a student object was found
        if student:
            # Update any missing fields
            if not student.name:
                student.name = name
            if not student.email:
                student.email = email
            if not student.student_id:
                student.student_id = student_id
            db.session.commit()
        else:  
            # Create new student object
            student = Student(name=name, email=email, student_id=student_id)
            try:
                db.session.add(student)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                raise ValueError("A student with this email or student_id already exists")
        return student

    def validate_room(self, room_identifier):
        """Resolve and validate room from ID or room_code."""
        raise NotImplementedError

    def get_active_session_for_student(self, student_id):
        """Return ACTIVE attendance record if one exists. """
        raise NotImplementedError

    def create_signin_session(self, student, room, now):
        """Create and persist a new ACTIVE attendance session. """
        raise NotImplementedError

    def complete_session(self, attendance_record, end_time, status):
        """Mark session as COMPLETED or EXPIRED and set sign-out timestamp."""
        raise NotImplementedError

    def get_active_sessions(self):
        """Return all ACTIVE sessions for dashboard and enforcement job."""
        raise NotImplementedError
