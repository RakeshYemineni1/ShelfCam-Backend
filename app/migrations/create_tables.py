"""
Database migration script to create shelf and staff assignment tables
Run this after setting up your database connection and environment variables

File location: migrations/create_tables.py
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Add the project root to Python path to import app modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.database.db import Base
    from app.models.shelf import Shelf
    from app.models.staff_assignment import StaffAssignment, AssignmentHistory
    from app.models.employee import Employee
    from app.models.inventory import Inventory
except ImportError as e:
    print(f"❌ Error importing models: {e}")
    print("Make sure you're running this from the project root or migrations directory")
    sys.exit(1)

def load_environment():
    """Load environment variables from .env file"""
    # Look for .env file in current directory and parent directories
    env_path = Path('.env')
    if not env_path.exists():
        env_path = Path('../.env')
    if not env_path.exists():
        env_path = Path('../../.env')
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from: {env_path.absolute()}")
    else:
        print("⚠️  No .env file found. Using system environment variables.")

def get_database_url():
    """Construct database URL from environment variables"""
    # Try to get complete DATABASE_URL first
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Build from individual components
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'store_management')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    if not db_password:
        print("❌ Database password not found in environment variables")
        print("Please set DB_PASSWORD in your .env file or environment")
        sys.exit(1)
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def test_connection(engine):
    """Test database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Database connection successful")
        return True
    except SQLAlchemyError as e:
        print(f"❌ Database connection failed: {e}")
        return False

def run_migration():
    """Run the database migration"""
    print("🚀 Starting database migration...")
    
    # Load environment variables
    load_environment()
    
    # Get database URL
    try:
        database_url = get_database_url()
        print(f"📊 Connecting to database...")
        # Don't print the full URL to avoid exposing credentials
        url_parts = database_url.split('@')
        if len(url_parts) > 1:
            safe_url = f"postgresql://***:***@{url_parts[1]}"
        else:
            safe_url = "postgresql://***"
        print(f"   URL: {safe_url}")
    except Exception as e:
        print(f"❌ Error getting database URL: {e}")
        sys.exit(1)
    
    # Create engine
    try:
        engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debug output
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
        )
    except Exception as e:
        print(f"❌ Error creating database engine: {e}")
        sys.exit(1)
    
    # Test connection
    if not test_connection(engine):
        sys.exit(1)
    
    # Run migration
    try:
        print("📋 Creating tables...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database migration completed successfully!")
        print("📋 Created/verified tables:")
        print("   - employees")
        print("   - inventory")
        print("   - shelves")
        print("   - staff_assignments")
        print("   - assignment_history")
        print("   - Updated all tables with relationships")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"📊 Found {len(tables)} tables in database:")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("⚠️  No tables found in database")
                
    except SQLAlchemyError as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()