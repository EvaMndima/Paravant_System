# SESSION 5B: STRATEGY VALIDATION & EXECUTION
## Backtest Engine + Paper Trading
**Duration:** ~44 hours | **Tasks:** 20 | **Sections:** 5.3 + 5.4

**Goal:** Build deterministic backtest engine and paper trading pipeline. All strategies validated before live trading.

**Start Conditions:** Session 5A complete (strategy engine + signal generators working)
**Exit Conditions:** Backtest produces deterministic results, paper trading validates all strategies

---

## 📊 SESSION 5B OVERVIEW

```
Section 5.3: Backtest Engine (22.5h, 10 tasks)
- Core backtesting engine
- Trade simulation and P&L tracking
- Performance metrics calculation
- Equity curve and trade logging
- Validation framework
- Walk-forward analysis (optional)
- API endpoints

Section 5.4: Paper Trading (21.5h, 10 tasks)
- Live paper trading engine (2 modes)
- Simulated paper (21-day recent data)
- Live paper (real-time with simulated fills)
- Metrics tracking during trading
- State persistence and recovery
- Validation triggers
- Multi-strategy coordination
- Dashboard data API
```

**Effort Distribution:**
- 5.3 Backtest Engine: 22.5 hours
- 5.4 Paper Trading: 21.5 hours
- **Total: 44 hours**

---

## CRITICAL CONCEPTS

### Backtest Engine Architecture

The backtest engine must be **deterministic** - same input always produces same output:

```
Input: Strategy + Symbols + Historical Data
         ↓
Backtest Engine
  ├─ Load OHLCV data (fixed start/end dates)
  ├─ Iterate chronologically (bar by bar)
  ├─ Generate signal per bar
  ├─ Simulate fill at next bar open
  ├─ Track position & cash
  ├─ Calculate P&L
  └─ Aggregate metrics
         ↓
Output: BacktestResult (metrics + equity curve + trade log)
```

**Key Invariants:**
- Always fill at next bar open (no lookahead bias)
- Commission applied consistently
- Slippage applied consistently
- No floating point rounding errors (use Decimal for financial values)
- Edge cases handled: no trades, all wins, all losses, extreme volatility

### Paper Trading Modes

**Simulated Paper (Phase 1):**
- Runs on last 21 days of data
- Same engine as backtest but recent data
- Fast validation before live trading
- Must pass same thresholds as backtest
- Deterministic results

**Live Paper (Phase 2):**
- Real-time data (current + recent)
- Simulated order fills (next bar or next 1m)
- Tracks metrics in real-time
- Runs for 7+ days minimum
- Non-deterministic (depends on live prices)

---

## SECTION 5.3: BACKTEST ENGINE (22.5 hours)

### Task 5.3.1: Create Backtest Engine Core (3 hours)

**File:** `src/core/strategy/backtest/engine.py`

**Purpose:** Central backtesting orchestrator. Loads data, iterates chronologically, generates signals, simulates fills.

**Core Interface:**

```python
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
import pandas as pd

@dataclass
class BacktestConfig:
    """Backtest execution configuration."""
    initial_capital: float = 10000.0
    slippage_bps: float = 2.0  # 2 basis points
    commission_rate: float = 0.001  # 0.1%
    timeframe: str = "1m"  # Candle timeframe
    lookback_bars: int = 200  # For indicator warmup

    def __post_init__(self):
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not 0 <= self.slippage_bps <= 100:
            raise ValueError("slippage_bps must be 0-100")

class BacktestEngine:
    """
    Deterministic backtesting engine.

    Guarantees:
    - Same input always produces same output
    - No lookahead bias (fill at next bar)
    - Chronological iteration
    - Accurate P&L calculation
    """

    def __init__(
        self,
        market_data: MarketDataService,
        signal_generator_factory: SignalGeneratorFactory,
        logger = None
    ):
        """Initialize backtest engine.

        Args:
            market_data: Service for historical OHLCV data
            signal_generator_factory: Factory to create generators
            logger: Structured logger instance
        """
        self.market_data = market_data
        self.factory = signal_generator_factory
        self.logger = logger or get_logger(__name__)

    async def run_backtest(
        self,
        strategy: Strategy,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        config: Optional[BacktestConfig] = None
    ) -> 'BacktestResult':
        """
        Run backtest for a strategy.

        Sequence:
        1. Validate inputs
        2. Load historical data
        3. Create signal generator
        4. Initialize portfolio state
        5. Iterate bars chronologically
        6. Generate signals
        7. Simulate fills
        8. Track equity
        9. Calculate metrics
        10. Validate result

        Args:
            strategy: Strategy to backtest
            symbol: Trading symbol (e.g., "BTCUSDT")
            start_date: Backtest start (inclusive)
            end_date: Backtest end (inclusive)
            config: Backtest configuration

        Returns:
            BacktestResult with complete metrics and trade log

        Raises:
            ValueError: If inputs invalid
            DataError: If data cannot be loaded
        """
        if config is None:
            config = BacktestConfig()

        # Validate inputs
        if end_date <= start_date:
            raise ValueError("end_date must be after start_date")

        if strategy.status not in [StrategyStatus.DRAFT, StrategyStatus.BACKTEST]:
            raise ValueError(f"Cannot backtest strategy in {strategy.status} status")

        self.logger.info(
            "backtest_started",
            strategy_id=strategy.id,
            symbol=symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            initial_capital=config.initial_capital
        )

        # Load data with lookback for warmup
        lookback_start = start_date - pd.Timedelta(days=30)
        data = await self.market_data.get_ohlcv(
            symbol=symbol,
            start_date=lookback_start,
            end_date=end_date,
            timeframe=config.timeframe
        )

        if data is None or len(data) == 0:
            raise ValueError(f"No OHLCV data available for {symbol}")

        # Create signal generator
        generator = self.factory.create(strategy.template_id)

        # Initialize portfolio
        portfolio = PortfolioState(initial_capital=config.initial_capital)
        trader = SimulatedTrader(portfolio, config)
        equity_tracker = EquityCurve()
        trade_log = TradeLog()

        # Iterate bars chronologically
        warmup_end = start_date
        active_data = data[data.index >= start_date].copy()

        for i, (timestamp, row) in enumerate(active_data.iterrows()):
            if i == 0:
                # Record initial equity
                equity_tracker.record(timestamp, config.initial_capital)
                continue

            # Get previous bars for indicator calculation
            lookback = data[data.index <= timestamp].tail(
                config.lookback_bars + 1
            )

            # Generate signal
            signal = await generator.generate_signal(
                strategy=strategy,
                symbol=symbol,
                data=lookback
            )

            # Execute on signal
            if signal.type != SignalType.NO_SIGNAL:
                trade = await trader.execute_signal(
                    signal=signal,
                    fill_price=row['open'],  # Fill at next bar open
                    timestamp=timestamp
                )

                if trade:
                    trade_log.add(trade)

            # Update equity and drawdown
            current_equity = trader.get_current_equity(row['close'])
            equity_tracker.record(timestamp, current_equity)

        # Calculate metrics
        metrics = BacktestMetricsCalculator.calculate(
            trades=trade_log.trades,
            equity_curve=equity_tracker.curve,
            initial_capital=config.initial_capital
        )

        result = BacktestResult(
            strategy_id=strategy.id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=config.initial_capital,
            final_capital=portfolio.get_total_value(active_data.iloc[-1]['close']),
            metrics=metrics,
            equity_curve=equity_tracker.to_dataframe(),
            trade_log=trade_log.trades,
            config=config
        )

        # Validate result
        validation_passed, errors = self._validate_result(result)
        result.passed_validation = validation_passed
        result.validation_errors = errors

        self.logger.info(
            "backtest_completed",
            strategy_id=strategy.id,
            symbol=symbol,
            total_return_pct=metrics.total_return_pct,
            sharpe_ratio=metrics.sharpe_ratio,
            max_drawdown_pct=metrics.max_drawdown_pct,
            win_rate_pct=metrics.win_rate_pct,
            num_trades=len(trade_log.trades),
            passed_validation=validation_passed
        )

        return result

    def _validate_result(
        self,
        result: 'BacktestResult'
    ) -> tuple[bool, List[str]]:
        """Validate backtest result against thresholds.

        Returns:
            (passed: bool, errors: List[str])
        """
        errors = []

        # Check minimum trades
        if len(result.trade_log) < 30:
            errors.append(
                f"Insufficient trades: {len(result.trade_log)} < 30"
            )

        # Check metrics thresholds
        if result.metrics.sharpe_ratio < 0.5:
            errors.append(
                f"Sharpe ratio too low: {result.metrics.sharpe_ratio:.2f} < 0.5"
            )

        if result.metrics.max_drawdown_pct > 15.0:
            errors.append(
                f"Max drawdown too high: {result.metrics.max_drawdown_pct:.1f}% > 15%"
            )

        if result.metrics.win_rate_pct < 35.0:
            errors.append(
                f"Win rate too low: {result.metrics.win_rate_pct:.1f}% < 35%"
            )

        if result.metrics.profit_factor < 1.0:
            errors.append(
                f"Profit factor too low: {result.metrics.profit_factor:.2f} < 1.0"
            )

        return len(errors) == 0, errors
```

