from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Text,
    DateTime,
    UniqueConstraint
)

from sqlalchemy.orm import relationship

from database import Base

from datetime import datetime


# =========================================================
# USER MODEL
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    password = Column(
        String(255),
        nullable=False
    )

    # admin | host | traveler
    role = Column(
        String(20),
        default="traveler"
    )

    profile_image = Column(
        String(255),
        nullable=True
    )

    bio = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    destinations = relationship(
        "Destination",
        back_populates="host",
        cascade="all, delete"
    )

    bookings = relationship(
        "Booking",
        back_populates="traveler",
        cascade="all, delete"
    )

    reviews = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete"
    )

    wishlist_items = relationship(
        "Wishlist",
        back_populates="user",
        cascade="all, delete"
    )


# =========================================================
# DESTINATION MODEL
# =========================================================

class Destination(Base):
    __tablename__ = "destinations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # =====================================================
    # BASIC INFO
    # =====================================================

    name = Column(
        String(255),
        nullable=False
    )

    slug = Column(
        String(255),
        unique=True,
        nullable=False
    )

    location = Column(
        String(255),
        nullable=False
    )

    category = Column(
        String(100),
        nullable=False
    )

    description = Column(
        Text,
        nullable=False
    )

    # =====================================================
    # PRICING
    # =====================================================

    price = Column(
        Float,
        nullable=False
    )

    # =====================================================
    # TRIP DETAILS
    # =====================================================

    duration = Column(
        String(100)
    )

    difficulty = Column(
        String(50)
    )

    max_group_size = Column(
        Integer,
        default=1
    )

    included_items = Column(
        Text
    )

    itinerary = Column(
        Text
    )

    # =====================================================
    # MAIN COVER IMAGE
    # =====================================================

    image = Column(
        String(255)
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # =====================================================
    # FOREIGN KEY
    # =====================================================

    host_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    host = relationship(
        "User",
        back_populates="destinations"
    )

    bookings = relationship(
        "Booking",
        back_populates="destination",
        cascade="all, delete"
    )

    reviews = relationship(
        "Review",
        back_populates="destination",
        cascade="all, delete"
    )

    wishlist_items = relationship(
        "Wishlist",
        back_populates="destination",
        cascade="all, delete"
    )

    # =====================================================
    # GALLERY IMAGES
    # =====================================================

    gallery_images = relationship(
        "DestinationImage",
        back_populates="destination",
        cascade="all, delete"
    )


# =========================================================
# DESTINATION IMAGE MODEL
# =========================================================

class DestinationImage(Base):
    __tablename__ = "destination_images"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    image = Column(
        String(255),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    destination_id = Column(
        Integer,
        ForeignKey("destinations.id"),
        nullable=False
    )

    # =====================================================
    # RELATIONSHIP
    # =====================================================

    destination = relationship(
        "Destination",
        back_populates="gallery_images"
    )


# =========================================================
# BOOKING MODEL
# =========================================================

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    traveler_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    destination_id = Column(
        Integer,
        ForeignKey("destinations.id"),
        nullable=False
    )

    booking_date = Column(
        DateTime,
        default=datetime.utcnow
    )

    travel_date = Column(
        DateTime,
        nullable=True
    )

    guests = Column(
        Integer,
        default=1
    )

    total_price = Column(
        Float,
        nullable=False
    )

    # pending | confirmed | cancelled | completed
    status = Column(
        String(50),
        default="pending"
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    traveler = relationship(
        "User",
        back_populates="bookings"
    )

    destination = relationship(
        "Destination",
        back_populates="bookings"
    )


# =========================================================
# REVIEW MODEL
# =========================================================

class Review(Base):
    __tablename__ = "reviews"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    destination_id = Column(
        Integer,
        ForeignKey("destinations.id"),
        nullable=False
    )

    rating = Column(
        Integer,
        nullable=False
    )

    comment = Column(
        Text
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    user = relationship(
        "User",
        back_populates="reviews"
    )

    destination = relationship(
        "Destination",
        back_populates="reviews"
    )


# =========================================================
# WISHLIST MODEL
# =========================================================

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    destination_id = Column(
        Integer,
        ForeignKey("destinations.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    user = relationship(
        "User",
        back_populates="wishlist_items"
    )

    destination = relationship(
        "Destination",
        back_populates="wishlist_items"
    )

    # =====================================================
    # PREVENT DUPLICATES
    # =====================================================

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "destination_id",
            name="unique_wishlist"
        ),
    )