from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.db import Base
from datetime import datetime


class StaffAssignment(Base):
    __tablename__ = "staff_assignments"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"))
    shelf_id = Column(String, ForeignKey("shelves.name"))
    assigned_by = Column(String, ForeignKey("employees.employee_id"))
    is_active = Column(Boolean, default=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)

    employee = relationship("Employee", foreign_keys=[employee_id])
    assigned_by_manager = relationship("Employee", foreign_keys=[assigned_by])
    shelf = relationship("Shelf", foreign_keys=[shelf_id])

class AssignmentHistory(Base):
    __tablename__ = "assignment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Match employee_id with string if it's like 'E201'
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    shelf_id = Column(String, ForeignKey("shelves.name")) 
    
    action = Column(String, nullable=False)  # 'assigned', 'unassigned', 'transferred'
    action_date = Column(DateTime, default=datetime.utcnow)
    
    performed_by = Column(Integer, ForeignKey("employees.id"), nullable=False)  # manager's user.id
    notes = Column(Text, nullable=True)

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    shelf = relationship("Shelf", foreign_keys=[shelf_id])
    manager = relationship("Employee", foreign_keys=[performed_by])
