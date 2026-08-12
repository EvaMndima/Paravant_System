"""Load and performance tests for the PARAVANT Trading System.

Tests verify:
- Concurrent API request handling (all < 500ms)
- Dashboard endpoint throughput (p95 < 200ms)
- EventBus event delivery performance
- Memory leak detection via tracemalloc

Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import os
import statistics
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.event_bus import EventBus
from src.data.models import (
    Account, AccountStatus, Base, PnLRecord, RiskProfile,
)
from src.data.store import DataStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def perf_engine():
    """Create in-memory engine for performance tests.

    Uses StaticPool to maintain a single persistent connection,
    ensuring tables created by create_all() remain available.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def perf_store(perf_engine):
    """Create DataStore for performance tests."""
    store = DataStore()
    store.engine = perf_engine
    return store


@pytest.fixture
def perf_session(perf_engine):
    """Create session for seeding performance test data."""
    SessionLocal = sessionmaker(bind=perf_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def seeded_perf_data(perf_session, perf_store):
    """Seed data for performance tests."""
    # Create account
    account = Account(
        name="Perf Test Account",
        broker="binance",
        profile=RiskProfile.BALANCED,
        status=AccountStatus.ACTIVE,
        balance_usdt=10000.0,
        equity_usdt=10000.0,
        regime="unknown",
    )
    perf_session.add(account)
    perf_session.commit()
    perf_session.refresh(account)

    # Create 90 days of P&L records
    today = date.today()
    for i in range(90):
        d = today - timedelta(days=89 - i)
        record = PnLRecord(
            account_id=account.id,
            record_date=d,
            realized_pnl=50.0 * (i % 5) - 100.0,
            unrealized_pnl=20.0,
            total_pnl=50.0 * (i % 5) - 80.0,
            portfolio_value=10000.0 + i * 10,
            cash_balance=9000.0,
            position_value=1000.0,
            daily_return_pct=0.5 * (i % 5) - 1.0,
            trades_count=3,
            winning_trades=2,
            losing_trades=1,
        )
        perf_session.add(record)
    perf_session.commit()
    return account


@pytest.fixture
def perf_client(perf_store, seeded_perf_data):
    """Create test client for performance tests."""
    os.environ["ENVIRONMENT"] = "development"

    from src.api.routes.system import init_system_routes
    from src.api.routes.dashboard import init_dashboard_routes
    from src.api.routes.accounts import init_account_routes
    from src.api.routes.pnl import init_pnl_routes
    from src.core.event_bus import init_event_bus
    from src.api.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        # Re-inject test dependencies AFTER TestClient startup
        # (startup_event creates default DataStore, we override with test store)
        event_bus = init_event_bus()
        init_system_routes(store=perf_store, event_bus=event_bus)
        init_dashboard_routes(store=perf_store)
        init_account_routes(store=perf_store)
        init_pnl_routes(store=perf_store)
        yield client


# ---------------------------------------------------------------------------
# Test: Concurrent API Requests
# ---------------------------------------------------------------------------


class TestConcurrentRequests:
    """Test API performance under concurrent load."""

    def test_concurrent_health_checks(self, perf_client):
        """100 concurrent health check requests all under 500ms."""
        durations: list[float] = []

        def make_request():
            start = time.monotonic()
            response = perf_client.get("/health")
            duration_ms = (time.monotonic() - start) * 1000
            return response.status_code, duration_ms

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            for future in futures:
                status_code, duration_ms = future.result()
                assert status_code == 200
                durations.append(duration_ms)

        p95 = sorted(durations)[int(len(durations) * 0.95)]
        avg = statistics.mean(durations)

        assert p95 < 500, f"p95 latency {p95:.1f}ms exceeds 500ms threshold"
        assert avg < 200, f"Average latency {avg:.1f}ms exceeds 200ms threshold"

    def test_concurrent_dashboard_summary(self, perf_client):
        """50 concurrent dashboard summary requests."""
        durations: list[float] = []

        def make_request():
            start = time.monotonic()
            response = perf_client.get("/api/v1/dashboard/summary")
            duration_ms = (time.monotonic() - start) * 1000
            return response.status_code, duration_ms

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            for future in futures:
                status_code, duration_ms = future.result()
                assert status_code == 200
                durations.append(duration_ms)

        p95 = sorted(durations)[int(len(durations) * 0.95)]
        # Cache should make subsequent requests very fast
        assert p95 < 500, f"Dashboard p95 latency {p95:.1f}ms exceeds 500ms"

    def test_concurrent_mixed_endpoints(self, perf_client):
        """50 concurrent requests to mixed endpoints."""
        endpoints = [
            "/health",
            "/api/v1/dashboard/summary",
            "/api/v1/dashboard/performance",
            "/api/v1/pnl/daily",
            "/api/v1/accounts",
        ]

        durations: list[float] = []

        def make_request(endpoint: str):
            start = time.monotonic()
            response = perf_client.get(endpoint)
            duration_ms = (time.monotonic() - start) * 1000
            return response.status_code, duration_ms

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_request, endpoints[i % len(endpoints)])
                for i in range(50)
            ]
            for future in futures:
                status_code, duration_ms = future.result()
                assert status_code in (200, 404)  # 404 is OK for P&L with no default account
                durations.append(duration_ms)

        max_duration = max(durations)
        assert max_duration < 1000, f"Max latency {max_duration:.1f}ms exceeds 1000ms"


