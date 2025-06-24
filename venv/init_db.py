from app.core.database import engine
from app.models.inventory import Inventory

# Creates all tables
Inventory.metadata.create_all(bind=engine)
