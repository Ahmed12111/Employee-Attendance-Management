"""
services.py — Core business logic for the attendance system.

All functions are pure, testable, and decoupled from FastAPI.
"""

import io
import logging
from datetime import date, datetime, time, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.models import Attendance, AttendanceStatus, Employee
from backend.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORK_START        = settings.WORK_START
WORK_END          = settings.WORK_END
ATTENDANCE_OPEN   = settings.ATTENDANCE_OPEN
ATTENDANCE_CLOSE  = settings.ATTENDANCE_CLOSE
RESET_HOUR        = settings.RESET_HOUR
EGYPT_TZ          = ZoneInfo("Africa/Cairo")


def egypt_now() -> datetime:
    """Return the current datetime in Egypt timezone."""
    return datetime.now(EGYPT_TZ)


def egypt_today() -> date:
    """Return today's date according to Egypt timezone."""
    return egypt_now().date()


def is_day_closed() -> bool:
    """Return True if Egypt time is at or after 8 PM (stats reset hour)."""
    return egypt_now().hour >= RESET_HOUR


def is_too_early() -> bool:
    """Return True if Egypt time is before 8 AM (attendance not open yet)."""
    return egypt_now().time() < ATTENDANCE_OPEN


def is_too_late() -> bool:
    """Return True if Egypt time is at or after 6 PM (attendance window closed)."""
    return egypt_now().time() >= ATTENDANCE_CLOSE

# ---------------------------------------------------------------------------
# Employee helpers
# ---------------------------------------------------------------------------


def get_active_employees(db: Session) -> List[Employee]:
    """Return all active employees ordered by name."""
    return (
        db.query(Employee)
        .filter(Employee.is_active == True)  # noqa: E712
        .order_by(Employee.full_name)
        .all()
    )


# ---------------------------------------------------------------------------
# Time calculation helpers
# ---------------------------------------------------------------------------


def _time_to_minutes(t: time) -> int:
    """Convert a time object to total minutes since midnight."""
    return t.hour * 60 + t.minute


def calculate_late_minutes(check_in: time) -> int:
    """Return how many minutes after WORK_START the employee arrived."""
    start = _time_to_minutes(WORK_START)
    actual = _time_to_minutes(check_in)
    return max(0, actual - start)


def calculate_working_hours(check_in: time, check_out: time) -> float:
    """Return total hours worked as a decimal (e.g. 7.5)."""
    today = date.today()
    dt_in = datetime.combine(today, check_in)
    dt_out = datetime.combine(today, check_out)
    delta = dt_out - dt_in
    return round(delta.total_seconds() / 3600, 2)


def calculate_missing_minutes(check_out: time) -> int:
    """Return how many minutes the employee left before WORK_END."""
    end = _time_to_minutes(WORK_END)
    actual = _time_to_minutes(check_out)
    return max(0, end - actual)


def calculate_overtime_minutes(check_out: time) -> int:
    """Return how many minutes past WORK_END the employee stayed."""
    end = _time_to_minutes(WORK_END)
    actual = _time_to_minutes(check_out)
    return max(0, actual - end)


def determine_status(
    late_minutes: int,
    missing_minutes: int,
    overtime_minutes: int,
) -> AttendanceStatus:
    """Derive the attendance status from the calculated metrics."""
    if missing_minutes > 0:
        return AttendanceStatus.EARLY_LEAVE
    return AttendanceStatus.COMPLETED


# ---------------------------------------------------------------------------
# Main attendance registration
# ---------------------------------------------------------------------------