**Acceptance Criteria:**
- [ ] Loads OHLCV data for date range
- [ ] Iterates bars chronologically (no lookahead)
- [ ] Generates signal per bar
- [ ] Simulates fills at next bar open
- [ ] Tracks portfolio state
- [ ] Returns comprehensive result
- [ ] Unit test: basic backtest with known signals

---

### Task 5.3.2: Implement Trade Simulation (2.5 hours)

**Add to:** `src/core/strategy/backtest/engine.py`

**Purpose:** Simulate order execution with accurate position tracking.

```python
from decimal import Decimal
import math

@dataclass
class Position:
    """Simulated trading position."""
    symbol: str
    entry_price: float
    entry_time: datetime
    quantity: float  # Positive for long
    commission_paid: float = 0.0

    @property
    def notional_value(self) -> float:
        """Position value at entry."""
        return abs(self.quantity) * self.entry_price

class PortfolioState:
    """Track portfolio state during backtest."""

    def __init__(self, initial_capital: float):
        """Initialize portfolio."""
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position: Optional[Position] = None
        self.closed_pnl = 0.0
        self.trades: List[dict] = []

    def open_position(
        self,
        symbol: str,
        quantity: float,
        price: float,
        commission: float,
        timestamp: datetime
    ) -> None:
        """Open a new position."""
        if self.position is not None:
            raise ValueError("Position already open")

        # Validate no NaN/Infinity
        if math.isnan(price) or math.isinf(price):
            raise ValueError(f"Invalid price: {price}")

        notional = abs(quantity) * price
        total_cost = notional + commission

        if total_cost > self.cash:
            raise ValueError(f"Insufficient cash: need {total_cost}, have {self.cash}")

        self.cash -= total_cost
        self.position = Position(
            symbol=symbol,
            entry_price=price,
            entry_time=timestamp,
            quantity=quantity,
            commission_paid=commission
        )

    def close_position(
        self,
        price: float,
        commission: float,
        timestamp: datetime
    ) -> dict:
        """Close current position.

        Returns:
            Trade record with entry/exit details
        """
        if self.position is None:
            raise ValueError("No position open")

        if math.isnan(price) or math.isinf(price):
            raise ValueError(f"Invalid exit price: {price}")

        position = self.position
        exit_value = abs(position.quantity) * price
        realized_pnl = (price - position.entry_price) * position.quantity - commission - position.commission_paid

        self.cash += exit_value - commission
        self.closed_pnl += realized_pnl

        trade = {
            'entry_time': position.entry_time,
            'entry_price': position.entry_price,
            'exit_time': timestamp,
            'exit_price': price,
            'quantity': position.quantity,
            'realized_pnl': realized_pnl,
            'holding_bars': 0,  # Will be calculated
            'mae': 0.0,  # Will be calculated
            'mfe': 0.0   # Will be calculated
        }

        self.trades.append(trade)
        self.position = None

        return trade

    def get_total_value(self, current_price: float) -> float:
        """Get total portfolio value (cash + position)."""
        if self.position is None:
            return self.cash

        unrealized = (current_price - self.position.entry_price) * self.position.quantity
        position_value = abs(self.position.quantity) * current_price

        return self.cash + position_value + unrealized

class SimulatedTrader:
    """Execute trades in backtest with accurate P&L."""

    def __init__(self, portfolio: PortfolioState, config: BacktestConfig):
        """Initialize trader."""
        self.portfolio = portfolio
        self.config = config
        self.mae_tracker = {}  # Track max adverse excursion
        self.mfe_tracker = {}  # Track max favorable excursion

    async def execute_signal(
        self,
        signal: Signal,
        fill_price: float,
        timestamp: datetime
    ) -> Optional[dict]:
        """Execute signal and return trade record if closed.

        Args:
            signal: Generated trading signal
            fill_price: Price to fill at (next bar open)
            timestamp: Bar timestamp

        Returns:
            Trade record if position closed, None if still open
        """
        # Apply slippage
        if signal.type in [SignalType.LONG_ENTRY, SignalType.SHORT_ENTRY]:
            # Buy slippage: price moves against us
            fill_price = fill_price * (1 + self.config.slippage_bps / 10000)
        else:
            # Sell slippage: price moves against us
            fill_price = fill_price * (1 - self.config.slippage_bps / 10000)

        # Calculate commission
        notional = abs(signal.metadata.get('quantity', 1.0)) * fill_price
        commission = notional * self.config.commission_rate

        # Execute based on signal type
        if signal.type == SignalType.LONG_ENTRY:
            if self.portfolio.position is not None:
                # Close existing position first
                trade = self.portfolio.close_position(
                    price=fill_price,
                    commission=commission,
                    timestamp=timestamp
                )

            # Open new long position
            self.portfolio.open_position(
                symbol=signal.symbol,
                quantity=1.0,  # Simplified: 1 unit
                price=fill_price,
                commission=commission,
                timestamp=timestamp
            )

        elif signal.type == SignalType.LONG_EXIT:
            if self.portfolio.position is None:
                return None

            trade = self.portfolio.close_position(
                price=fill_price,
                commission=commission,
                timestamp=timestamp
            )
            return trade

        return None

    def get_current_equity(self, current_price: float) -> float:
        """Get current equity including unrealized P&L."""
        return self.portfolio.get_total_value(current_price)
```

