from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

# Import other schemas
from app.schemas.employee import EmployeeResponse
from app.schemas.shelf import ShelfResponse


class AssignmentStatus(str, Enum):
    """Assignment status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"


class AssignmentPriority(str, Enum):
    """Assignment priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Base Staff Assignment Schemas
class StaffAssignmentBase(BaseModel):
    """Base staff assignment schema"""
    employee_id: str = Field(..., description="Employee ID (string from employees.employee_id)")
    shelf_id: str = Field(..., description="Shelf name (string from shelves.name)")
    assigned_date: datetime = Field(..., description="Assignment date")
    due_date: Optional[datetime] = Field(None, description="Due date")
    status: AssignmentStatus = Field(AssignmentStatus.ACTIVE, description="Assignment status")
    priority: AssignmentPriority = Field(AssignmentPriority.MEDIUM, description="Assignment priority")
    notes: Optional[str] = Field(None, description="Assignment notes")


class StaffAssignmentCreate(StaffAssignmentBase):
    """Create staff assignment schema"""
    pass


class StaffAssignmentUpdate(BaseModel):
    """Update staff assignment schema"""
    due_date: Optional[datetime] = None
    status: Optional[AssignmentStatus] = None
    priority: Optional[AssignmentPriority] = None
    notes: Optional[str] = None


class StaffAssignmentResponse(StaffAssignmentBase):
    """Staff assignment response schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    # Relationships
    employee: Optional[EmployeeResponse] = None
    shelf: Optional[ShelfResponse] = None
    assigned_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Assignment History Schemas
class AssignmentHistoryBase(BaseModel):
    """Base assignment history schema"""
    assignment_id: int = Field(..., description="Assignment ID")
    action: str = Field(..., description="Action performed")
    old_status: Optional[AssignmentStatus] = None
    new_status: Optional[AssignmentStatus] = None
    notes: Optional[str] = None
    created_by: int = Field(..., description="User who created the history entry")


class AssignmentHistoryCreate(AssignmentHistoryBase):
    """Create assignment history schema"""
    pass


class AssignmentHistoryResponse(AssignmentHistoryBase):
    """Assignment history response schema"""
    id: int
    timestamp: datetime
    assignment: Optional[StaffAssignmentResponse] = None

    model_config = ConfigDict(from_attributes=True)


# Extended Schemas for Dashboard and Reports
class AssignmentWithDetails(BaseModel):
    """Assignment with detailed information"""
    id: int
    employee_id: str
    shelf_id: str
    assigned_date: datetime
    due_date: Optional[datetime] = None
    status: AssignmentStatus
    priority: AssignmentPriority
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Employee details
    employee_name: str
    employee_email: str
    employee_phone: Optional[str] = None

    # Shelf details
    shelf_name: str
    shelf_location: str
    shelf_capacity: int

    model_config = ConfigDict(from_attributes=True)


class ShelfWithAssignments(BaseModel):
    id: int
    name: str
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    capacity: int
    assigned_staff_count: int
    assigned_staff: List[str]

    model_config = ConfigDict(from_attributes=True)

    # Assignments for this shelf
    assignments: List[AssignmentWithDetails] = Field(default_factory=list)

    # Statistics
    total_assignments: int = 0
    active_assignments: int = 0
    pending_assignments: int = 0
    completed_assignments: int = 0

    model_config = ConfigDict(from_attributes=True)


class EmployeeWithAssignments(BaseModel):
    """Employee with their assignments"""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None

    # Assignments for this employee
    assignments: List[AssignmentWithDetails] = Field(default_factory=list)

    # Statistics
    total_assignments: int = 0
    active_assignments: int = 0
    pending_assignments: int = 0
    completed_assignments: int = 0

    model_config = ConfigDict(from_attributes=True)


class AssignmentDashboardResponse(BaseModel):
    """Dashboard response with assignment overview"""
    total_assignments: int = 0
    active_assignments: int = 0
    pending_assignments: int = 0
    completed_assignments: int = 0
    overdue_assignments: int = 0

    # Recent assignments
    recent_assignments: List[AssignmentWithDetails] = Field(default_factory=list)

    # Shelves with assignments
    shelves_with_assignments: List[ShelfWithAssignments] = Field(default_factory=list)

    # Employees with assignments
    employees_with_assignments: List[EmployeeWithAssignments] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssignmentFilters(BaseModel):
    """Filters for assignment queries"""
    employee_id: Optional[str] = None
    shelf_id: Optional[str] = None
    status: Optional[AssignmentStatus] = None
    priority: Optional[AssignmentPriority] = None
    assigned_date_from: Optional[datetime] = None
    assigned_date_to: Optional[datetime] = None
    due_date_from: Optional[datetime] = None
    due_date_to: Optional[datetime] = None
    overdue_only: bool = False

    model_config = ConfigDict(from_attributes=True)


class AssignmentListResponse(BaseModel):
    """Paginated assignment list response"""
    assignments: List[AssignmentWithDetails]
    total: int
    page: int
    per_page: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


# Bulk operations
class BulkAssignmentCreate(BaseModel):
    """Bulk assignment creation"""
    assignments: List[StaffAssignmentCreate] = Field(..., min_length=1)

    model_config = ConfigDict(from_attributes=True)


class BulkAssignmentUpdate(BaseModel):
    """Bulk assignment update"""
    assignment_ids: List[int] = Field(..., min_length=1)
    updates: StaffAssignmentUpdate

    model_config = ConfigDict(from_attributes=True)


class BulkAssignmentResponse(BaseModel):
    """Bulk operation response"""
    success: bool
    message: str
    processed: int
    failed: int
    errors: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Statistics and Analytics
class AssignmentStats(BaseModel):
    """Assignment statistics"""
    total_assignments: int
    assignments_by_status: dict[AssignmentStatus, int]
    assignments_by_priority: dict[AssignmentPriority, int]
    average_completion_time: Optional[float] = None  # in days
    overdue_rate: float = 0.0  # percentage

    model_config = ConfigDict(from_attributes=True)


class PerformanceMetrics(BaseModel):
    """Performance metrics for employees"""
    employee_id: str
    employee_name: str
    total_assignments: int
    completed_assignments: int
    pending_assignments: int
    overdue_assignments: int
    completion_rate: float = 0.0  # percentage
    average_completion_time: Optional[float] = None  # in days

    model_config = ConfigDict(from_attributes=True)


class AssignmentReportResponse(BaseModel):
    """Assignment report response"""
    period_start: datetime
    period_end: datetime
    overall_stats: AssignmentStats
    employee_performance: List[PerformanceMetrics] = Field(default_factory=list)
    shelf_utilization: List[dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AvailableStaffResponse(BaseModel):
    employee_id: str
    username: str
    role: str
