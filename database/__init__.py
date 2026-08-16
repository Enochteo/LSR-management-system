"""Database package scaffold.

This package should contain model declarations and DB bootstrap helpers.
"""

from .models import AttendanceRecord, Room, Student

__all__ = ["Student", "Room", "AttendanceRecord"]
