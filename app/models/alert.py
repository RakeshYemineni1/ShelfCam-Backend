from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Enum as SqlEnum,
    ForeignKey,
    DateTime
)
from sqlalchemy.orm import relationship

from pydantic import BaseModel, ConfigDict

from app.database.db import Base


# -------------------- ENUMS --------------------

class AlertType(str, Enum):
    LOW_STOCK = "low_stock"
    MEDIUM_STOCK = "medium_stock"
    HIGH_STOCK = "high_stock"
    CRITICAL_STOCK = "critical_stock"
    OUT_OF_STOCK = "out_of_stock"
    MISPLACED_ITEM = "misplaced_item"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    PENDING = "pending"


class AlertPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# -------------------- ORM MODEL --------------------

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    
    alert_type = Column(SqlEnum(AlertType), nullable=False)
    status = Column(SqlEnum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    priority = Column(SqlEnum(AlertPriority), nullable=False)

    shelf_name = Column(String, nullable=False)
    rack_name = Column(String, nullable=True)  # optional
    product_number = Column(String, nullable=True)
    product_name = Column(String, nullable=True)

    category = Column(String, nullable=True)

    title = Column(String, nullable=False)
    message = Column(String, nullable=False)

    expected_product = Column(String, nullable=True)
    actual_product = Column(String, nullable=True)
    correct_location = Column(String, nullable=True)

    empty_percentage = Column(Float, nullable=True)
    fill_percentage = Column(Float, nullable=True)

    assigned_staff_id = Column(String, ForeignKey("employees.employee_id"), nullable=True)
    created_by = Column(String, nullable=True)

    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_staff = relationship("Employee", back_populates="assigned_alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "status": self.status,
            "priority": self.priority,
            "shelf_name": self.shelf_name,
            "rack_name": self.rack_name,
            "product_number": self.product_number,
            "product_name": self.product_name,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "expected_product": self.expected_product,
            "actual_product": self.actual_product,
            "correct_location": self.correct_location,
            "empty_percentage": self.empty_percentage,
            "fill_percentage": self.fill_percentage,
            "assigned_staff_id": self.assigned_staff_id,
            "created_by": self.created_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# -------------------- Pydantic Models --------------------

class AlertBase(BaseModel):
    alert_type: AlertType
    status: Optional[AlertStatus] = AlertStatus.ACTIVE
    priority: AlertPriority
    shelf_name: str
    product_number: Optional[str] = None
    product_name: Optional[str] = None
    title: str
    message: str
    expected_product: Optional[str] = None
    actual_product: Optional[str] = None
    correct_location: Optional[str] = None
    empty_percentage: Optional[float] = None
    fill_percentage: Optional[float] = None
    assigned_staff_id: Optional[str] = None
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AlertCreate(AlertBase):
    pass


class AlertRead(AlertBase):
    id: int
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
