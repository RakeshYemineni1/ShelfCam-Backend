from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.db import Base


class AlertHistory(Base):
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    action = Column(String(50), nullable=False)  # created, acknowledged, resolved
    performed_by = Column(String, ForeignKey("employees.employee_id"), nullable=True)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    alert = relationship("Alert")
    employee = relationship("Employee", foreign_keys=[performed_by])
