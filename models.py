from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="customer")

    products = relationship("Product", back_populates="owner")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000))
    price = Column(Float, nullable=False)
    image = Column(String(255))
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="products")
    cart_items = relationship("Cart", back_populates="product")
    wishlist_items = relationship("Wishlist", back_populates="product")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))

    status = Column(String, default="pending")

    # Relationships
    user = relationship("User")
    product = relationship("Product")

class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))

    # ✅ ADD THESE
    product = relationship("Product")
    user = relationship("User")

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="wishlist_items")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='unique_wishlist'),
    )

class Cart(Base):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Product", back_populates="cart_items")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='unique_cart'),
    )