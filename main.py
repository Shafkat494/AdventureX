from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os

# Database
from database import engine
from models import Base

# Routers
from routers import auth
from routers import destinations
from routers import bookings
from routers import dashboard


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Adventure Booking Platform",
    description="Production-ready Trekking, Skiing and Climbing Booking Platform",
    version="1.0.0"
)


# =========================================================
# TEMPLATES
# =========================================================

templates = Jinja2Templates(directory="templates")


# =========================================================
# STATIC FILES
# =========================================================

# Create upload directory automatically
UPLOAD_DIR = "static/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static folder
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# =========================================================
# INCLUDE ROUTERS
# =========================================================

app.include_router(auth.router)

app.include_router(destinations.router)

app.include_router(bookings.router)

app.include_router(dashboard.router)


# =========================================================
# ROOT HEALTH CHECK
# =========================================================

@app.get("/health")
def health_check():
    return {
        "status": "running",
        "project": "Adventure Booking Platform"
    }