"""Tests for the DataStore query, update and persistence paths.

These target the methods that had no coverage from any suite: the order query
variants, the partial-update validators, the symbol registry, and the paper
session persistence used to restore state across container restarts.

Placed under `tests/unit/` deliberately. `DataStore` was previously exercised
only from `tests/integration/`, which the CI coverage job does not measure --
so a well-tested module reported 28% and was ranked as a finding
(DEC-2026-08-14-004). The measurement scope is fixed separately; these close
the paths that were genuinely untested either way.

Decision: DEC-2026-02-08-006 - Eager loading to prevent N+1 queries
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-08-14-004 - Coverage measured over the whole suite
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.data.models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperTradingSession,
    Position,
    PositionSide,
    PositionStatus,
    SymbolInfo,
    Trade,
)
from src.data.store import DataStore


@pytest.fixture
def store(test_db) -> DataStore:
    """A DataStore bound to the per-test SQLite engine."""
    s = DataStore()
    s.engine = test_db
    return s


def _order(account_id, strategy_id, *, status=OrderStatus.PENDING, **kw) -> Order:
    """Build a valid Order, overriding any field via kwargs."""
    fields = {
        "account_id": account_id,
        "strategy_id": strategy_id,
        "symbol": "BTCUSDT",
        "side": OrderSide.BUY,
        "type": OrderType.MARKET,
        "status": status,
        "quantity": Decimal("0.1"),
    }
    fields.update(kw)
    return Order(**fields)


def _position(account_id, strategy_id, **kw) -> Position:
    """Build a valid Position, overriding any field via kwargs."""
    fields = {
        "account_id": account_id,
        "strategy_id": strategy_id,
        "symbol": "BTCUSDT",
        "side": PositionSide.LONG,
        "status": PositionStatus.OPEN,
        "size": Decimal("0.5"),
        "entry_price": Decimal("50000.0"),
        "current_price": Decimal("50000.0"),
    }
    fields.update(kw)
    return Position(**fields)


def _symbol(symbol="BTCUSDT", **kw) -> SymbolInfo:
    """Build a valid SymbolInfo, overriding any field via kwargs."""
    fields = {
        "symbol": symbol,
        "base_asset": "BTC",
        "quote_asset": "USDT",
        "min_quantity": 0.00001,
        "max_quantity": 9000.0,
        "step_size": 0.00001,
        "tick_size": 0.01,
        "min_notional": 10.0,
    }
    fields.update(kw)
    return SymbolInfo(**fields)


class TestOrderQueries:
    """Order lookup variants."""

    def test_get_orders_by_status_filters(self, store, sample_account, sample_strategy):
        store.save_order(_order(sample_account.id, sample_strategy.id))
        store.save_order(
            _order(sample_account.id, sample_strategy.id, status=OrderStatus.FILLED)
        )

        pending = store.get_orders_by_status(OrderStatus.PENDING)
        statuses = [o.status for o in pending]

        assert len(pending) == 1
        assert statuses == [OrderStatus.PENDING]

    def test_get_orders_by_status_returns_detached_objects(
        self, store, sample_account, sample_strategy
    ):
        """Rows are expunged before return. Reading an attribute after the
        session closes must not raise DetachedInstanceError -- the eager loads
        exist precisely so callers can use the result outside the session."""
        store.save_order(_order(sample_account.id, sample_strategy.id))

        orders = store.get_orders_by_status(OrderStatus.PENDING)

        assert orders[0].symbol == "BTCUSDT"

    def test_get_orders_by_account_and_status_without_filter(
        self, store, sample_account, sample_strategy
    ):
        store.save_order(_order(sample_account.id, sample_strategy.id))
        store.save_order(
            _order(sample_account.id, sample_strategy.id, status=OrderStatus.FILLED)
        )

        assert len(store.get_orders_by_account_and_status(sample_account.id)) == 2

    def test_get_orders_by_account_and_status_with_filter(
        self, store, sample_account, sample_strategy
    ):
        store.save_order(_order(sample_account.id, sample_strategy.id))
        store.save_order(
            _order(sample_account.id, sample_strategy.id, status=OrderStatus.FILLED)
        )

        filled = store.get_orders_by_account_and_status(
            sample_account.id, OrderStatus.FILLED
        )

        assert len(filled) == 1

    def test_get_orders_by_account_and_status_scopes_to_account(
        self, store, sample_account, sample_strategy
    ):
        store.save_order(_order(sample_account.id, sample_strategy.id))

        assert store.get_orders_by_account_and_status("acct_does_not_exist") == []

    def test_count_open_orders_counts_all_active_states(
        self, store, sample_account, sample_strategy
    ):
        """PENDING, SUBMITTED and PARTIALLY_FILLED are all non-terminal. Missing
        one would under-report exposure to the risk layer."""
        for status in (
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        ):
            store.save_order(
                _order(sample_account.id, sample_strategy.id, status=status)
            )

        assert store.count_open_orders(sample_account.id) == 3

    def test_count_open_orders_excludes_terminal_states(
        self, store, sample_account, sample_strategy
    ):
        for status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        ):
            store.save_order(
                _order(sample_account.id, sample_strategy.id, status=status)
            )

        assert store.count_open_orders(sample_account.id) == 0

    def test_count_open_orders_is_zero_for_unknown_account(self, store):
        assert store.count_open_orders("acct_does_not_exist") == 0

    def test_get_order_by_external_id_found(
        self, store, sample_account, sample_strategy
    ):
        """Reconciliation path: Binance returns its own ID and it must map back
        to an internal order."""
        store.save_order(
            _order(sample_account.id, sample_strategy.id, external_id="BINANCE-77")
        )

        found = store.get_order_by_external_id("BINANCE-77")

        assert found is not None
        assert found.external_id == "BINANCE-77"

    def test_get_order_by_external_id_missing_returns_none(self, store):
        assert store.get_order_by_external_id("no-such-id") is None


class TestUpdateOrder:
    """Partial updates, and the validation that guards them."""

    def test_updates_the_named_fields(self, store, sample_account, sample_strategy):
        saved = store.save_order(_order(sample_account.id, sample_strategy.id))

        updated = store.update_order(
            saved.id, status=OrderStatus.SUBMITTED, external_id="BINANCE-1"
        )

        assert updated is not None
        assert updated.status == OrderStatus.SUBMITTED
        assert updated.external_id == "BINANCE-1"

    def test_unknown_order_id_returns_none(self, store):
        """None, not an exception: a missing order is an expected outcome during
        reconciliation, not a programming error."""
        assert store.update_order("ord_does_not_exist", status=OrderStatus.FILLED) is None

    def test_invalid_field_name_raises(self, store, sample_account, sample_strategy):
        """Without this guard a typo would silently set an attribute that is
        never persisted, and the caller would believe the write succeeded."""
        saved = store.save_order(_order(sample_account.id, sample_strategy.id))

        with pytest.raises(ValueError, match="Invalid Order fields"):
            store.update_order(saved.id, nonexistent_column="x")

    def test_validation_happens_before_any_write(
        self, store, sample_account, sample_strategy
    ):
        """A mix of one valid and one invalid field must write neither."""
        saved = store.save_order(_order(sample_account.id, sample_strategy.id))

        with pytest.raises(ValueError):
            store.update_order(saved.id, status=OrderStatus.FILLED, bogus=1)

        assert store.get_order(saved.id).status == OrderStatus.PENDING


class TestPositionQueries:
    """Position lookup and partial update."""

    def test_get_positions_for_account(self, store, sample_account, sample_strategy):
        store.save_position(_position(sample_account.id, sample_strategy.id))
        store.save_position(
            _position(sample_account.id, sample_strategy.id, symbol="ETHUSDT")
        )

        positions = store.get_positions_for_account(sample_account.id)

        assert len(positions) == 2
        assert {p.symbol for p in positions} == {"BTCUSDT", "ETHUSDT"}

    def test_get_positions_for_unknown_account_is_empty(self, store):
        assert store.get_positions_for_account("acct_does_not_exist") == []

    def test_update_position_updates_fields(
        self, store, sample_account, sample_strategy
    ):
        saved = store.save_position(_position(sample_account.id, sample_strategy.id))

        updated = store.update_position(saved.id, current_price=Decimal("51000.0"))

        assert updated is not None
        assert updated.current_price == Decimal("51000.0")

    def test_update_position_unknown_id_returns_none(self, store):
        assert store.update_position("pos_does_not_exist", size=Decimal("1")) is None

    def test_update_position_invalid_field_raises(
        self, store, sample_account, sample_strategy
    ):
        saved = store.save_position(_position(sample_account.id, sample_strategy.id))

        with pytest.raises(ValueError, match="Invalid Position fields"):
            store.update_position(saved.id, nonexistent_column="x")


class TestTradeQueries:
    """Trade history, including the date-filtered path."""

    @staticmethod
    def _trade(order_id, account_id, executed_at) -> Trade:
        return Trade(
            order_id=order_id,
            account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            executed_at=executed_at,
        )

    def test_start_date_filter_excludes_older_trades(
        self, store, sample_account, sample_strategy
    ):
        order = store.save_order(_order(sample_account.id, sample_strategy.id))
        now = datetime.now(timezone.utc)

        store.save_trade(
            self._trade(order.id, sample_account.id, now - timedelta(days=10))
        )
        store.save_trade(self._trade(order.id, sample_account.id, now))

        recent = store.get_trades_for_account(
            sample_account.id, start_date=now - timedelta(days=1)
        )

        assert len(recent) == 1

    def test_without_start_date_returns_all(
        self, store, sample_account, sample_strategy
    ):
        order = store.save_order(_order(sample_account.id, sample_strategy.id))
        now = datetime.now(timezone.utc)

        store.save_trade(
            self._trade(order.id, sample_account.id, now - timedelta(days=10))
        )
        store.save_trade(self._trade(order.id, sample_account.id, now))

        assert len(store.get_trades_for_account(sample_account.id)) == 2


class TestSystemStateAndAudit:
    """System state fields and audit log filters that had no coverage."""

    def test_update_last_trade_and_health_check_timestamps(self, store):
        now = datetime.now(timezone.utc)

        state = store.update_system_state(last_trade_at=now, last_health_check=now)

        assert state.last_trade_at is not None
        assert state.last_health_check is not None

    def test_partial_update_leaves_other_fields_alone(self, store):
        """Every field is optional and None means 'do not touch'. A regression
        here would silently reset the kill switch on an unrelated update."""
        store.update_system_state(kill_switch_active=True, trading_enabled=False)

        store.update_system_state(last_health_check=datetime.now(timezone.utc))

        state = store.get_system_state()
        assert state.kill_switch_active is True
        assert state.trading_enabled is False

    def test_audit_logs_filtered_by_start_time(self, store):
        store.add_audit_log(action="kill_switch_activated", actor="operator")

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
        recent = store.get_audit_logs(start_time=cutoff)

        assert len(recent) >= 1

    def test_audit_logs_start_time_excludes_older(self, store):
        store.add_audit_log(action="kill_switch_activated", actor="operator")

        future = datetime.now(timezone.utc) + timedelta(days=1)

        assert store.get_audit_logs(start_time=future) == []


class TestSymbolRegistry:
    """Symbol info persistence and the two filter branches."""

    def test_save_and_get_symbol_info(self, store):
        store.save_symbol_info(_symbol())

        found = store.get_symbol_info("BTCUSDT")

        assert found is not None
        assert found.base_asset == "BTC"
        assert found.min_notional == 10.0

    def test_get_symbol_info_missing_returns_none(self, store):
        assert store.get_symbol_info("NOPEUSDT") is None

    def test_get_all_symbols_orders_by_symbol(self, store):
        store.save_symbol_info(_symbol("ETHUSDT", base_asset="ETH"))
        store.save_symbol_info(_symbol("BTCUSDT"))

        symbols = [s.symbol for s in store.get_all_symbols()]

        assert symbols == ["BTCUSDT", "ETHUSDT"]

    def test_trading_only_filter(self, store):
        """Delisted pairs stay in the table but must not be offered for trading."""
        store.save_symbol_info(_symbol("BTCUSDT"))
        store.save_symbol_info(_symbol("DEADUSDT", base_asset="DEAD", is_trading=False))

        tradable = [s.symbol for s in store.get_all_symbols(trading_only=True)]

        assert tradable == ["BTCUSDT"]

    def test_quote_asset_filter(self, store):
        store.save_symbol_info(_symbol("BTCUSDT"))
        store.save_symbol_info(
            _symbol("ETHBTC", base_asset="ETH", quote_asset="BTC")
        )

        usdt = [s.symbol for s in store.get_all_symbols(quote_asset="USDT")]

        assert usdt == ["BTCUSDT"]

    def test_filters_combine(self, store):
        store.save_symbol_info(_symbol("BTCUSDT"))
        store.save_symbol_info(_symbol("DEADUSDT", base_asset="DEAD", is_trading=False))
        store.save_symbol_info(
            _symbol("ETHBTC", base_asset="ETH", quote_asset="BTC")
        )

        result = [
            s.symbol
            for s in store.get_all_symbols(trading_only=True, quote_asset="USDT")
        ]

        assert result == ["BTCUSDT"]


class TestPaperSessionPersistence:
    """State that must survive a container restart.

    `upsert_paper_session` is called after every poll cycle and
    `get_paper_session` on engine startup. If this round-trip is broken, a
    Railway redeploy silently resets paper trading history -- which is the
    evidence the promotion gate reads.
    """

    @staticmethod
    def _session(session_id="paper_BTF_BTCUSDT", **kw) -> PaperTradingSession:
        fields = {
            "session_id": session_id,
            "template_id": "BTF",
            "symbol": "BTCUSDT",
            "initial_capital": 1000.0,
            "cash": 1000.0,
            "total_trades": 0,
        }
        fields.update(kw)
        return PaperTradingSession(**fields)

    def test_round_trip(self, store):
        store.upsert_paper_session(self._session(cash=950.0, total_trades=3))

        loaded = store.get_paper_session("paper_BTF_BTCUSDT")

        assert loaded is not None
        assert loaded.cash == 950.0
        assert loaded.total_trades == 3

    def test_upsert_replaces_rather_than_duplicating(self, store):
        """It is called every poll cycle. Inserting instead of merging would
        grow the table without bound and break the primary key."""
        store.upsert_paper_session(self._session(cash=1000.0, total_trades=0))
        store.upsert_paper_session(self._session(cash=900.0, total_trades=5))

        assert len(store.list_paper_sessions()) == 1
        assert store.get_paper_session("paper_BTF_BTCUSDT").cash == 900.0

    def test_missing_session_returns_none(self, store):
        """A fresh start, not an error."""
        assert store.get_paper_session("paper_NEVER_EXISTED") is None

    def test_list_returns_newest_first(self, store):
        now = datetime.now(timezone.utc)
        store.upsert_paper_session(
            self._session("paper_OLD", started_at=now - timedelta(days=2))
        )
        store.upsert_paper_session(self._session("paper_NEW", started_at=now))

        ids = [s.session_id for s in store.list_paper_sessions()]

        assert ids == ["paper_NEW", "paper_OLD"]

    def test_list_is_empty_when_none_persisted(self, store):
        assert store.list_paper_sessions() == []
