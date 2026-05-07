from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

import os


# =========================================================
# DATABASE CONFIG
# =========================================================

# Database folder
os.makedirs("data", exist_ok=True)

# SQLite Database
DATABASE_URL = "sqlite:///./data/adventure_booking.db"


# =========================================================
# ENGINE
# =========================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # Set True for SQL debugging
)


# =========================================================
# SESSION
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =========================================================
# BASE MODEL
# =========================================================

Base = declarative_base()


# =========================================================
# DATABASE DEPENDENCY
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()