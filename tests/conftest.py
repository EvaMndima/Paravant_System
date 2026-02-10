"""Shared pytest fixtures."""
import pytest
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_database_url():
    """Return test database URL."""
    return "sqlite:///:memory:"  # In-memory database for tests


@pytest.fixture(scope="function")
def db_engine(test_database_url):
    """Create test database engine."""
    from src.data.models.base import Base
    
    from sqlalchemy import event

    engine = create_engine(
        test_database_url,
        connect_args={"check_same_thread": False}  # For SQLite
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture(scope="function")
def test_db(db_engine):
    """Alias for db_engine for test compatibility."""
    yield db_engine


@pytest.fixture(scope="session")
def api_client():
    """Create FastAPI test client."""
    # Set test environment
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from src.api.main import app
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    return [
        {
            "timestamp": 1704067200000,
            "open": 42000,
            "high": 42500,
            "low": 41800,
            "close": 42300,
            "volume": 100,
        },
        {
            "timestamp": 1704070800000,
            "open": 42300,
            "high": 42800,
            "low": 42100,
            "close": 42600,
            "volume": 150,
        },
        {
            "timestamp": 1704074400000,
            "open": 42600,
            "high": 42900,
            "low": 42400,
            "close": 42700,
            "volume": 120,
        },
    ]


@pytest.fixture
def test_config_path(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_binance_client(mocker):
    """Mock Binance client for testing."""
    return mocker.MagicMock()


@pytest.fixture
def sample_account(db_session):
    """Create a sample account for testing."""
    from src.data.models import Account, AccountStatus, RiskProfile
    
    account = Account(
        name="Test Account",
        broker="binance",
        profile=RiskProfile.BALANCED,  # Correct field name
        status=AccountStatus.ACTIVE,
        balance_usdt=10000.0,
        equity_usdt=10000.0,
        regime="unknown",
        risk_config={}
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def sample_strategy(db_session):
    """Create a sample strategy for testing."""
    from src.data.models import Strategy, StrategyStatus, StrategyType
    
    strategy = Strategy(
        name="Test Strategy",  # ADDED: Required field
        template_id="test_template",
        template_version="1.0.0",
        type=StrategyType.TREND_FOLLOWING,
        status=StrategyStatus.DRAFT,
        parameters={"period": 10, "threshold": 0.5},
        symbols=["BTCUSDT"],
        backtest_results={},
        paper_results={},
        live_results={},
        lifecycle=[]
    )
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)
    return strategy


@pytest.fixture
def sample_order(db_session, sample_account, sample_strategy):
    """Create a sample order for testing."""
    from src.data.models import Order, OrderSide, OrderType, OrderStatus
    
    order = Order(
        account_id=sample_account.id,
        strategy_id=sample_strategy.id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        status=OrderStatus.PENDING,
        filled_quantity=0.0,
        filled_price=None  # Fixed: was average_fill_price
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order
