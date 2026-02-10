import sys
import os
sys.path.append(os.getcwd())
print(f"Python executable: {sys.executable}")
try:
    import sqlalchemy
    print(f"SQLAlchemy version: {sqlalchemy.__version__}")
    print(f"   Path: {sqlalchemy.__file__}")
except ImportError as e:
    print(f"FAIL: SQLAlchemy import failed: {e}")

try:
    import dotenv
    print(f"python-dotenv version: {dotenv.__version__ if hasattr(dotenv, '__version__') else 'installed'}")
    print(f"   Path: {dotenv.__file__}")
except ImportError as e:
    print(f"FAIL: python-dotenv import failed: {e}")

try:
    from src.data.database import get_db
    print("src.data.database imported successfully")
except ImportError as e:
    print(f"FAIL: src.data.database import failed: {e}")
