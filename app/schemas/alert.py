from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


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


# -------------------- BASE SCHEMA --------------------

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


# -------------------- CREATE SCHEMA --------------------

class AlertCreate(AlertBase):
    pass


# -------------------- READ SCHEMA --------------------

class AlertRead(AlertBase):
    id: int
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# -------------------- LIST ITEM (Optional) --------------------

class AlertListItem(BaseModel):
    id: int
    title: str
    priority: AlertPriority
    status: AlertStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
