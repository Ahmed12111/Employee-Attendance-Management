"""
config.py — Application configuration using Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import time


class Settings(BaseSettings):
    # App config
    APP_NAME: str = "Employee Attendance Management System"
    DEBUG: bool = False
    SECRET_KEY: str = "supersecretkey"  # Change this in production
    
    # Database
    DATABASE_URL: str = "sqlite:///./attendance.db"

    # Geofencing
    COMPANY_LATITUDE: float
    COMPANY_LONGITUDE: float
    ALLOWED_RADIUS_METERS: int

    # Business Rules
    WORK_START: time = time(8, 0)
    WORK_END: time = time(16, 0)
    ATTENDANCE_OPEN: time = time(8, 0)
    ATTENDANCE_CLOSE: time = time(18, 0)
    RESET_HOUR: int = 20

    # CORS
    CORS_ORIGINS: str = "http://localhost,http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
