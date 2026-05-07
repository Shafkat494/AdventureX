from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    UploadFile,
    File
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
    Destination
)

import shutil
import os
import uuid
import re


# =========================================================
# ROUTER
# =========================================================

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# =========================================================
# UPLOAD DIRECTORY
# =========================================================

UPLOAD_DIR = "static/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================================================
# HOME PAGE
# =========================================================

@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db)
):

    destinations = db.query(Destination).all()

    user = None

    user_id = request.cookies.get("user")

    if user_id:
        user = db.query(User).filter(
            User.id == int(user_id)
        ).first()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "destinations": destinations,
            "user": user
        }
    )


# =========================================================
# CREATE DESTINATION PAGE
# =========================================================

@router.get("/create-destination", response_class=HTMLResponse)
def create_destination_page(
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

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    # Only hosts/admins allowed
    if user.role not in ["host", "admin"]:
        return RedirectResponse(
            "/",
            status_code=302
        )

    return templates.TemplateResponse(
        "create_destination.html",
        {
            "request": request,
            "user": user,
            "error": None
        }
    )


# =========================================================
# CREATE DESTINATION
# =========================================================

@router.post("/create-destination")
def create_destination(
    request: Request,

    name: str = Form(...),
    location: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),

    price: float = Form(...),

    duration: str = Form(...),
    difficulty: str = Form(...),

    max_group_size: int = Form(...),

    included_items: str = Form(...),
    itinerary: str = Form(...),

    image: UploadFile = File(...),

    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    # Not logged in
    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    # Only hosts/admins allowed
    if user.role not in ["host", "admin"]:
        return RedirectResponse(
            "/",
            status_code=302
        )

    # =====================================================
    # CREATE SLUG
    # =====================================================

    slug = re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        name.lower()
    ).strip('-')

    # =====================================================
    # IMAGE SAVE
    # =====================================================

    image_extension = image.filename.split(".")[-1]

    unique_filename = f"{uuid.uuid4()}.{image_extension}"

    image_path = os.path.join(
        UPLOAD_DIR,
        unique_filename
    )

    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # =====================================================
    # CREATE DESTINATION
    # =====================================================

    new_destination = Destination(
        name=name,
        slug=slug,
        location=location,
        category=category,
        description=description,
        price=price,
        duration=duration,
        difficulty=difficulty,
        max_group_size=max_group_size,
        included_items=included_items,
        itinerary=itinerary,
        image=unique_filename,
        host_id=user.id
    )

    db.add(new_destination)
    db.commit()

    return RedirectResponse(
        "/",
        status_code=303
    )


# =========================================================
# DESTINATION DETAILS PAGE
# =========================================================

@router.get("/destination/{slug}", response_class=HTMLResponse)
def destination_detail(
    slug: str,
    request: Request,
    db: Session = Depends(get_db)
):

    destination = db.query(Destination).filter(
        Destination.slug == slug
    ).first()

    if not destination:
        return HTMLResponse(
            "Destination not found",
            status_code=404
        )

    user = None

    user_id = request.cookies.get("user")

    if user_id:
        user = db.query(User).filter(
            User.id == int(user_id)
        ).first()

    return templates.TemplateResponse(
        "destination_detail.html",
        {
            "request": request,
            "destination": destination,
            "user": user
        }
    )


# =========================================================
# DELETE DESTINATION
# =========================================================

@router.post("/delete-destination/{destination_id}")
def delete_destination(
    destination_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    destination = db.query(Destination).filter(
        Destination.id == destination_id
    ).first()

    if not destination:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Only owner/admin can delete
    if (
        destination.host_id != int(user_id)
    ):
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # Delete image
    image_path = os.path.join(
        UPLOAD_DIR,
        destination.image
    )

    if os.path.exists(image_path):
        os.remove(image_path)

    # Delete database record
    db.delete(destination)

    db.commit()

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )