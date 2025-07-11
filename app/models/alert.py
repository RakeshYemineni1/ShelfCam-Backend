# app/models/alert.py - FIXED VERSION
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database.db import Base
from datetime import datetime
import enum

class AlertType(enum.Enum):
    LOW_STOCK = "low_stock"
    MEDIUM_STOCK = "medium_stock"
    HIGH_STOCK = "high_stock"
    CRITICAL_STOCK = "critical_stock"
    OUT_OF_STOCK = "out_of_stock"
    MISPLACED_ITEM = "misplaced_item"

class AlertStatus(enum.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class AlertPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    priority = Column(SQLEnum(AlertPriority), nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE)
    
    # Location details
    shelf_name = Column(String(100), nullable=False)
    rack_name = Column(String(50), nullable=False)
    product_number = Column(String(50), nullable=True)
    product_name = Column(String(200), nullable=True)
    category = Column(String(50), nullable=True)
    
    # Alert details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    empty_percentage = Column(Float, nullable=True)
    fill_percentage = Column(Float, nullable=True)
    
    # Misplacement details
    expected_product = Column(String(200), nullable=True)
    actual_product = Column(String(200), nullable=True)
    correct_location = Column(String(100), nullable=True)
    
    # Assignment and tracking - FIXED FOREIGN KEY
    assigned_staff_id = Column(String, ForeignKey("employees.employee_id"), nullable=True)
    notified_staff_ids = Column(Text, nullable=True)  # JSON array of notified staff IDs
    created_by = Column(String, default="system")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships - FIXED
    assigned_staff = relationship("Employee",  back_populates="assigned_alerts", primaryjoin="Alert.assigned_staff_id==Employee.employee_id")

    def to_dict(self):
        """Convert alert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "alert_type": self.alert_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "shelf_name": self.shelf_name,
            "rack_name": self.rack_name,
            "product_number": self.product_number,
            "product_name": self.product_name,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "empty_percentage": self.empty_percentage,
            "fill_percentage": self.fill_percentage,
            "expected_product": self.expected_product,
            "actual_product": self.actual_product,
            "correct_location": self.correct_location,
            "assigned_staff_id": self.assigned_staff_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "assigned_staff": {
                "employee_id": self.assigned_staff.employee_id,
                "username": self.assigned_staff.username,
                "email": self.assigned_staff.email
            } if self.assigned_staff else None
        }