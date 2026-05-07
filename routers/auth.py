from fastapi import (
    APIRouter,
    Request,
    Form,
    Depends
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse
)

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database import get_db

from models import User

from utils.security import (
    hash_password,
    verify_password
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# =========================================================
# SIGNUP PAGE
# =========================================================

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):

    return templates.TemplateResponse(
        "signup.html",
        {
            "request": request,
            "user": None,
            "error": None
        }
    )


# =========================================================
# SIGNUP
# =========================================================

@router.post("/signup")
def signup(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):

    # Password match check
    if password != confirm_password:

        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "user": None,
                "error": "Passwords do not match"
            }
        )

    # Username exists
    existing_user = db.query(User).filter(
        User.username == username
    ).first()

    if existing_user:

        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "user": None,
                "error": "Username already exists"
            }
        )

    # Email exists
    existing_email = db.query(User).filter(
        User.email == email
    ).first()

    if existing_email:

        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "user": None,
                "error": "Email already exists"
            }
        )

    # Create new user
    new_user = User(
        username=username,
        email=email,
        password=hash_password(password),
        role=role
    )

    db.add(new_user)

    db.commit()

    return RedirectResponse(
        "/login",
        status_code=303
    )


# =========================================================
# LOGIN PAGE
# =========================================================

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "user": None,
            "error": None
        }
    )


# =========================================================
# LOGIN
# =========================================================

@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.username == username
    ).first()

    # Invalid credentials
    if not user or not verify_password(
        password,
        user.password
    ):

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "user": None,
                "error": "Invalid username or password"
            }
        )

    response = RedirectResponse(
        "/",
        status_code=303
    )

    response.set_cookie(
        key="user",
        value=str(user.id),
        httponly=True,
        max_age=60 * 60 * 24,
        samesite="lax",

        # IMPORTANT FOR RENDER HTTPS
        secure=True
    )

    return response


# =========================================================
# LOGOUT
# =========================================================

@router.get("/logout")
def logout():

    response = RedirectResponse(
        "/",
        status_code=302
    )

    response.delete_cookie("user")

    return response