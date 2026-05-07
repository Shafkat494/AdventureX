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

    # User not logged in
    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # Get current user
    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    # =====================================================
    # HOST DASHBOARD
    # =====================================================

    if user.role in ["host", "admin"]:

        destinations = db.query(Destination).filter(
            Destination.host_id == user.id
        ).all()

        bookings = db.query(Booking).join(
            Destination,
            Booking.destination_id == Destination.id
        ).filter(
            Destination.host_id == user.id
        ).all()

        total_destinations = len(destinations)

        total_bookings = len(bookings)

        total_revenue = sum(
            booking.total_price for booking in bookings
        )

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

                "dashboard_type": "host"
            }
        )

    # =====================================================
    # TRAVELER DASHBOARD
    # =====================================================

    traveler_bookings = db.query(Booking).filter(
        Booking.traveler_id == user.id
    ).all()

    total_trips = len(traveler_bookings)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,

            "bookings": traveler_bookings,

            "total_trips": total_trips,

            "dashboard_type": "traveler"
        }
    )