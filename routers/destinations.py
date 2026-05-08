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
from sqlalchemy import func

from database import get_db

from models import (
    User,
    Destination,
    DestinationImage,
    Booking,
    Review
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
# ALLOWED IMAGE TYPES
# =========================================================

ALLOWED_EXTENSIONS = [
    "jpg",
    "jpeg",
    "png",
    "webp"
]


# =========================================================
# SAVE IMAGE HELPER
# =========================================================

def save_image(file: UploadFile):

    extension = file.filename.split(".")[-1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return None

    filename = f"{uuid.uuid4()}.{extension}"

    path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    with open(path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    return filename


# =========================================================
# HOME PAGE
# =========================================================

@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db)
):

    search = request.query_params.get("search")
    category = request.query_params.get("category")
    difficulty = request.query_params.get("difficulty")
    location = request.query_params.get("location")

    query = db.query(Destination)

    if search:
        query = query.filter(
            Destination.name.ilike(f"%{search}%")
        )

    if category:
        query = query.filter(
            Destination.category == category
        )

    if difficulty:
        query = query.filter(
            Destination.difficulty == difficulty
        )

    if location:
        query = query.filter(
            Destination.location.ilike(f"%{location}%")
        )

    destinations = query.order_by(
        Destination.id.desc()
    ).all()

    user = None

    user_id = request.cookies.get("user")

    if user_id:
        try:
            user = db.query(User).filter(
                User.id == int(user_id)
            ).first()
        except:
            user = None

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
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

    if user.role not in ["host", "admin"]:
        return RedirectResponse(
            "/",
            status_code=302
        )

    return templates.TemplateResponse(
        request=request,
        name="create_destination.html",
        context={
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

    gallery_images: list[UploadFile] = File([]),

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

    if user.role not in ["host", "admin"]:
        return RedirectResponse(
            "/",
            status_code=302
        )

    # =====================================================
    # CREATE SLUG
    # =====================================================

    base_slug = re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        name.lower()
    ).strip('-')

    slug = base_slug

    counter = 1

    while db.query(Destination).filter(
        Destination.slug == slug
    ).first():

        slug = f"{base_slug}-{counter}"

        counter += 1

    # =====================================================
    # SAVE HERO IMAGE
    # =====================================================

    hero_image = save_image(image)

    if not hero_image:

        return templates.TemplateResponse(
            request=request,
            name="create_destination.html",
            context={
                "user": user,
                "error": "Invalid hero image format"
            }
        )

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
        image=hero_image,
        host_id=user.id
    )

    db.add(new_destination)

    db.commit()

    db.refresh(new_destination)

    # =====================================================
    # SAVE GALLERY IMAGES
    # =====================================================

    for gallery_image in gallery_images:

        if not gallery_image.filename:
            continue

        saved_filename = save_image(gallery_image)

        if not saved_filename:
            continue

        new_gallery_image = DestinationImage(
            destination_id=new_destination.id,
            image=saved_filename
        )

        db.add(new_gallery_image)

    db.commit()

    return RedirectResponse(
        "/",
        status_code=303
    )

# =========================================================
# EDIT DESTINATION PAGE
# =========================================================

@router.get(
    "/edit-destination/{destination_id}",
    response_class=HTMLResponse
)
def edit_destination_page(
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

    # Only owner/admin
    if (
        destination.host_id != int(user_id)
    ):
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="edit_destination.html",
        context={
            "user": user,
            "destination": destination,
            "error": None
        }
    )

# =========================================================
# UPDATE DESTINATION
# =========================================================

@router.post("/edit-destination/{destination_id}")
def update_destination(
    destination_id: int,
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

    image: UploadFile = File(None),

    gallery_images: list[UploadFile] = File([]),

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

    # Only owner/admin
    if destination.host_id != int(user_id):
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # =====================================================
    # UPDATE BASIC FIELDS
    # =====================================================

    destination.name = name
    destination.location = location
    destination.category = category
    destination.description = description

    destination.price = price

    destination.duration = duration
    destination.difficulty = difficulty

    destination.max_group_size = max_group_size

    destination.included_items = included_items
    destination.itinerary = itinerary

    # =====================================================
    # UPDATE HERO IMAGE
    # =====================================================

    if image and image.filename:

        new_image = save_image(image)

        if new_image:

            old_image_path = os.path.join(
                UPLOAD_DIR,
                destination.image
            )

            if os.path.exists(old_image_path):
                os.remove(old_image_path)

            destination.image = new_image

    # =====================================================
    # ADD NEW GALLERY IMAGES
    # =====================================================

    for gallery_image in gallery_images:

        if not gallery_image.filename:
            continue

        saved_filename = save_image(
            gallery_image
        )

        if not saved_filename:
            continue

        new_gallery_image = DestinationImage(
            destination_id=destination.id,
            image=saved_filename
        )

        db.add(new_gallery_image)

    db.commit()

    return RedirectResponse(
        f"/destination/{destination.slug}",
        status_code=303
    )


# =========================================================
# DESTINATION DETAILS
# =========================================================

@router.get(
    "/destination/{slug}",
    response_class=HTMLResponse
)
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
        try:
            user = db.query(User).filter(
                User.id == int(user_id)
            ).first()
        except:
            user = None

    reviews = db.query(Review).filter(
        Review.destination_id == destination.id
    ).order_by(
        Review.id.desc()
    ).all()

    total_reviews = len(reviews)

    average_rating = db.query(
        func.avg(Review.rating)
    ).filter(
        Review.destination_id == destination.id
    ).scalar()

    if average_rating:
        average_rating = round(float(average_rating), 1)
    else:
        average_rating = 0

    can_review = False

    if user:

        completed_booking = db.query(Booking).filter(
            Booking.traveler_id == user.id,
            Booking.destination_id == destination.id,
            Booking.status == "completed"
        ).first()

        existing_review = db.query(Review).filter(
            Review.user_id == user.id,
            Review.destination_id == destination.id
        ).first()

        if completed_booking and not existing_review:
            can_review = True

    return templates.TemplateResponse(
        request=request,
        name="destination_detail.html",
        context={
            "destination": destination,
            "user": user,
            "reviews": reviews,
            "average_rating": average_rating,
            "total_reviews": total_reviews,
            "can_review": can_review
        }
    )


# =========================================================
# ADD REVIEW
# =========================================================

@router.post("/add-review/{destination_id}")
def add_review(
    destination_id: int,
    request: Request,

    rating: int = Form(...),
    comment: str = Form(...),

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

    destination = db.query(Destination).filter(
        Destination.id == destination_id
    ).first()

    if not destination:
        return RedirectResponse(
            "/",
            status_code=302
        )

    if rating < 1 or rating > 5:
        return RedirectResponse(
            f"/destination/{destination.slug}",
            status_code=302
        )

    completed_booking = db.query(Booking).filter(
        Booking.traveler_id == user.id,
        Booking.destination_id == destination.id,
        Booking.status == "completed"
    ).first()

    if not completed_booking:
        return RedirectResponse(
            f"/destination/{destination.slug}",
            status_code=302
        )

    existing_review = db.query(Review).filter(
        Review.user_id == user.id,
        Review.destination_id == destination.id
    ).first()

    if existing_review:
        return RedirectResponse(
            f"/destination/{destination.slug}",
            status_code=302
        )

    new_review = Review(
        user_id=user.id,
        destination_id=destination.id,
        rating=rating,
        comment=comment
    )

    db.add(new_review)

    db.commit()

    return RedirectResponse(
        f"/destination/{destination.slug}",
        status_code=303
    )

# =========================================================
# DELETE GALLERY IMAGE
# =========================================================

@router.post("/delete-gallery-image/{image_id}")
def delete_gallery_image(
    image_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse(
            "/login",
            status_code=302
        )

    gallery_image = db.query(
        DestinationImage
    ).filter(
        DestinationImage.id == image_id
    ).first()

    if not gallery_image:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    destination = db.query(
        Destination
    ).filter(
        Destination.id == gallery_image.destination_id
    ).first()

    if not destination:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # =====================================================
    # OWNER CHECK
    # =====================================================

    if destination.host_id != int(user_id):

        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # =====================================================
    # DELETE IMAGE FILE
    # =====================================================

    image_path = os.path.join(
        UPLOAD_DIR,
        gallery_image.image
    )

    if os.path.exists(image_path):
        os.remove(image_path)

    # =====================================================
    # DELETE DATABASE RECORD
    # =====================================================

    db.delete(gallery_image)

    db.commit()

    return RedirectResponse(
        f"/edit-destination/{destination.id}",
        status_code=303
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

    if destination.host_id != int(user_id):

        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # =====================================================
    # DELETE HERO IMAGE
    # =====================================================

    hero_image_path = os.path.join(
        UPLOAD_DIR,
        destination.image
    )

    if os.path.exists(hero_image_path):
        os.remove(hero_image_path)

    # =====================================================
    # DELETE GALLERY IMAGES
    # =====================================================

    for gallery_image in destination.gallery_images:

        gallery_path = os.path.join(
            UPLOAD_DIR,
            gallery_image.image
        )

        if os.path.exists(gallery_path):
            os.remove(gallery_path)

    # =====================================================
    # DELETE DESTINATION
    # =====================================================

    db.delete(destination)

    db.commit()

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )