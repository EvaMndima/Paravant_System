"""System health check script."""
import sys
from pathlib import Path
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_python_version():
    """Check Python version."""
    import sys
    version = sys.version_info
    if version >= (3, 11):
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python version: {version.major}.{version.minor}.{version.micro} (3.11+ required)")
        return False


def check_dependencies():
    """Check if core dependencies are installed."""
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pandas",
        "pydantic",
        "python_binance",
        "telegram",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        return False
    else:
        print(f"✅ All {len(required_packages)} core dependencies installed")
        return True


def check_env_variables():
    """Check environment variables."""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ["DATABASE_URL"]
    optional_vars = ["BINANCE_API_KEY", "BINANCE_SECRET_KEY", "TELEGRAM_BOT_TOKEN"]
    
    missing_required = [var for var in required_vars if not os.getenv(var)]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        return False
    else:
        print("✅ Required environment variables present")
        
    if missing_optional:
        print(f"⚠️  Missing optional environment variables: {', '.join(missing_optional)}")
    
    return True


def check_database():
    """Check database connectivity."""
    try:
        from src.data.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    """Run all health checks."""
    print("=" * 50)
    print("SYSTEM HEALTH CHECK")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment Variables", check_env_variables),
        ("Database", check_database),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Error during {name} check: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ ALL CHECKS PASSED")
        print("=" * 50)
        return 0
    else:
        passed = sum(results)
        total = len(results)
        print(f"⚠️  {passed}/{total} CHECKS PASSED")
        print("=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
