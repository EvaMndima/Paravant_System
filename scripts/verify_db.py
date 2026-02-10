"""Verify database schema and connectivity."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import engine
from sqlalchemy import inspect, text


def main():
    """Verify database schema and connectivity."""
    print("Verifying database...")
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Database connection successful")
        
        # Verify schema
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("❌ No tables found. Run scripts/init_db.py first.")
            sys.exit(1)
            
        print(f"✅ Found {len(tables)} tables:")
        for table in sorted(tables):
            columns = inspector.get_columns(table)
            print(f"   - {table} ({len(columns)} columns)")
            
        # Expected tables
        expected_tables = {
            "accounts",
            "strategies",
            "orders",
            "positions",
            "strategy_assignments",
            "signals",
        }
        
        missing = expected_tables - set(tables)
        if missing:
            print(f"⚠️  Missing tables: {missing}")
        else:
            print("✅ All expected tables present")
            
        print("\n✅ Database verification complete")
        
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