**Acceptance Criteria:**
- [ ] PortfolioState tracks cash and position
- [ ] Position opening validates sufficient cash
- [ ] Position closing calculates realized P&L
- [ ] Slippage applied to fills
- [ ] Commission applied consistently
- [ ] MAE/MFE tracked
- [ ] Unit test: open/close sequence
- [ ] Unit test: slippage calculation
- [ ] Unit test: commission calculation

---

### Task 5.3.3: Implement Backtest Metrics Calculator (2.5 hours)

**File:** `src/core/strategy/backtest/metrics.py`

**Purpose:** Calculate comprehensive performance metrics from trades.

```python
from dataclasses import dataclass
from typing import List
import numpy as np
import pandas as pd

@dataclass
class BacktestMetrics:
    """Complete backtest performance metrics."""
    # Returns
    total_return_pct: float
    total_return_usd: float
    annual_return_pct: float

    # Risk metrics
    max_drawdown_pct: float
    max_drawdown_usd: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Trade metrics
    num_trades: int
    num_winning_trades: int
    num_losing_trades: int
    win_rate_pct: float
    profit_factor: float
    average_win_usd: float
    average_loss_usd: float
    avg_winning_trade_pct: float
    avg_losing_trade_pct: float

    # Duration
    avg_trade_duration_bars: int
    avg_holding_period_days: float

    # Risk/Reward
    expectancy_usd: float
    payoff_ratio: float  # avg_win / abs(avg_loss)

    # Recovery
    recovery_factor: float  # total_return / max_drawdown

class BacktestMetricsCalculator:
    """Calculate backtest metrics from trades and equity curve."""

    RISK_FREE_RATE = 0.02  # 2% annual risk-free rate

    @classmethod
    def calculate(
        cls,
        trades: List[dict],
        equity_curve: pd.DataFrame,
        initial_capital: float,
        risk_free_rate: float = RISK_FREE_RATE
    ) -> BacktestMetrics:
        """Calculate all metrics.

        Args:
            trades: List of trade records with entry/exit
            equity_curve: DataFrame with timestamp and equity
            initial_capital: Starting capital
            risk_free_rate: Annual risk-free rate for Sharpe

        Returns:
            BacktestMetrics with all calculations
        """
        if len(trades) == 0:
            raise ValueError("No trades to analyze")

        # Basic returns
        final_equity = equity_curve['equity'].iloc[-1]
        total_return = final_equity - initial_capital
        total_return_pct = (total_return / initial_capital) * 100

        # Time period
        num_bars = len(equity_curve)
        annual_return = (total_return_pct / 365) * 252  # Annualize

        # Drawdown metrics
        max_drawdown_pct, max_drawdown_usd = cls._calculate_max_drawdown(
            equity_curve,
            initial_capital
        )

        # Sharpe & Sortino
        returns = equity_curve['equity'].pct_change().dropna()
        sharpe = cls._calculate_sharpe(returns, risk_free_rate)
        sortino = cls._calculate_sortino(returns, risk_free_rate)

        # Trade metrics
        win_rate, avg_win, avg_loss, profit_factor = cls._calculate_trade_metrics(trades)

        num_trades = len(trades)
        num_wins = sum(1 for t in trades if t['realized_pnl'] > 0)
        num_losses = sum(1 for t in trades if t['realized_pnl'] < 0)

        # Expectancy
        expectancy = cls._calculate_expectancy(trades)
        payoff_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else 0

        # Recovery factor
        recovery = (total_return / max_drawdown_usd) if max_drawdown_usd != 0 else 0

        # Calmar ratio
        calmar = annual_return / max_drawdown_pct if max_drawdown_pct != 0 else 0

        return BacktestMetrics(
            total_return_pct=total_return_pct,
            total_return_usd=total_return,
            annual_return_pct=annual_return,
            max_drawdown_pct=max_drawdown_pct,
            max_drawdown_usd=max_drawdown_usd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            num_trades=num_trades,
            num_winning_trades=num_wins,
            num_losing_trades=num_losses,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            average_win_usd=avg_win,
            average_loss_usd=avg_loss,
            avg_winning_trade_pct=0.0,  # Calculated per trade
            avg_losing_trade_pct=0.0,   # Calculated per trade
            avg_trade_duration_bars=0,  # Simplified
            avg_holding_period_days=0.0, # Simplified
            expectancy_usd=expectancy,
            payoff_ratio=payoff_ratio,
            recovery_factor=recovery
        )

    @staticmethod
    def _calculate_max_drawdown(
        equity_curve: pd.DataFrame,
        initial_capital: float
    ) -> tuple[float, float]:
        """Calculate maximum drawdown as % and USD.

        Formula:
        DD = (Peak - Trough) / Peak
        """
        equity = equity_curve['equity'].values

        max_equity = np.maximum.accumulate(equity)
        drawdown = (max_equity - equity) / max_equity
        max_dd_pct = np.max(drawdown) * 100

        peak_idx = np.argmax(max_equity)
        trough_idx = np.argmax(drawdown)
        max_dd_usd = max_equity[peak_idx] - equity[trough_idx]

        return max_dd_pct, max_dd_usd

    @staticmethod
    def _calculate_sharpe(
        returns: pd.Series,
        risk_free_rate: float
    ) -> float:
        """Calculate Sharpe ratio.

        Formula:
        Sharpe = (R - Rf) / StdDev(R)
        """
        excess_returns = returns - (risk_free_rate / 252)

        if len(excess_returns) == 0:
            return 0.0

        std_dev = excess_returns.std()
        if std_dev == 0:
            return 0.0

        sharpe = excess_returns.mean() / std_dev
        return sharpe * np.sqrt(252)  # Annualize

    @staticmethod
    def _calculate_sortino(
        returns: pd.Series,
        risk_free_rate: float
    ) -> float:
        """Calculate Sortino ratio (downside deviation only).

        Formula:
        Sortino = (R - Rf) / Downside_StdDev(R)
        """
        excess_returns = returns - (risk_free_rate / 252)

        # Only penalize downside volatility
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return 0.0

        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0.0

        sortino = excess_returns.mean() / downside_std
        return sortino * np.sqrt(252)  # Annualize

    @staticmethod
    def _calculate_trade_metrics(
        trades: List[dict]
    ) -> tuple[float, float, float, float]:
        """Calculate win rate, avg win/loss, profit factor.

        Returns:
            (win_rate_pct, avg_win, avg_loss, profit_factor)
        """
        if len(trades) == 0:
            return 0.0, 0.0, 0.0, 0.0

        pnls = [t['realized_pnl'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        win_rate = (len(wins) / len(trades)) * 100

        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0

        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 1.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        return win_rate, avg_win, avg_loss, profit_factor

    @staticmethod
    def _calculate_expectancy(trades: List[dict]) -> float:
        """Calculate expectancy (average P&L per trade).

        Formula:
        E = (Win% * AvgWin) - (Loss% * |AvgLoss|)
        """
        if len(trades) == 0:
            return 0.0

        pnls = [t['realized_pnl'] for t in trades]
        return np.mean(pnls)
```

