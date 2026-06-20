"""
models.py — SQLAlchemy ORM models for the attendance system.
"""

import enum
from datetime import date, time
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, Time, Float, ForeignKey, Enum
)
from sqlalchemy.orm import relationship

from backend.database import Base


class AttendanceStatus(str, enum.Enum):
    """Valid attendance status values."""
    PRESENT = "Present"
    LATE = "Late"
    EARLY_LEAVE = "Early Leave"
    COMPLETED = "Completed"


class Employee(Base):
    """Represents a company employee."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship
    attendances = relationship("Attendance", back_populates="employee")

    def __repr__(self) -> str:
        return f"<Employee id={self.id} name={self.full_name!r}>"


class Attendance(Base):
    """Represents a single day's attendance record for one employee."""

    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    check_in = Column(Time, nullable=True)
    check_out = Column(Time, nullable=True)
    working_hours = Column(Float, nullable=True)        # Decimal hours
    late_minutes = Column(Integer, nullable=True, default=0)
    missing_minutes = Column(Integer, nullable=True, default=0)
    overtime_minutes = Column(Integer, nullable=True, default=0)
    attendance_status = Column(
        Enum(AttendanceStatus),
        nullable=True,
        default=AttendanceStatus.PRESENT,
    )

    # Relationship
    employee = relationship("Employee", back_populates="attendances")

    def __repr__(self) -> str:
        return (
            f"<Attendance id={self.id} employee_id={self.employee_id} "
            f"date={self.attendance_date} status={self.attendance_status}>"
        )
