# Employee Attendance Management System

A QR-based, no-login attendance tracking system built for simplicity and efficiency. Employees scan a QR code to access the check-in page and register their attendance. Administrators can view statistics and export monthly attendance reports in Excel format.

## Features

- **Quick Check-In/Out:** Employees select their name from a dropdown to register their attendance.
- **Automated Time Tracking:** Calculates late minutes, missing minutes, overtime, and working hours automatically based on configurable business hours.
- **Dynamic Excel Export:** Generates clean, formatted Excel reports directly from the SQLite database on demand.
- **Responsive UI:** Clean, modern interface that works seamlessly on desktop and mobile devices.

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Database:** SQLite
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Excel Generation:** openpyxl

## Folder Structure

```
├── backend/            # FastAPI application
│   ├── config.py       # Configuration and env vars
│   ├── database.py     # SQLAlchemy setup
│   ├── main.py         # Entry point and routing
│   ├── models.py       # ORM Models
│   ├── routes.py       # API endpoints
│   ├── schemas.py      # Pydantic schemas
│   └── services.py     # Business logic
├── frontend/           # Static assets
│   ├── admin.html      # Admin dashboard
│   ├── attendance.html # Check-in page
│   ├── index.html      # Landing page
│   ├── script.js       # Check-in logic
│   └── style.css       # Styles
├── .env.example        # Environment variable template
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Running Locally

1. **Clone the repository.**
2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables:**
   - Copy `.env.example` to `.env` and adjust the variables if needed.
4. **Run the application:**
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. **Access the application:**
   - Open `http://127.0.0.1:8000` in your browser.

## Render Deployment Guide

This project is configured to run effortlessly on the Render Free Plan.

1. **Create a Web Service** in Render and connect your GitHub repository.
2. **Configure Settings:**
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. **Set Environment Variables:**
   Add all necessary environment variables (e.g., `APP_NAME`, `CORS_ORIGINS`, etc.) in the Render dashboard.
4. **Deploy.**
   Render will automatically build and start the server. SQLite will run within Render's ephemeral filesystem (which is fine for an MVP, but attaching a persistent disk is recommended for production data retention).

## API Endpoints

- `GET /` - Home page
- `GET /check-in` - Attendance page
- `GET /admin` - Admin dashboard
- `GET /employees` - List active employees
- `POST /attendance` - Register check-in or check-out
- `GET /attendance/today` - Today's attendance records
- `GET /export/excel` - Download generated monthly Excel report