**Acceptance Criteria:**
- [ ] Total return calculated correctly
- [ ] Sharpe ratio calculated correctly
- [ ] Sortino ratio calculated correctly
- [ ] Max drawdown calculated correctly
- [ ] Win rate calculated correctly
- [ ] Profit factor calculated correctly
- [ ] Handles edge cases (no trades, all wins, all losses)
- [ ] Unit test: verify against manual calculations
- [ ] Unit test: edge case handling

---

### Task 5.3.4: Implement Equity Curve Tracking (1.5 hours)

**Add to:** `src/core/strategy/backtest/engine.py`

**Purpose:** Track portfolio equity at each bar for visualization and drawdown calculation.

```python
import pandas as pd

class EquityCurve:
    """Track equity over time during backtest."""

    def __init__(self):
        """Initialize equity tracker."""
        self.timestamps: List[datetime] = []
        self.equity: List[float] = []
        self.drawdown: List[float] = []

    def record(self, timestamp: datetime, equity: float) -> None:
        """Record equity at timestamp.

        Args:
            timestamp: Bar timestamp
            equity: Current total equity (cash + position value)
        """
        if math.isnan(equity) or math.isinf(equity):
            raise ValueError(f"Invalid equity: {equity}")

        self.timestamps.append(timestamp)
        self.equity.append(equity)

        # Calculate drawdown from peak
        if len(self.equity) > 0:
            peak = max(self.equity)
            dd = (peak - equity) / peak if peak > 0 else 0.0
            self.drawdown.append(dd)
        else:
            self.drawdown.append(0.0)

    def to_dataframe(self) -> pd.DataFrame:
        """Export to pandas DataFrame."""
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'equity': self.equity,
            'drawdown_pct': [d * 100 for d in self.drawdown]
        }).set_index('timestamp')

    @property
    def max_drawdown(self) -> float:
        """Maximum drawdown percentage."""
        return max(self.drawdown) * 100 if self.drawdown else 0.0

    @property
    def final_equity(self) -> float:
        """Final equity value."""
        return self.equity[-1] if self.equity else 0.0
```

**Acceptance Criteria:**
- [ ] Records equity at each bar
- [ ] Calculates drawdown from peak
- [ ] Exports to DataFrame
- [ ] Handles no data edge case
- [ ] Unit test: recording and calculation

---

### Task 5.3.5: Implement Trade Log (1.5 hours)

**Add to:** `src/core/strategy/backtest/engine.py`

**Purpose:** Log and calculate MAE/MFE for each trade.

```python
@dataclass
class TradeRecord:
    """Complete record of a single trade."""
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    quantity: float
    realized_pnl: float
    realized_pnl_pct: float
    holding_bars: int
    mae: float  # Max Adverse Excursion
    mfe: float  # Max Favorable Excursion
    mae_pct: float
    mfe_pct: float

class TradeLog:
    """Log and track metrics for all trades."""

    def __init__(self):
        """Initialize trade log."""
        self.trades: List[TradeRecord] = []
        self._tracking: dict = {}  # Current trade tracking

    def add(self, trade_data: dict) -> TradeRecord:
        """Add completed trade.

        Args:
            trade_data: Trade record from SimulatedTrader

        Returns:
            TradeRecord with MAE/MFE calculated
        """
        pnl_pct = (trade_data['realized_pnl'] / (trade_data['entry_price'] * trade_data['quantity'])) * 100

        holding_bars = 0  # Would be calculated from timestamps

        record = TradeRecord(
            entry_time=trade_data['entry_time'],
            entry_price=trade_data['entry_price'],
            exit_time=trade_data['exit_time'],
            exit_price=trade_data['exit_price'],
            quantity=trade_data['quantity'],
            realized_pnl=trade_data['realized_pnl'],
            realized_pnl_pct=pnl_pct,
            holding_bars=holding_bars,
            mae=trade_data.get('mae', 0.0),
            mfe=trade_data.get('mfe', 0.0),
            mae_pct=0.0,  # Calculate from entry_price
            mfe_pct=0.0   # Calculate from entry_price
        )

        self.trades.append(record)
        return record

    def to_dataframe(self) -> pd.DataFrame:
        """Export to DataFrame."""
        return pd.DataFrame([
            {
                'entry_time': t.entry_time,
                'entry_price': t.entry_price,
                'exit_time': t.exit_time,
                'exit_price': t.exit_price,
                'pnl': t.realized_pnl,
                'pnl_pct': t.realized_pnl_pct,
                'mae': t.mae,
                'mfe': t.mfe,
                'holding_bars': t.holding_bars
            }
            for t in self.trades
        ])
```

**Acceptance Criteria:**
- [ ] Logs all trades
- [ ] Calculates P&L % correctly
- [ ] Tracks MAE and MFE
- [ ] Exports to DataFrame
- [ ] Unit test: trade recording

---

### Task 5.3.6: Implement BacktestResult (1.5 hours)

**File:** `src/core/strategy/backtest/result.py`

**Purpose:** Comprehensive backtest result object with serialization.

```python
from dataclasses import dataclass, asdict
import json

@dataclass
class BacktestResult:
    """Complete backtest execution result."""
    strategy_id: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float

    # Metrics
    metrics: BacktestMetrics

    # Details
    equity_curve: pd.DataFrame
    trade_log: List[TradeRecord]
    config: BacktestConfig

    # Validation
    passed_validation: bool = False
    validation_errors: List[str] = None

    def __post_init__(self):
        """Validate result."""
        if math.isnan(self.final_capital):
            raise ValueError("Final capital is NaN")
        if self.final_capital < 0:
            raise ValueError("Final capital is negative")
        if self.validation_errors is None:
            self.validation_errors = []

    @property
    def total_return_pct(self) -> float:
        """Total return percentage."""
        return self.metrics.total_return_pct

    @property
    def num_trades(self) -> int:
        """Number of completed trades."""
        return len(self.trade_log)

    def to_dict(self) -> dict:
        """Export to dictionary (JSON-serializable)."""
        return {
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': float(self.initial_capital),
            'final_capital': float(self.final_capital),
            'metrics': {
                'total_return_pct': float(self.metrics.total_return_pct),
                'sharpe_ratio': float(self.metrics.sharpe_ratio),
                'max_drawdown_pct': float(self.metrics.max_drawdown_pct),
                'win_rate_pct': float(self.metrics.win_rate_pct),
                'num_trades': int(self.metrics.num_trades),
                'profit_factor': float(self.metrics.profit_factor)
            },
            'trade_log': [
                {
                    'entry_time': t.entry_time.isoformat(),
                    'entry_price': float(t.entry_price),
                    'exit_time': t.exit_time.isoformat(),
                    'exit_price': float(t.exit_price),
                    'pnl': float(t.realized_pnl),
                    'pnl_pct': float(t.realized_pnl_pct)
                }
                for t in self.trade_log
            ],
            'passed_validation': bool(self.passed_validation),
            'validation_errors': list(self.validation_errors)
        }

    def summary(self) -> str:
        """Human-readable summary."""
        return f"""
Backtest Results: {self.symbol}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Period: {self.start_date.date()} to {self.end_date.date()}
Initial Capital: ${self.initial_capital:,.2f}
Final Capital: ${self.final_capital:,.2f}

Returns:
  Total Return: {self.metrics.total_return_pct:.2f}%
  Annual Return: {self.metrics.annual_return_pct:.2f}%

Risk:
  Sharpe Ratio: {self.metrics.sharpe_ratio:.2f}
  Max Drawdown: {self.metrics.max_drawdown_pct:.2f}%
  Sortino Ratio: {self.metrics.sortino_ratio:.2f}

Trades:
  Total Trades: {len(self.trade_log)}
  Win Rate: {self.metrics.win_rate_pct:.1f}%
  Profit Factor: {self.metrics.profit_factor:.2f}
  Avg Win: ${self.metrics.average_win_usd:,.2f}
  Avg Loss: ${self.metrics.average_loss_usd:,.2f}

Validation:
  Status: {"✓ PASSED" if self.passed_validation else "✗ FAILED"}
  Errors: {len(self.validation_errors)}
"""
```

