"""
schemas.py — Pydantic models for request/response validation.
"""

from datetime import date, time
from typing import Optional
from pydantic import BaseModel

from backend.models import AttendanceStatus


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------

class EmployeeOut(BaseModel):
    """Employee data returned by the API."""

    id: int
    full_name: str
    department: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class AttendanceCreate(BaseModel):
    """Payload sent by the frontend to register attendance."""

    employee_id: int
    latitude: float
    longitude: float


class AttendanceOut(BaseModel):
    """Full attendance record returned by the API."""

    id: int
    employee_id: int
    attendance_date: date
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    working_hours: Optional[float] = None
    late_minutes: Optional[int] = None
    missing_minutes: Optional[int] = None
    overtime_minutes: Optional[int] = None
    attendance_status: Optional[AttendanceStatus] = None

    model_config = {"from_attributes": True}


class AttendanceResponse(BaseModel):
    """Standard API response envelope for attendance actions."""

    success: bool
    message: str
    action: Optional[str] = None      # "check_in" | "check_out" | "rejected"
    data: Optional[AttendanceOut] = None
    distance: Optional[float] = None
    allowed_radius: Optional[int] = None
