"""
routes.py — All FastAPI route definitions.

Pages are served directly from the backend so a single uvicorn process
handles both the API and the static HTML files.
"""

from pathlib import Path
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Attendance
from backend.schemas import AttendanceCreate, AttendanceOut, AttendanceResponse, EmployeeOut, LoginRequest
from backend import services
from backend.services import is_day_closed, egypt_today
from backend.gps import validate_location
from backend.config import settings

router = APIRouter()

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ---------------------------------------------------------------------------
# Page routes — backend serves the HTML so QR codes and direct links work
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse, tags=["Pages"])
def home_page():
    """Serve the home / landing page."""
    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/check-in", response_class=HTMLResponse, tags=["Pages"])
def attendance_page():
    """Serve the attendance registration page (QR code target)."""
    return FileResponse(FRONTEND_DIR / "attendance.html")


@router.get("/admin", response_class=HTMLResponse, tags=["Pages"])
def admin_page():
    """Serve the admin dashboard."""
    return FileResponse(FRONTEND_DIR / "admin.html")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

def verify_token(token: Optional[str] = None):
    if not token or token != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")
    return token


@router.post("/admin/login", tags=["Admin"])
def admin_login(payload: LoginRequest):
    """Authenticate admin and return a token."""
    if payload.username == settings.ADMIN_USERNAME and payload.password == settings.ADMIN_PASSWORD:
        return JSONResponse(content={"success": True, "token": settings.ADMIN_PASSWORD})
    return JSONResponse(status_code=401, content={"success": False, "message": "Invalid username or password"})


@router.get("/export/excel", tags=["Export"])
def export_excel(token: Optional[str] = Depends(verify_token), db: Session = Depends(get_db)):
    """Download the dynamically generated Attendance.xlsx file."""
    try:
        stream = services.generate_excel_report(db)
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Attendance.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Excel: {str(e)}")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@router.get("/employees", response_model=list[EmployeeOut], tags=["Employees"])
def list_employees(db: Session = Depends(get_db)):
    """Return all active employees for the dropdown."""
    return services.get_active_employees(db)


@router.post("/attendance", response_model=AttendanceResponse, tags=["Attendance"])
def register_attendance(payload: AttendanceCreate, db: Session = Depends(get_db)):
    """
    Register check-in or check-out for an employee.

    The service layer decides which action to apply based on today's records.
    """
    is_valid, distance, msg = validate_location(payload.latitude, payload.longitude)
    if not is_valid:
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "message": msg,
                "distance": distance,
                "allowed_radius": settings.ALLOWED_RADIUS_METERS
            }
        )

    result = services.register_attendance(payload.employee_id, db)
    return AttendanceResponse(
        success=result["success"],
        action=result["action"],
        message=result["message"],
        data=AttendanceOut.model_validate(result["record"]) if result["record"] else None,
        distance=distance
    )


@router.get("/attendance/today", response_model=list[AttendanceOut], tags=["Attendance"])
def today_attendance(db: Session = Depends(get_db)):
    """
    Return all attendance records for today (Egypt time).
    After 8 PM Egypt time the day is considered closed and an empty list
    is returned so the home-page stats reset to 0.
    """
    if is_day_closed():
        return []  # Day is over — stats reset to 0 until next morning

    records = (
        db.query(Attendance)
        .filter(Attendance.attendance_date == egypt_today())
        .all()
    )
    return records


@router.delete("/attendance/reset", tags=["Admin"])
def reset_all_attendance(token: Optional[str] = Depends(verify_token), db: Session = Depends(get_db)):
    """Wipe all attendance records. Only for admin use."""
    try:
        services.reset_attendance_data(db)
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "All attendance records have been permanently deleted."}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset data: {str(e)}")
