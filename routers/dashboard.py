from fastapi import (
    APIRouter,
    Request,
    Depends
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse
)

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

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
# DASHBOARD
# =========================================================

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    # =====================================================
    # NOT LOGGED IN
    # =====================================================

    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # =====================================================
    # GET USER
    # =====================================================

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # =====================================================
    # HOST / ADMIN DASHBOARD
    # =====================================================

    if user.role in ["host", "admin"]:

        # Get destinations
        destinations = db.query(Destination).filter(
            Destination.host_id == user.id
        ).all()

        # Get bookings
        bookings = db.query(Booking).join(
            Destination,
            Booking.destination_id == Destination.id
        ).filter(
            Destination.host_id == user.id
        ).order_by(
            Booking.id.desc()
        ).all()

        # Stats
        total_destinations = len(destinations)

        total_bookings = len(bookings)

        total_revenue = sum(
            booking.total_price
            for booking in bookings
            if booking.status in ["confirmed", "completed"]
        )

        pending_bookings = len([
            booking for booking in bookings
            if booking.status == "pending"
        ])

        completed_bookings = len([
            booking for booking in bookings
            if booking.status == "completed"
        ])

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,

                "destinations": destinations,
                "bookings": bookings,

                "total_destinations": total_destinations,
                "total_bookings": total_bookings,
                "total_revenue": total_revenue,

                "pending_bookings": pending_bookings,
                "completed_bookings": completed_bookings,

                "dashboard_type": "host"
            }
        )

    # =====================================================
    # TRAVELER DASHBOARD
    # =====================================================

    traveler_bookings = db.query(Booking).filter(
        Booking.traveler_id == user.id
    ).order_by(
        Booking.id.desc()
    ).all()

    total_trips = len(traveler_bookings)

    completed_trips = len([
        booking for booking in traveler_bookings
        if booking.status == "completed"
    ])

    upcoming_trips = len([
        booking for booking in traveler_bookings
        if booking.status in ["pending", "confirmed"]
    ])

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,

            "bookings": traveler_bookings,

            "total_trips": total_trips,
            "completed_trips": completed_trips,
            "upcoming_trips": upcoming_trips,

            "dashboard_type": "traveler"
        }
    )


# =========================================================
# CONFIRM BOOKING
# =========================================================

@router.post("/confirm-booking/{booking_id}")
def confirm_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    # Not logged in
    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # Get booking
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Get destination
    destination = db.query(Destination).filter(
        Destination.id == booking.destination_id
    ).first()

    if not destination:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Only host/admin can confirm
    if destination.host_id != int(user_id):
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Update status
    booking.status = "confirmed"

    db.commit()

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )


# =========================================================
# COMPLETE BOOKING
# =========================================================

@router.post("/complete-booking/{booking_id}")
def complete_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    # Not logged in
    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # Get booking
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Get destination
    destination = db.query(Destination).filter(
        Destination.id == booking.destination_id
    ).first()

    if not destination:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Only host/admin can complete
    if destination.host_id != int(user_id):
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Only confirmed bookings can complete
    if booking.status != "confirmed":
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Update status
    booking.status = "completed"

    db.commit()

    return RedirectResponse(
        "/dashboard",
        status_code=303
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

    # Not logged in
    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # Get booking
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Get destination
    destination = db.query(Destination).filter(
        Destination.id == booking.destination_id
    ).first()

    if not destination:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Only host/admin can cancel
    if destination.host_id != int(user_id):
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Update status
    booking.status = "cancelled"

    db.commit()

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )