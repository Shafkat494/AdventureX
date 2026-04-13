from fastapi import FastAPI, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import shutil
import os
import time
import re
import traceback

from database import SessionLocal, engine
import models
from utils.security import hash_password, verify_password
from fastapi.templating import Jinja2Templates

# 1. Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. Define Templates BEFORE the routes use them (Crucial Fix)
templates = Jinja2Templates(directory="templates")

# 3. Static files & Directory setup
upload_path = os.path.join("static", "uploads")
try:
    if os.path.exists(upload_path) and os.path.isfile(upload_path):
        os.remove(upload_path) 
    os.makedirs(upload_path, exist_ok=True)
except Exception as e:
    print(f"Note: Could not create directory automatically: {e}")

app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------- DATABASE DEPENDENCY ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- HOME ----------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    products = db.query(models.Product).all()

    user_id = request.cookies.get("user")
    user = None

    if user_id:
        user = db.query(models.User).filter(models.User.id == int(user_id)).first()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products,
        "user": user,
        "current_path": request.url.path
    })

# ---------------- SIGNUP ----------------
@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})

@app.post("/signup")
def signup(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form(...),   # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match"
        })

    if db.query(models.User).filter(models.User.username == username).first():
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Username already exists"
        })

    # 🔥 ADD THIS (email check)
    if db.query(models.User).filter(models.User.email == email).first():
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Email already exists"
    })

    try:
        new_user = models.User(
            username=username,
            email=email,
            password=hash_password(password),
            role=role   # ✅ SAVE ROLE
        )

        db.add(new_user)
        db.commit()

    except Exception as e:
        db.rollback()
        print("SIGNUP ERROR:", e)  # 👈 helps debugging
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Database error during signup"
        })

    return RedirectResponse("/login", status_code=303)
# ---------------- LOGIN ----------------
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.username == username
    ).first()

    # ❌ Invalid credentials
    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password"
        })

    redirect_url = "/"
    response = RedirectResponse(url=redirect_url, status_code=303)

    # ✅ Secure cookie
    response.set_cookie(
        key="user",
        value=str(user.id),
        httponly=True,
        max_age=60 * 60 * 24,   # 1 day
        samesite="lax",
        secure=False  # ⚠️ change to True when using HTTPS
    )

    return response

@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("user")
    return response

# ---------------- DASHBOARD ----------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()

    # ✅ ADD THIS
    if user.role != "owner":
        return RedirectResponse("/", status_code=303)

    products = db.query(models.Product).filter(
        models.Product.owner_id == user.id
    ).all()

    orders = db.query(models.Order).join(models.Product).filter(
        models.Product.owner_id == user.id
    ).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "products": products,
        "orders": orders,
        "current_path": request.url.path
    })

# ---------------- UPLOAD ----------------
@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user")

    # Not logged in
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    # ✅ GET USER (THIS FIXES NAVBAR)
    user = db.query(models.User).filter(
        models.User.id == int(user_id)
    ).first()

    # Only owners allowed
    if user.role != "owner":
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse("upload.html", {
        "request": request,
        "user": user,
        "error": None
    })

@app.post("/upload")
def upload(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user")
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    # ✅ GET USER (for error rendering)
    user = db.query(models.User).filter(
        models.User.id == int(user_id)
    ).first()

    try:
        price_val = float(price)
    except ValueError:
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "user": user, 
            "error": "Invalid price format"
        })

    # Save logic
    timestamp = int(time.time())
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename)
    unique_name = f"{timestamp}_{clean_name}"
    file_path = os.path.join(upload_path, unique_name)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        new_prod = models.Product(
            title=title,
            description=description,
            price=price_val,
            image=unique_name,
            owner_id=int(user_id)
        )
        db.add(new_prod)
        db.commit()
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        return templates.TemplateResponse("upload.html", {
            "request": request, 
            "user": user,
            "error": "Database error."
        })
    finally:
        file.file.close()

    return RedirectResponse("/dashboard", status_code=303)

