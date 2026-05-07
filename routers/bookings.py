from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form
)

from fastapi.responses import (
    RedirectResponse,
    HTMLResponse
)

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from datetime import datetime

from database import get_db

from models import (
    User,
    Destination,
    Booking
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# =========================================================
# BOOK DESTINATION
# =========================================================

@router.post("/book/{destination_id}")
def book_destination(
    destination_id: int,
    request: Request,

    guests: int = Form(...),
    travel_date: str = Form(...),

    db: Session = Depends(get_db)
):

    # =====================================================
    # AUTH CHECK
    # =====================================================

    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # =====================================================
    # GET DESTINATION
    # =====================================================

    destination = db.query(Destination).filter(
        Destination.id == destination_id
    ).first()

    if not destination:
        return HTMLResponse(
            "Destination not found",
            status_code=404
        )

    # =====================================================
    # VALIDATION
    # =====================================================

    if guests < 1:
        return HTMLResponse(
            "Guests must be at least 1",
            status_code=400
        )

    if guests > destination.max_group_size:
        return HTMLResponse(
            f"Maximum allowed guests is {destination.max_group_size}",
            status_code=400
        )

    # =====================================================
    # CONVERT DATE
    # =====================================================

    try:
        parsed_travel_date = datetime.strptime(
            travel_date,
            "%Y-%m-%d"
        )

    except ValueError:

        return HTMLResponse(
            "Invalid date format",
            status_code=400
        )

    # =====================================================
    # CALCULATE PRICE
    # =====================================================

    total_price = destination.price * guests

    # =====================================================
    # CREATE BOOKING
    # =====================================================

    new_booking = Booking(
        traveler_id=user.id,
        destination_id=destination.id,

        travel_date=parsed_travel_date,

        guests=guests,

        total_price=total_price,

        status="pending"
    )

    db.add(new_booking)

    db.commit()

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )


# =========================================================
# MY BOOKINGS PAGE
# =========================================================

@router.get("/my-bookings", response_class=HTMLResponse)
def my_bookings(
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    bookings = db.query(Booking).filter(
        Booking.traveler_id == user.id
    ).all()

    return templates.TemplateResponse(
        "my_bookings.html",
        {
            "request": request,
            "user": user,
            "bookings": bookings
        }
    )


# =========================================================
# CANCEL BOOKING
# =========================================================

@router.post("/cancel-booking/{booking_id}")
def cancel_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Only booking owner can cancel
    if booking.traveler_id != int(user_id):
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Update status instead of deleting
    booking.status = "cancelled"

    db.commit()

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )


# =========================================================
# CONFIRM BOOKING (HOST/ADMIN)
# =========================================================

@router.post("/confirm-booking/{booking_id}")
def confirm_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # Only hosts/admins
    if user.role not in ["host", "admin"]:
        return RedirectResponse(
            "/",
            status_code=302
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    booking.status = "confirmed"

    db.commit()

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )