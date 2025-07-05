from sqlalchemy import Column, Integer, String
from app.database.db import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)  # ✅ must match DB column
    role = Column(String)
