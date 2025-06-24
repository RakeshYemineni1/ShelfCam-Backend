# app/models/inventory.py
from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, index=True)
    category = Column(String)
    stock = Column(Integer)
