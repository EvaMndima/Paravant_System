"""Initialize database schema."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import init_db, engine


def main():
    """Initialize the database schema."""
    print("Initializing database...")
    
    try:
        # Create all tables
        init_db()
        print("✅ Database schema created successfully")
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
