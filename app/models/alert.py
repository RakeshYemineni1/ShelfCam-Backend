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
    MISPLACED_ITEM = "misplaced_item"

class AlertStatus(enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"

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
    rack_name = Column(String(50), nullable=False)  # From inventory table
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
    
    # Assignment and tracking
    assigned_staff_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    notified_staff_ids = Column(Text, nullable=True)  # JSON array of notified staff IDs
    created_by = Column(String(50), default="system")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    assigned_staff = relationship("Employee", foreign_keys=[assigned_staff_id])