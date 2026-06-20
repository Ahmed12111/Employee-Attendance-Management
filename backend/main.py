"""
main.py — FastAPI application entry point.

Responsibilities:
  - Create the app instance
  - Mount static assets (CSS, JS)
  - Register routes
  - Initialize the database on startup
  - Seed default employees if the table is empty
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.database import init_db, SessionLocal
from backend.routes import router
from backend.config import settings

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    description="QR-based attendance tracking for small companies.",
    version="1.0.0",
    debug=settings.DEBUG,
)

# CORS
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend assets (CSS, JS, images) at /static
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Register all routes
app.include_router(router)


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail), "errors": None},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Validation Error", "errors": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal Server Error", "errors": str(exc) if settings.DEBUG else None},
    )


# ---------------------------------------------------------------------------
# Startup event
# ---------------------------------------------------------------------------


@app.on_event("startup")
def on_startup():
    """Initialize the database and seed employees on first run."""
    init_db()
    _seed_employees()


def _seed_employees() -> None:
    """Insert 13 default employees if the employees table is empty."""
    from backend.models import Employee

    default_employees = [
        {"full_name": "Ahmed Nour Yehia",          "department": "TA"},
        {"full_name": "Ahmed Mostafa Sayed",       "department": "TA"},
        {"full_name": "Ziad Ahmed",                "department": "TA"},
        {"full_name": "Ahmed Mohamed Makboul",     "department": "TA"},
        {"full_name": "Youssef Abdel Maged",       "department": "TA"},
        {"full_name": "Abdelrahman Hesham",        "department": "TA"},
        {"full_name": "Alaa El Mohamady",          "department": "TA"},
        {"full_name": "Eman Ahmed",                "department": "TA"},
        {"full_name": "Toqa Mohamed",              "department": "TA"},
        {"full_name": "Ruba Hesham",               "department": "TA"},
        {"full_name": "Mahmoud Khaled",            "department": "TA"},
    ]

    db = SessionLocal()
    try:
        count = db.query(Employee).count()
        if count == 0:
            for emp_data in default_employees:
                emp = Employee(
                    full_name=emp_data["full_name"],
                    department=emp_data["department"],
                    is_active=True,
                )
                db.add(emp)
            db.commit()
            logger.info(f"[Seed] {len(default_employees)} employees inserted.")
        else:
            logger.info(f"[Seed] Skipped — {count} employees already exist.")
    finally:
        db.close()