# ---------------- PRODUCT DETAIL ----------------
@app.get("/product/{product_id}", response_class=HTMLResponse)
def product_page(product_id: int, request: Request, db: Session = Depends(get_db)):

    user_id = request.cookies.get("user")
    user = None

    if user_id:
        user = db.query(models.User).filter(models.User.id == int(user_id)).first()

    # GET PRODUCT
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    if not product:
        return HTMLResponse("Product not found", status_code=404)

    # ✅ LIKE STATUS
    liked = None
    if user_id:
        liked = db.query(models.Like).filter_by(
            user_id=int(user_id),
            product_id=product.id
        ).first()

    # ✅ CART STATUS
    in_cart = None
    if user_id:
        in_cart = db.query(models.Cart).filter_by(
            user_id=int(user_id),
            product_id=product.id
        ).first()

    # ✅ WISHLIST STATUS
    wish = request.query_params.get("wish") == "1"
    in_wishlist = False

    if user_id:
        in_wishlist = db.query(models.Wishlist).filter_by(
            user_id=int(user_id),
            product_id=product.id
        ).first() is not None

    return templates.TemplateResponse("product.html", {
        "request": request,
        "product": product,
        "user": user,
        "liked": liked,
        "in_cart": in_cart,
        "in_wishlist": in_wishlist,
        "wish": wish,
        "current_path": request.url.path
    })

# ---------------- DELETE PRODUCT ----------------
@app.post("/delete/{product_id}")
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.owner_id == int(user_id)
    ).first()

    if not product:
        return RedirectResponse("/dashboard", status_code=302)

    # Delete image file
    file_path = f"static/uploads/{product.image}"
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from DB
    db.delete(product)
    db.commit()

    return RedirectResponse("/dashboard", status_code=303)

@app.get("/edit/{product_id}", response_class=HTMLResponse)
def edit_page(product_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.owner_id == int(user_id)
    ).first()

    if not product:
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "product": product
    })

@app.post("/edit/{product_id}")
def edit_product(
    product_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.owner_id == int(user_id)
    ).first()

    if not product:
        return RedirectResponse("/dashboard", status_code=302)

    try:
        product.title = title
        product.description = description
        product.price = float(price)

        db.commit()
    except:
        db.rollback()
        return RedirectResponse(f"/edit/{product_id}", status_code=302)

    return RedirectResponse("/dashboard", status_code=303)

@app.get("/manage/{product_id}", response_class=HTMLResponse)
def manage_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    
    user_id = request.cookies.get("user")
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.owner_id == int(user_id)
    ).first()

    if not product:
        return RedirectResponse("/dashboard", status_code=302)

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()

    return templates.TemplateResponse("manage.html", {
        "request": request,
        "product": product,
        "user": user
    })

@app.post("/like/{product_id}")
def like_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    existing = db.query(models.Like).filter_by(
        user_id=int(user_id),
        product_id=product_id
    ).first()

    if existing:
        db.delete(existing)  # Unlike
    else:
        db.add(models.Like(user_id=int(user_id), product_id=product_id))

    db.commit()

    return RedirectResponse(f"/product/{product_id}", status_code=303)

@app.get("/wishlist", response_class=HTMLResponse)
def view_wishlist(request: Request, db: Session = Depends(get_db)):

    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    user = db.query(models.User).filter(
        models.User.id == int(user_id)
    ).first()

    wishlist_items = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == int(user_id)
    ).all()

    return templates.TemplateResponse("wishlist.html", {
        "request": request,
        "user": user,
        "wishlist_items": wishlist_items
    })

@app.post("/wishlist/{product_id}")
def add_to_wishlist(product_id: int, request: Request, db: Session = Depends(get_db)):

    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    # check if already exists
    exists = db.query(models.Wishlist).filter_by(
        user_id=int(user_id),
        product_id=product_id
    ).first()

    if not exists:
        db.add(models.Wishlist(
            user_id=int(user_id),
            product_id=product_id
        ))
        db.commit()

    # redirect back to product page
    return RedirectResponse(f"/product/{product_id}?wish=1", status_code=303)

@app.post("/remove-wishlist/{wishlist_id}")
def remove_wishlist(wishlist_id: int, request: Request, db: Session = Depends(get_db)):

    item = db.query(models.Wishlist).filter(
        models.Wishlist.id == wishlist_id
    ).first()

    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse("/wishlist", status_code=303)

@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()

    cart_items = db.query(models.Cart).filter(
        models.Cart.user_id == int(user_id)
    ).all()

    return templates.TemplateResponse("cart.html", {
        "request": request,
        "user": user,
        "cart_items": cart_items
    })

@app.post("/cart/{product_id}")
def add_to_cart(product_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user")

    if not user_id:
        return RedirectResponse("/login", status_code=302)

    exists = db.query(models.Cart).filter_by(
        user_id=int(user_id),
        product_id=product_id
    ).first()

    if not exists:
        db.add(models.Cart(user_id=int(user_id), product_id=product_id))
        db.commit()

    return RedirectResponse(f"/product/{product_id}", status_code=303)

@app.post("/remove-cart/{cart_id}")
def remove_cart(cart_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(models.Cart).filter(models.Cart.id == cart_id).first()

    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse("/cart", status_code=303)