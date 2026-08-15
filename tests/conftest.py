"""Shared pytest fixtures."""
import pytest
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Hermetic environment
# ---------------------------------------------------------------------------

# Environment variables that must never leak from a developer machine into a
# test run. BINANCE_TESTNET is the load-bearing one: a real .env setting it to
# "false" selects real-money mode, and that value was reaching the suite.
_LEAKY_ENV_PREFIXES = ("BINANCE_", "TELEGRAM_")

_LEAKY_ENV_NAMES = frozenset({
    "DATABASE_URL",
    "ENVIRONMENT",
    "DEBUG",
    "LOG_LEVEL",
    "TRADING_MODE",
    "PAPER_TRADING",
    "LIVE_TRADING_ENABLED",
    "LIVE_CAPITAL",
    "PER_STRATEGY_ALLOCATION_PCT",
    "POSITION_SIZE_FRACTION",
    "MAX_STRATEGIES_LIVE_CONCURRENT",
    "CAPITAL_RESERVE_FRACTION",
    "ALLOWED_ORIGINS",
    # A developer's real API key must not decide whether the auth gate is
    # exercised. Tests that need it set it explicitly.
    # Decision: DEC-2026-08-14-001
    "PARAVANT_API_KEY",
})

# Integration modules whose fixtures open a real connection to Binance during
# setup. They are auto-marked `binance` so a clean clone does not produce
# errors it cannot act on.
_NETWORK_TEST_MODULES = ("test_binance_client.py", "test_symbol_refresh.py")

_RUN_NETWORK_ENV = "PARAVANT_RUN_NETWORK_TESTS"


@pytest.fixture(autouse=True)
def hermetic_environment(request, monkeypatch):
    """Isolate every test from the developer's real environment.

    Two independent leaks are closed:

    1. ``os.environ`` -- BINANCE_*, TELEGRAM_*, DATABASE_URL and the
       live-trading switches are removed for the duration of each test.
    2. ``.env`` -- ``Settings`` is a pydantic-settings ``BaseSettings`` with
       ``env_file=".env"``, so instantiating it reads the developer's real file
       even when ``os.environ`` is already clean. ``env_file`` is therefore
       disabled for the test run.

    This is a safety fix before it is a hygiene fix. Without it,
    ``test_settings_defaults`` failed because the real ``.env`` sets
    ``BINANCE_TESTNET=false`` -- the suite was observing the setting that
    selects real-money mode.

    Tests marked ``binance`` opt out: they talk to the real testnet and need
    genuine credentials. They only run when ``PARAVANT_RUN_NETWORK_TESTS`` is
    set, so opting out cannot happen by accident.
    """
    if request.node.get_closest_marker("binance"):
        return

    for key in list(os.environ):
        if key.startswith(_LEAKY_ENV_PREFIXES) or key in _LEAKY_ENV_NAMES:
            monkeypatch.delenv(key, raising=False)

    # Disable .env discovery. Imported lazily so collection does not depend on
    # application import order.
    from src.core.config.settings import Settings

    monkeypatch.setitem(Settings.model_config, "env_file", None)


def pytest_collection_modifyitems(config, items):
    """Auto-mark and skip network-dependent tests.

    Integration tests against Binance previously produced 32 setup ERRORS on
    any machine without working exchange connectivity -- noise a contributor
    cannot distinguish from a real regression. They now skip by default and
    run only on explicit opt-in via ``PARAVANT_RUN_NETWORK_TESTS=1``.

    Opt-in is deliberately a flag rather than credential sniffing: presence of
    an API key should never be enough to start making live network calls.
    """
    run_network = os.environ.get(_RUN_NETWORK_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    skip_network = pytest.mark.skip(
        reason=f"network test; set {_RUN_NETWORK_ENV}=1 to run"
    )

    for item in items:
        module = Path(str(getattr(item, "fspath", ""))).name
        if module in _NETWORK_TEST_MODULES:
            item.add_marker(pytest.mark.binance)
        if "binance" in item.keywords and not run_network:
            item.add_marker(skip_network)


@pytest.fixture(scope="session")
def test_database_url():
    """Return test database URL."""
    return "sqlite:///:memory:"  # In-memory database for tests


@pytest.fixture(scope="function")
def db_engine(test_database_url):
    """Create test database engine with proper resource cleanup."""
    from src.data.models.base import Base

    from sqlalchemy import event

    engine = create_engine(
        test_database_url,
        connect_args={"check_same_thread": False},  # For SQLite
        poolclass=None  # Disable connection pooling for tests to prevent ResourceWarning
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # FIXED: Comprehensive cleanup to prevent ResourceWarning
    # Close all connections in the pool before disposing
    Base.metadata.drop_all(engine)
    engine.dispose()  # This should now properly close all connections


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create test database session with proper cleanup."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    yield session

    # FIXED: Ensure session is properly closed and rolled back
    try:
        session.rollback()  # Roll back any uncommitted changes
    finally:
        session.close()  # Always close the session


@pytest.fixture(scope="function")
def test_db(db_engine):
    """Alias for db_engine for test compatibility."""
    yield db_engine


@pytest.fixture(scope="session")
def api_client():
    """Create FastAPI test client with proper database cleanup."""
    # Set test environment
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    from src.api.main import app

    with TestClient(app) as client:
        yield client

    # FIXED MEDIUM-001: Explicitly dispose of any database engines created by the API
    # This prevents ResourceWarning from unclosed connections
    try:
        from src.data.database import engine
        engine.dispose()
    except Exception:
        pass  # Engine may not have been created, ignore


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