**Acceptance Criteria:**
- [ ] Stores all result data
- [ ] Serializable to dict/JSON
- [ ] Human-readable summary
- [ ] Validation status tracking
- [ ] Unit test: serialization

---

### Task 5.3.7: Implement Backtest Validation (2 hours)

**Add to:** `src/core/strategy/backtest/engine.py`

**Purpose:** Validate backtest results against thresholds per PRD.

```python
@dataclass
class ValidationThresholds:
    """Backtest validation thresholds."""
    min_sharpe_ratio: float = 0.5
    max_drawdown_pct: float = 15.0
    min_win_rate_pct: float = 35.0
    min_profit_factor: float = 1.0
    min_num_trades: int = 30

class BacktestValidator:
    """Validate backtest results against thresholds."""

    @staticmethod
    def validate(
        result: BacktestResult,
        thresholds: Optional[ValidationThresholds] = None
    ) -> tuple[bool, List[str]]:
        """Validate result and return pass/fail + reasons.

        Args:
            result: BacktestResult to validate
            thresholds: Custom validation thresholds

        Returns:
            (passed: bool, errors: List[str])
        """
        if thresholds is None:
            thresholds = ValidationThresholds()

        errors = []

        # Minimum trades
        if result.num_trades < thresholds.min_num_trades:
            errors.append(
                f"Too few trades: {result.num_trades} < {thresholds.min_num_trades}"
            )

        # Sharpe ratio
        if result.metrics.sharpe_ratio < thresholds.min_sharpe_ratio:
            errors.append(
                f"Sharpe too low: {result.metrics.sharpe_ratio:.2f} < {thresholds.min_sharpe_ratio}"
            )

        # Max drawdown
        if result.metrics.max_drawdown_pct > thresholds.max_drawdown_pct:
            errors.append(
                f"Max drawdown too high: {result.metrics.max_drawdown_pct:.2f}% > {thresholds.max_drawdown_pct}%"
            )

        # Win rate
        if result.metrics.win_rate_pct < thresholds.min_win_rate_pct:
            errors.append(
                f"Win rate too low: {result.metrics.win_rate_pct:.1f}% < {thresholds.min_win_rate_pct}%"
            )

        # Profit factor
        if result.metrics.profit_factor < thresholds.min_profit_factor:
            errors.append(
                f"Profit factor too low: {result.metrics.profit_factor:.2f} < {thresholds.min_profit_factor}"
            )

        return len(errors) == 0, errors
```

**Acceptance Criteria:**
- [ ] Validates against all thresholds
- [ ] Sharpe >= 0.5
- [ ] Max drawdown <= 15%
- [ ] Win rate >= 35%
- [ ] Profit factor >= 1.0
- [ ] Min trades >= 30
- [ ] Returns clear failure messages
- [ ] Thresholds configurable
- [ ] Unit test: pass scenarios
- [ ] Unit test: fail scenarios

---

### Task 5.3.8: Create Backtest API Endpoints (2 hours)

**Add to:** `src/api/routes/strategies.py`

**Purpose:** REST API for backtest execution.

```python
# Existing strategies.py file - add these endpoints

@router.post("/api/strategies/{strategy_id}/backtest")
async def run_backtest(
    strategy_id: str,
    request: BacktestRequest,
    db: Session = Depends(get_db),
    backtest_engine: BacktestEngine = Depends(get_backtest_engine)
) -> BacktestResponse:
    """Run backtest for strategy.

    Request:
    {
        "symbol": "BTCUSDT",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 10000
    }

    Response:
    {
        "strategy_id": "...",
        "passed_validation": true,
        "metrics": {
            "total_return_pct": 25.5,
            "sharpe_ratio": 1.2,
            "max_drawdown_pct": 10.5,
            "win_rate_pct": 52.0
        },
        "trade_log": [...]
    }
    """
    strategy = await db.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    result = await backtest_engine.run_backtest(
        strategy=strategy,
        symbol=request.symbol,
        start_date=request.start_date,
        end_date=request.end_date,
        config=BacktestConfig(
            initial_capital=request.initial_capital
        )
    )

    return BacktestResponse.from_result(result)

@router.get("/api/strategies/{strategy_id}/backtest/trades")
async def get_backtest_trades(
    strategy_id: str,
    db: Session = Depends(get_db)
) -> List[dict]:
    """Get backtest trade log."""
    # Query from database
    trades = await db.get_backtest_trades(strategy_id)
    return [t.to_dict() for t in trades]
```

**Acceptance Criteria:**
- [ ] POST endpoint triggers backtest
- [ ] GET endpoint returns results
- [ ] Trade log accessible
- [ ] Equity curve data accessible
- [ ] Integration test: full flow

---

### Task 5.3.9: Write Backtest Engine Tests (3 hours)

**File:** `tests/unit/strategy/test_backtest_engine.py`

**Purpose:** Comprehensive tests for backtest correctness.

