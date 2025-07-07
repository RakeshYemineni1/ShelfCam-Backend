from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database.db import Base
from datetime import datetime
import enum

class ShelfCategoryEnum(enum.Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    GROCERIES = "groceries"
    BOOKS = "books"
    TOYS = "toys"
    SPORTS = "sports"
    HOME_GARDEN = "home_garden"
    BEAUTY = "beauty"
    AUTOMOTIVE = "automotive"
    PHARMACY = "pharmacy"

class Shelf(Base):
    __tablename__ = "shelves"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(200), nullable=False)  # changed from location
    capacity = Column(Integer, nullable=False)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    current_stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to staff assignments
    staff_assignments = relationship("StaffAssignment", back_populates="shelf", cascade="all, delete-orphan")