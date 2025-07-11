# app/models/employee.py (Updated to include relationships)
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.database.db import Base
from app.models.staff_assignment import StaffAssignment
from app.models.alert_history import AlertHistory


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)  # ✅ must match DB column
    role = Column(String)
    email = Column(String)
    phone = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Relationships for staff assignments
    assignments = relationship("StaffAssignment", foreign_keys="[StaffAssignment.employee_id]", back_populates="employee")
    assigned_assignments = relationship("StaffAssignment", foreign_keys="[StaffAssignment.assigned_by]", back_populates="assigned_by_manager")
    alerts = relationship("AlertHistory", back_populates="employee")
    assigned_alerts = relationship(
    "Alert",
    back_populates="assigned_staff"
    )