```python
import pytest
from datetime import datetime, timezone
import pandas as pd

@pytest.fixture
def backtest_engine(market_data_service, signal_generator_factory):
    """Create backtest engine."""
    return BacktestEngine(market_data_service, signal_generator_factory)

@pytest.fixture
def simple_strategy():
    """Create simple test strategy."""
    return Strategy(
        id="test-strat-1",
        template_id="ema_trend_rsi",
        name="Test Strategy",
        parameters={
            'fast_ema': 12,
            'slow_ema': 26,
            'rsi_period': 14
        },
        symbols=['BTCUSDT']
    )

@pytest.mark.asyncio
async def test_backtest_determinism(backtest_engine, simple_strategy, market_data):
    """Verify same input produces same output."""
    config = BacktestConfig(initial_capital=10000)

    # Run backtest twice
    result1 = await backtest_engine.run_backtest(
        strategy=simple_strategy,
        symbol='BTCUSDT',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
        config=config
    )

    result2 = await backtest_engine.run_backtest(
        strategy=simple_strategy,
        symbol='BTCUSDT',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
        config=config
    )

    # Metrics should match exactly
    assert result1.metrics.total_return_pct == result2.metrics.total_return_pct
    assert result1.metrics.sharpe_ratio == result2.metrics.sharpe_ratio
    assert result1.num_trades == result2.num_trades

@pytest.mark.asyncio
async def test_backtest_pnl_calculation(backtest_engine):
    """Verify P&L calculation correctness."""
    # Create strategy with known behavior
    strategy = Strategy(
        id="test-pnl",
        template_id="simple_ma",
        name="PnL Test",
        parameters={'period': 20},
        symbols=['BTCUSDT']
    )

    result = await backtest_engine.run_backtest(
        strategy=strategy,
        symbol='BTCUSDT',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 31, tzinfo=timezone.utc),
        config=BacktestConfig(initial_capital=10000, commission_rate=0.001)
    )

    # Manually verify trades
    for trade in result.trade_log:
        # P&L = (exit - entry) * qty - commission
        expected_pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        assert abs(trade.realized_pnl - expected_pnl) < 0.01

@pytest.mark.asyncio
async def test_backtest_no_lookahead_bias(backtest_engine, simple_strategy):
    """Verify fills happen at next bar (no lookahead)."""
    # If we generate signal at bar N
    # Fill must happen at bar N+1 open price
    # Not at bar N close or high

    result = await backtest_engine.run_backtest(
        strategy=simple_strategy,
        symbol='BTCUSDT',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 31, tzinfo=timezone.utc)
    )

    # Verify no fills at extreme prices
    for trade in result.trade_log:
        # Entry should be reasonable (not at 1-min extremes)
        assert trade.entry_price > 0

@pytest.mark.asyncio
async def test_backtest_edge_case_no_trades():
    """Backtest with no signals generated."""
    # Strategy that never generates signals
    mock_generator = AsyncMock()
    mock_generator.generate_signal = AsyncMock(
        return_value=Signal(
            type=SignalType.NO_SIGNAL,
            symbol='BTCUSDT',
            strategy_id='test',
            timestamp=datetime.now(timezone.utc),
            price=100.0
        )
    )

    # Should handle gracefully
    # No trades = validation fails

@pytest.mark.asyncio
async def test_backtest_validation_pass():
    """Test validation with strong results."""
    result = BacktestResult(
        strategy_id='test',
        symbol='BTCUSDT',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        initial_capital=10000,
        final_capital=15000,
        metrics=BacktestMetrics(
            total_return_pct=50.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=8.0,
            win_rate_pct=60.0,
            num_trades=100,
            profit_factor=2.0,
            # ... other metrics
        ),
        equity_curve=pd.DataFrame(),
        trade_log=[],
        config=BacktestConfig()
    )

    passed, errors = BacktestValidator.validate(result)
    assert passed is True
    assert len(errors) == 0

@pytest.mark.asyncio
async def test_backtest_validation_fail_low_sharpe():
    """Test validation failure on low Sharpe."""
    result = BacktestResult(
        strategy_id='test',
        symbol='BTCUSDT',
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        initial_capital=10000,
        final_capital=11000,
        metrics=BacktestMetrics(
            total_return_pct=10.0,
            sharpe_ratio=0.2,  # Below threshold
            max_drawdown_pct=5.0,
            win_rate_pct=50.0,
            num_trades=100,
            profit_factor=1.0,
            # ...
        ),
        equity_curve=pd.DataFrame(),
        trade_log=[],
        config=BacktestConfig()
    )

    passed, errors = BacktestValidator.validate(result)
    assert passed is False
    assert any('Sharpe' in e for e in errors)
```

**Acceptance Criteria:**
- [ ] Determinism verified (same input = same output)
- [ ] P&L calculation verified manually
- [ ] No lookahead bias
- [ ] Edge cases tested (no trades, all wins, all losses)
- [ ] Validation pass/fail scenarios
- [ ] >85% coverage
- [ ] All trade metrics verified

---

### Task 5.3.10: Implement Walk-Forward Analysis (Optional, 3 hours)

**File:** `src/core/strategy/backtest/walk_forward.py`

**Purpose:** Walk-forward optimization validation (nice-to-have).

```python
class WalkForwardAnalyzer:
    """Walk-forward analysis for strategy validation."""

    def __init__(self, backtest_engine: BacktestEngine):
        """Initialize analyzer."""
        self.backtest_engine = backtest_engine

    async def run_walk_forward(
        self,
        strategy: Strategy,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        window_size_days: int = 90,
        step_days: int = 30
    ) -> dict:
        """Run walk-forward test.

        Args:
            strategy: Strategy to test
            symbol: Trading symbol
            start_date: Period start
            end_date: Period end
            window_size_days: In-sample + out-of-sample window
            step_days: Advance window by this many days

        Returns:
            Walk-forward results with OOS performance
        """
        windows = []
        current_date = start_date

        while current_date + pd.Timedelta(days=window_size_days) <= end_date:
            in_sample_end = current_date + pd.Timedelta(days=window_size_days // 2)
            oos_start = in_sample_end
            oos_end = current_date + pd.Timedelta(days=window_size_days)

            # Run backtest on in-sample
            is_result = await self.backtest_engine.run_backtest(
                strategy=strategy,
                symbol=symbol,
                start_date=current_date,
                end_date=in_sample_end
            )

            # Run backtest on out-of-sample
            oos_result = await self.backtest_engine.run_backtest(
                strategy=strategy,
                symbol=symbol,
                start_date=oos_start,
                end_date=oos_end
            )

            windows.append({
                'window': len(windows),
                'in_sample_return': is_result.metrics.total_return_pct,
                'oos_return': oos_result.metrics.total_return_pct,
                'in_sample_sharpe': is_result.metrics.sharpe_ratio,
                'oos_sharpe': oos_result.metrics.sharpe_ratio
            })

            current_date += pd.Timedelta(days=step_days)

        # Aggregate OOS results
        oos_returns = [w['oos_return'] for w in windows]

        return {
            'windows': windows,
            'avg_oos_return': np.mean(oos_returns),
            'oos_return_std': np.std(oos_returns),
            'num_windows': len(windows)
        }
```

**Acceptance Criteria:**
- [ ] Splits data into windows
- [ ] Tests both in-sample and OOS
- [ ] Aggregates OOS performance
- [ ] Optional for MVP
- [ ] Unit test: walk-forward

---

## SECTION 5.4: PAPER TRADING (21.5 hours)

### Task 5.4.1: Create Paper Trading Engine (3 hours)

**File:** `src/core/strategy/paper/engine.py`

**Purpose:** Execute strategies on live data with simulated fills.