def register_attendance(employee_id: int, db: Session) -> dict:
    """
    Determine and execute check-in or check-out for the given employee.

    Valid registration window: 08:00 AM – 06:00 PM Egypt time.
    Returns a dict with keys: success, action, message, record.
    """
    # ── Too early ────────────────────────────────────────────────────────
    if is_too_early():
        return {
            "success": False,
            "action": "rejected",
            "message": "Attendance not open yet. Doors open at 8:00 AM.",
            "record": None,
        }

    # ── Too late ────────────────────────────────────────────────────────
    if is_too_late():
        return {
            "success": False,
            "action": "rejected",
            "message": "Attendance closed. Registration not allowed after 6:00 PM.",
            "record": None,
        }

    today = egypt_today()
    now   = egypt_now().time().replace(second=0, microsecond=0)

    # Fetch today's existing record (if any)
    record: Optional[Attendance] = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == today,
        )
        .first()
    )

    # ── Case 1: No record today → Check-In ──────────────────────────────────
    if record is None:
        late = calculate_late_minutes(now)
        status = AttendanceStatus.LATE if late > 0 else AttendanceStatus.PRESENT

        record = Attendance(
            employee_id=employee_id,
            attendance_date=today,
            check_in=now,
            late_minutes=late,
            attendance_status=status,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(f"Check-In registered for employee_id={employee_id}")

        return {
            "success": True,
            "action": "check_in",
            "message": "Check-In registered successfully ✓",
            "record": record,
        }

    # ── Case 2: Check-In exists, no Check-Out → Check-Out ───────────────────
    if record.check_in is not None and record.check_out is None:
        missing = calculate_missing_minutes(now)
        overtime = calculate_overtime_minutes(now)
        working = calculate_working_hours(record.check_in, now)
        status = determine_status(record.late_minutes or 0, missing, overtime)

        record.check_out = now
        record.working_hours = working
        record.missing_minutes = missing
        record.overtime_minutes = overtime
        record.attendance_status = status

        db.commit()
        db.refresh(record)

        logger.info(f"Check-Out registered for employee_id={employee_id}")

        return {
            "success": True,
            "action": "check_out",
            "message": "Check-Out registered successfully ✓",
            "record": record,
        }

    # ── Case 3: Both exist → Reject ─────────────────────────────────────────
    return {
        "success": False,
        "action": "rejected",
        "message": "You have already completed today's attendance.",
        "record": record,
    }


# ---------------------------------------------------------------------------
# Excel reporting
# ---------------------------------------------------------------------------


def generate_excel_report(db: Session) -> io.BytesIO:
    """
    Generate an Excel report of all attendance records dynamically in memory.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        logger.error("openpyxl is not installed.")
        raise

    wb = openpyxl.Workbook()
    # Remove the default empty sheet
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    # Fetch all records
    records = db.query(Attendance).order_by(Attendance.attendance_date).all()
    employees = {emp.id: emp.full_name for emp in db.query(Employee).all()}

    # Group records by month-year and week
    grouped_records = {}
    for record in records:
        month_year = record.attendance_date.strftime("%b %Y")  # Short month to save sheet name space
        day = record.attendance_date.day
        
        if day <= 7:
            week = "Week 1"
        elif day <= 14:
            week = "Week 2"
        elif day <= 21:
            week = "Week 3"
        else:
            week = "Week 4"
            
        sheet_key = f"{month_year} - {week}"
        if sheet_key not in grouped_records:
            grouped_records[sheet_key] = []
        grouped_records[sheet_key].append(record)

    if not grouped_records:
        ws = wb.create_sheet(title="No Data")
        ws.cell(row=1, column=1, value="No attendance records found.")
    else:
        for sheet_title, month_records in grouped_records.items():
            # Excel sheet names max 31 chars
            ws = wb.create_sheet(title=sheet_title[:31])
            _write_header(ws)
            
            thin_border = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )
            center_align = Alignment(horizontal="center", vertical="center")
            left_align = Alignment(horizontal="left", vertical="center")

            status_colors = {
                "Present": "E6F4EA",    # Light green
                "Late": "FFF3E0",       # Light orange
                "Early Leave": "FFF3E0",
                "Completed": "E8F0FE",  # Light blue
            }

            for row_idx, record in enumerate(month_records, start=2):
                employee_name = employees.get(record.employee_id, f"ID_{record.employee_id}")
                date_str = record.attendance_date.strftime("%Y-%m-%d")
                check_in_str = record.check_in.strftime("%I:%M %p") if record.check_in else ""
                check_out_str = record.check_out.strftime("%I:%M %p") if record.check_out else ""
                status_str = record.attendance_status.value if record.attendance_status else ""

                row_data = [
                    employee_name,
                    date_str,
                    check_in_str,
                    check_out_str,
                    record.late_minutes or 0,
                    record.missing_minutes or 0,
                    record.overtime_minutes or 0,
                    status_str,
                ]

                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = thin_border
                    cell.alignment = left_align if col_idx == 1 else center_align
                    row_fill = PatternFill("solid", fgColor=status_colors.get(status_str, "FFFFFF"))
                    cell.fill = row_fill

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream


def _write_header(ws) -> None:
    """Write the styled header row to a new worksheet."""
    try:
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        return

    headers = [
        ("Employee", 26), ("Date", 14), ("Check In", 14), ("Check Out", 14),
        ("Late (min)", 14), ("Missing (min)", 14), ("Overtime (min)", 16), ("Status", 18),
    ]
    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    for col_idx, (header, width) in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = alignment
        cell.border = thin_border
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

    ws.row_dimensions[1].height = 24
    ws.auto_filter.ref = f"A1:H1"
