"""Attendance business-logic scaffold (Phase 2 + 4).

Keep route handlers thin and put policy checks here.
"""
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from database.models import Student, Room, AttendanceRecord, Status
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

        # Normalize room
        room_identifier = (room_identifier or "").strip().lower()

        if not room_identifier:
            raise ValueError("No room identifier provided")
        
        room = db.session.execute(
            db.select(Room).where(
                or_(Room.id == room_identifier, Room.room_code == room_identifier)
            )
        ).scalars().all()

        if not room:
            raise ValueError('Room not found')
        return room
        

    def get_active_session_for_student(self, student_id):
        """Return ACTIVE attendance record if one exists."""
        # Normalize student identifier
        if not student_id:
            raise ValueError("Student ID not provided")
        
        student_id = int(student_id)
        
        # Query to find record with student_id and status filter
        records = db.session.execute(
            db.select(AttendanceRecord).where(
                AttendanceRecord.student_id == student_id, 
                AttendanceRecord.status == Status.ACTIVE
                ).order_by(
                    db.desc(AttendanceRecord.sign_in_time)
                    )).scalars().all()
        # return most recent
        return records[0] if records else None

    def create_signin_session(self, student, room, now):
        """Create and persist a new ACTIVE attendance session. """

        # Validate student ID and room ID exist
        if not student.id:
            raise ValueError("Student ID not provided")
        
        if not room_id:
            raise ValueError("Room ID not provided")
        
        student_id = int(student.id)
        room_id = int(room.id)
        # Create new Record Object
        record = AttendanceRecord(student_id=student_id, room_id=room_id, status=Status.ACTIVE, sign_in_time=now)

        # Try adding to the table, check for integrity error
        try:
            db.session.add(record)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('Attendance record already exists')
        return record
    
    def complete_session(self, attendance_record, end_time, status):
        """Mark session as COMPLETED or EXPIRED and set sign-out timestamp."""
        if not end_time:
            raise ValueError("Value Error not provided")
        
        if end_time < attendance_record.sign_in_time:
            raise ValueError("Sign out time is earlier than the sign in time")
        
        try:
            attendance_record.sign_out_time = end_time
            attendance_record.status = status
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('Attendance record update error')
        