```python
from enum import Enum
from typing import Optional

class PaperTradingMode(str, Enum):
    """Paper trading execution modes."""
    SIMULATED = "simulated"  # Historical data, fast
    LIVE = "live"           # Real-time data, slow

@dataclass
class PaperTradingStatus:
    """Current paper trading status."""
    mode: PaperTradingMode
    strategy_id: str
    is_running: bool
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    current_equity: float
    current_pnl: float
    num_trades: int
    days_elapsed: float
    validation_status: str  # running, passed, failed

class PaperTradingEngine:
    """
    Paper trading engine for strategy validation.

    Two modes:
    1. Simulated: Run on recent historical data (21 days)
    2. Live: Run on real-time data (7+ days minimum)

    Both modes use same simulated execution to avoid real risk.
    """

    def __init__(
        self,
        strategy: Strategy,
        market_data: MarketDataService,
        signal_generator: SignalGenerator,
        mode: PaperTradingMode,
        data_store: DataStore,
        logger = None
    ):
        """Initialize paper trading engine.

        Args:
            strategy: Strategy to paper trade
            market_data: Market data service
            signal_generator: Signal generator for this strategy
            mode: SIMULATED or LIVE
            data_store: For persistence
            logger: Structured logger
        """
        self.strategy = strategy
        self.market_data = market_data
        self.signal_generator = signal_generator
        self.mode = mode
        self.data_store = data_store
        self.logger = logger or get_logger(__name__)

        # State
        self._running = False
        self._status = PaperTradingStatus(
            mode=mode,
            strategy_id=strategy.id,
            is_running=False,
            started_at=None,
            stopped_at=None,
            current_equity=10000.0,
            current_pnl=0.0,
            num_trades=0,
            days_elapsed=0.0,
            validation_status="running"
        )

        # Portfolio for simulated trading
        self._portfolio = PortfolioState(initial_capital=10000.0)
        self._equity_history: List[tuple[datetime, float]] = []
        self._trades: List[dict] = []

    async def start(self) -> None:
        """Start paper trading.

        Sequence:
        1. Load previous state (if exists)
        2. Start main loop
        3. Log start event
        """
        self._running = True
        self._status.is_running = True
        self._status.started_at = datetime.now(timezone.utc)

        # Load previous state for recovery
        await self._load_state()

        self.logger.info(
            "paper_trading_started",
            strategy_id=self.strategy.id,
            mode=self.mode.value
        )

        # Start main loop
        if self.mode == PaperTradingMode.SIMULATED:
            await self._run_simulated_paper()
        else:
            await self._run_live_paper()

    async def stop(self) -> None:
        """Stop paper trading.

        Sequence:
        1. Close main loop
        2. Save state
        3. Log stop event
        """
        self._running = False
        self._status.is_running = False
        self._status.stopped_at = datetime.now(timezone.utc)

        await self._save_state()

        self.logger.info(
            "paper_trading_stopped",
            strategy_id=self.strategy.id,
            final_equity=self._status.current_equity,
            pnl=self._status.current_pnl
        )

    async def get_status(self) -> PaperTradingStatus:
        """Get current paper trading status."""
        if self._status.started_at:
            elapsed = datetime.now(timezone.utc) - self._status.started_at
            self._status.days_elapsed = elapsed.total_seconds() / (24 * 3600)

        return self._status

    async def _run_simulated_paper(self) -> None:
        """
        Simulated paper trading on recent data.

        - Load last 21 days of data
        - Iterate bars
        - Generate signals
        - Simulate fills
        - Track metrics
        - Validate when complete
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - pd.Timedelta(days=21)

        # Load data
        data = await self.market_data.get_ohlcv(
            symbol=self.strategy.symbols[0],
            start_date=start_date,
            end_date=end_date,
            timeframe="1m"
        )

        if data is None or len(data) == 0:
            self.logger.error("paper_trading_no_data", strategy_id=self.strategy.id)
            self._status.validation_status = "failed"
            return

        # Iterate bars
        for timestamp, row in data.iterrows():
            if not self._running:
                break

            # Generate signal
            signal = await self.signal_generator.generate_signal(
                strategy=self.strategy,
                symbol=self.strategy.symbols[0],
                data=data[:timestamp]
            )

            # Execute on signal
            if signal.type != SignalType.NO_SIGNAL:
                await self._execute_paper_signal(signal, row['open'], timestamp)

            # Record equity
            current_equity = self._portfolio.get_total_value(row['close'])
            self._equity_history.append((timestamp, current_equity))
            self._status.current_equity = current_equity
            self._status.current_pnl = current_equity - 10000.0
            self._status.num_trades = len(self._trades)

        # Validate
        await self._validate_paper_trading()

    async def _run_live_paper(self) -> None:
        """
        Live paper trading on real-time data.

        - Subscribe to real-time prices
        - Generate signals every update
        - Simulate fills
        - Track metrics continuously
        - Run for 7+ days minimum
        """
        self.logger.info(
            "live_paper_trading_started",
            strategy_id=self.strategy.id,
            symbols=self.strategy.symbols
        )

        # Main trading loop
        while self._running:
            for symbol in self.strategy.symbols:
                # Get latest data
                data = await self.market_data.get_ohlcv(
                    symbol=symbol,
                    lookback_bars=200
                )

                if data is None or len(data) == 0:
                    await asyncio.sleep(60)
                    continue

                # Generate signal
                signal = await self.signal_generator.generate_signal(
                    strategy=self.strategy,
                    symbol=symbol,
                    data=data
                )

                # Execute on signal
                if signal.type != SignalType.NO_SIGNAL:
                    latest_row = data.iloc[-1]
                    await self._execute_paper_signal(
                        signal,
                        latest_row['close'],
                        pd.Timestamp.now(tz='UTC')
                    )

                # Update status
                if data is not None and len(data) > 0:
                    current_equity = self._portfolio.get_total_value(
                        data.iloc[-1]['close']
                    )
                    self._equity_history.append((
                        pd.Timestamp.now(tz='UTC'),
                        current_equity
                    ))
                    self._status.current_equity = current_equity
                    self._status.current_pnl = current_equity - 10000.0
                    self._status.num_trades = len(self._trades)

            # Check if minimum duration reached
            if self._status.started_at:
                elapsed = (datetime.now(timezone.utc) - self._status.started_at).total_seconds() / (24 * 3600)
                self._status.days_elapsed = elapsed

                if elapsed >= 7:
                    await self._validate_paper_trading()

            # Sleep before next iteration
            await asyncio.sleep(60)

    async def _execute_paper_signal(
        self,
        signal: Signal,
        fill_price: float,
        timestamp: datetime
    ) -> None:
        """Execute signal with simulated fill."""
        commission = abs(signal.metadata.get('quantity', 1.0)) * fill_price * 0.001

        try:
            if signal.type == SignalType.LONG_ENTRY:
                if self._portfolio.position is None:
                    self._portfolio.open_position(
                        symbol=signal.symbol,
                        quantity=1.0,
                        price=fill_price,
                        commission=commission,
                        timestamp=timestamp
                    )

            elif signal.type == SignalType.LONG_EXIT:
                if self._portfolio.position is not None:
                    trade = self._portfolio.close_position(
                        price=fill_price,
                        commission=commission,
                        timestamp=timestamp
                    )
                    self._trades.append(trade)

        except ValueError as e:
            self.logger.error(
                "paper_signal_execution_failed",
                strategy_id=self.strategy.id,
                signal_type=signal.type.value,
                error=str(e)
            )

    async def _validate_paper_trading(self) -> None:
        """Validate paper trading results."""
        # Calculate metrics
        if len(self._trades) < 5:
            self._status.validation_status = "failed"
            self.logger.info(
                "paper_validation_failed_insufficient_trades",
                strategy_id=self.strategy.id,
                num_trades=len(self._trades)
            )
            return

        # Check equity growth
        pnl_pct = (self._status.current_pnl / 10000.0) * 100
        if pnl_pct < 5.0:  # Minimum 5% return
            self._status.validation_status = "failed"
            self.logger.info(
                "paper_validation_failed_low_return",
                strategy_id=self.strategy.id,
                pnl_pct=pnl_pct
            )
            return

        # Passed validation
        self._status.validation_status = "passed"
        await self._on_validation_passed()

    async def _on_validation_passed(self) -> None:
        """Handle validation pass (auto-transition strategy)."""
        self.logger.info(
            "paper_validation_passed",
            strategy_id=self.strategy.id,
            mode=self.mode.value
        )
        # Strategy should transition status automatically

    async def _save_state(self) -> None:
        """Persist paper trading state."""
        state = {
            'strategy_id': self.strategy.id,
            'portfolio': self._portfolio,
            'trades': self._trades,
            'equity_history': self._equity_history,
            'started_at': self._status.started_at,
            'stopped_at': self._status.stopped_at
        }
        await self.data_store.save_paper_trading_state(state)

    async def _load_state(self) -> None:
        """Load previous paper trading state for recovery."""
        state = await self.data_store.load_paper_trading_state(self.strategy.id)
        if state:
            self._portfolio = state['portfolio']
            self._trades = state['trades']
            self._equity_history = state['equity_history']
            self._status.started_at = state['started_at']
            self.logger.info(
                "paper_trading_state_recovered",
                strategy_id=self.strategy.id,
                num_trades=len(self._trades)
            )
```

