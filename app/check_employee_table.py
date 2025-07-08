# check_employee_table.py - Check what's actually in your database

import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Row

from dotenv import load_dotenv

load_dotenv()

def check_employees():
    """Check employees in database"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env file")
        return
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if employees table exists
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'employees'
            """))
            
            if not result.fetchone():
                print("❌ 'employees' table doesn't exist!")
                print("🔧 You need to create the employees table first")
                return
            
            print("✅ Employees table exists")
            
            # Get all employees
            result = conn.execute(text("SELECT * FROM employees"))
            employees = result.mappings().all()  # returns dict-like rows

            
            if not employees:
                print("❌ No employees found in database!")
                print("🔧 You need to insert employee data")
                return
            
            print(f"📊 Found {len(employees)} employees:")
            print("-" * 60)
            for emp in employees:
                print(f"Employee ID: {emp['employee_id']}")
                print(f"Username: {emp['username']}")
                print(f"Role: {emp['role']}")

                
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_employees()