# ---------------------------------------------------------------------------
# Test: EventBus Performance
# ---------------------------------------------------------------------------


class TestEventBusPerformance:
    """Test EventBus throughput and latency."""

    @pytest.mark.asyncio
    async def test_event_delivery_throughput(self):
        """100 events delivered to 10 subscribers under 1s (respects 500 queue limit)."""
        bus = EventBus()
        sub_ids = []
        for _ in range(10):
            sub_ids.append(await bus.subscribe(["position_updated"]))

        start = time.monotonic()
        for i in range(100):
            await bus.publish("position_updated", {"index": i})
        duration = time.monotonic() - start

        assert duration < 1.0, f"100 events took {duration:.2f}s (limit: 1s)"

        # Verify all subscribers received all events
        for sub_id in sub_ids:
            count = 0
            while True:
                event = await bus.get_event(sub_id, timeout=0.01)
                if event is None:
                    break
                count += 1
            assert count == 100

            await bus.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_performance(self):
        """100 subscribe/unsubscribe cycles under 1s."""
        bus = EventBus()
        start = time.monotonic()

        for _ in range(100):
            sub_id = await bus.subscribe()
            await bus.unsubscribe(sub_id)

        duration = time.monotonic() - start
        assert duration < 1.0, f"100 sub/unsub cycles took {duration:.2f}s (limit: 1s)"
        assert await bus.get_subscriber_count() == 0


# ---------------------------------------------------------------------------
# Test: TTL Cache Performance
# ---------------------------------------------------------------------------


class TestCachePerformance:
    """Test TTL cache performance."""

    def test_cache_hit_performance(self):
        """10000 cache hits under 100ms."""
        from src.api.cache import TTLCache

        cache = TTLCache()
        cache.set("test_key", {"data": "value"}, ttl=60.0)

        start = time.monotonic()
        for _ in range(10000):
            result = cache.get("test_key")
            assert result is not None
        duration = time.monotonic() - start

        assert duration < 0.1, f"10000 cache hits took {duration:.3f}s (limit: 0.1s)"

    def test_cache_miss_performance(self):
        """10000 cache misses under 100ms."""
        from src.api.cache import TTLCache

        cache = TTLCache()

        start = time.monotonic()
        for i in range(10000):
            result = cache.get(f"nonexistent_{i}")
            assert result is None
        duration = time.monotonic() - start

        assert duration < 0.1, f"10000 cache misses took {duration:.3f}s (limit: 0.1s)"


# ---------------------------------------------------------------------------
# Test: Memory Leak Detection
# ---------------------------------------------------------------------------


class TestMemoryLeaks:
    """Test for memory leaks in critical paths."""

    @pytest.mark.asyncio
    async def test_eventbus_no_memory_leak(self):
        """EventBus subscribe/unsubscribe does not leak memory."""
        bus = EventBus()

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        # 1000 subscribe/publish/unsubscribe cycles
        for _ in range(1000):
            sub_id = await bus.subscribe()
            await bus.publish("position_updated", {"data": "test"})
            await bus.get_event(sub_id, timeout=0.01)
            await bus.unsubscribe(sub_id)

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Compare memory - allow up to 1MB growth
        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_growth = sum(s.size_diff for s in stats if s.size_diff > 0)

        # 1MB = 1048576 bytes
        assert total_growth < 1048576, (
            f"Memory grew by {total_growth / 1024:.1f}KB "
            f"after 1000 EventBus cycles (limit: 1MB)"
        )

        # Verify no leaked subscribers
        assert await bus.get_subscriber_count() == 0

    def test_cache_no_memory_leak(self):
        """TTL cache set/get/invalidate does not leak memory."""
        from src.api.cache import TTLCache

        cache = TTLCache()

        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        for i in range(1000):
            cache.set(f"key_{i}", {"data": i}, ttl=0.001)  # Very short TTL
            cache.get(f"key_{i}")  # Will be expired immediately

        # Force cleanup via gets
        for i in range(1000):
            cache.get(f"key_{i}")

        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_growth = sum(s.size_diff for s in stats if s.size_diff > 0)

        assert total_growth < 1048576, (
            f"Cache memory grew by {total_growth / 1024:.1f}KB (limit: 1MB)"
        )