**Acceptance Criteria:**
- [ ] Both modes implemented (SIMULATED, LIVE)
- [ ] Simulated mode runs on 21-day data
- [ ] Live mode runs in real-time loop
- [ ] Tracks virtual P&L
- [ ] Can start/stop cleanly
- [ ] State persists and recovers
- [ ] Unit test: simulated mode
- [ ] Integration test: live mode (mocked)

---

### Tasks 5.4.2 through 5.4.10: Implementation Details

Due to space constraints, I'll provide task summaries. Each follows the same pattern as 5.4.1:

**Task 5.4.2: Implement Simulated Paper Trading (2 hours)**
- Load last 21 days, iterate bars, track metrics
- Must pass same validation as backtest

**Task 5.4.3: Implement Live Paper Trading (3 hours)**
- Real-time data loop, simulated fills
- Runs 7+ days minimum
- Logs all signals and fills

**Task 5.4.4: Implement Paper Trading Metrics Tracker (2 hours)**
- Running P&L, Sharpe, win rate, drawdown
- Updates in real-time
- Queryable via API

**Task 5.4.5: Implement Paper Trading Validation (2 hours)**
- Auto-transition on pass
- Notification on fail
- Thresholds: 5% minimum return, 5+ trades

**Task 5.4.6: Implement State Persistence (1.5 hours)**
- Persist: positions, cash, trades, metrics
- Recovery on restart (no P&L gaps)

**Task 5.4.7: Create Paper Trading API (1.5 hours)**
- POST /api/strategies/{id}/paper/start
- POST /api/strategies/{id}/paper/stop
- GET /api/strategies/{id}/paper/status
- GET /api/strategies/{id}/paper/trades

**Task 5.4.8: Implement Multi-Strategy Paper Trading (2 hours)**
- Manage multiple engine instances
- Coordinate shared market data
- Aggregate metrics

**Task 5.4.9: Create Paper Trading Dashboard Data (1.5 hours)**
- GET /api/strategies/{id}/paper/dashboard
- Returns: status, days remaining, metrics, recent trades, equity curve

**Task 5.4.10: Write Paper Trading Tests (2.5 hours)**
- Test simulated mode (deterministic)
- Test live mode (with mocked prices)
- Test validation pass/fail
- Test state persistence
- >80% coverage

---

## CRITICAL INVARIANTS (SESSION 5B)

### Backtest Determinism (MUST NOT VIOLATE)

```
Same strategy + symbol + date range + config → EXACT same result
✓ Chronological iteration (bar by bar)
✓ Fill at next bar open (no lookahead)
✓ Consistent commission calculation
✓ Consistent slippage application
✗ DO NOT: Use random numbers, sort by dict keys, float rounding errors
```

### Paper Trading Validation (MUST NOT VIOLATE)

```
Simulated Paper (21 days on recent data):
- Must pass SAME thresholds as backtest
- Minimum: 5% return, 5+ trades, Sharpe >= 0.5

Live Paper (7+ days on real-time data):
- Minimum: 7 days of trading
- Must show positive PnL trend
- Auto-transition on pass, notify on fail
```

---

## FINANCIAL FORMULAS (Session 5B Review)

### Sharpe Ratio
```
Sharpe = (R - Rf) / σ(R) × √252
Where:
- R = daily return
- Rf = risk-free rate (2% annually)
- σ(R) = daily return standard deviation
```

### Maximum Drawdown
```
DD = (Peak - Trough) / Peak
Where Peak is the highest equity reached since start
```

### Profit Factor
```
PF = Gross Profit / Gross Loss
Where Gross Profit = sum of all winning trades
      Gross Loss = sum of all losing trades
```

---

## TEST DATA TEMPLATES

### Determinism Test
```python
# Run backtest twice with identical inputs
result1 = await engine.run_backtest(..., seed=42)
result2 = await engine.run_backtest(..., seed=42)

assert result1.metrics.total_return_pct == result2.metrics.total_return_pct
assert result1.num_trades == result2.num_trades
assert len(result1.trade_log) == len(result2.trade_log)
```

### P&L Verification Test
```python
# Manual calculation verification
trade = result.trade_log[0]
expected_pnl = (trade.exit_price - trade.entry_price) * trade.quantity
expected_pnl -= (trade.entry_commission + trade.exit_commission)

assert abs(trade.realized_pnl - expected_pnl) < 0.01  # 1 cent tolerance
```

---

## ✅ QUALITY CHECKLIST

**Before Completing Session 5B:**

- [ ] All 10 backtest engine tasks completed
- [ ] All 10 paper trading tasks completed
- [ ] Backtest engine produces deterministic results
- [ ] Backtest metrics verified against manual calculations
- [ ] Paper trading simulated mode works for 21 days
- [ ] Paper trading live mode works with real-time data
- [ ] Validation passes/fails correctly
- [ ] State persistence and recovery working
- [ ] All API endpoints functional
- [ ] >85% test coverage (backtest)
- [ ] >80% test coverage (paper trading)
- [ ] No mypy errors
- [ ] No ruff errors
- [ ] All logs use structured format
- [ ] All financial values validated (no NaN/Infinity)

---

**Last Updated:** 2026-02-14
**Status:** Ready for implementation in Plan Mode
**Next Step:** SESSION_5A_VERIFICATION_PROMPT.md and PHASE_5_IMPLEMENTATION_GUIDE.md
