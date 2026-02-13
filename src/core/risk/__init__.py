"""Risk management module.

Provides the core risk engine for the PARAVANT Trading System:
- RiskController: Central orchestrator for order validation
- KillSwitch: Emergency trading halt mechanism
- DeadMansSwitch: Auto-halt on system unresponsiveness
- Circuit breakers: Stateful risk limits with cooldown
- Volatility analysis: Regime classification and filtering
- Time/event filters: Trading restrictions by time and events
- Risk check functions and position sizing methods
- Immutable data types for the risk pipeline
"""
from src.core.risk.circuit_breakers import (CircuitBreaker,
                                            CircuitBreakerManager,
                                            CircuitBreakerResult,
                                            ConsecutiveLossCircuitBreaker,
                                            CorrelationCircuitBreaker,
                                            DailyLossCircuitBreaker,
                                            DrawdownCircuitBreaker,
                                            WeeklyLossCircuitBreaker)
from src.core.risk.controller import RiskController
from src.core.risk.dead_mans_switch import DeadMansSwitch
from src.core.risk.event_filter import (EventFilter, EventFilterResult,
                                        TradingEvent)
from src.core.risk.kill_switch import KillSwitch
from src.core.risk.sizing import (calculate_atr_size,
                                  calculate_available_capital,
                                  calculate_fixed_risk_size,
                                  calculate_kelly_size)
from src.core.risk.time_filter import TimeFilterResult, WeekendHolidayFilter
from src.core.risk.types import (OrderRequest, PortfolioState,
                                 PositionSizeResult, RiskCheckResult)
from src.core.risk.volatility import (VolatilityAnalyzer, VolatilityRegime,
                                      VolatilityResult)

__all__ = [
    # Controller and switches
    "RiskController",
    "KillSwitch",
    "DeadMansSwitch",
    # Circuit breakers
    "CircuitBreaker",
    "CircuitBreakerResult",
    "CircuitBreakerManager",
    "DailyLossCircuitBreaker",
    "WeeklyLossCircuitBreaker",
    "DrawdownCircuitBreaker",
    "ConsecutiveLossCircuitBreaker",
    "CorrelationCircuitBreaker",
    # Volatility
    "VolatilityRegime",
    "VolatilityResult",
    "VolatilityAnalyzer",
    # Time filter
    "TimeFilterResult",
    "WeekendHolidayFilter",
    # Event filter
    "TradingEvent",
    "EventFilterResult",
    "EventFilter",
    # Data types
    "OrderRequest",
    "PortfolioState",
    "PositionSizeResult",
    "RiskCheckResult",
    # Sizing functions
    "calculate_fixed_risk_size",
    "calculate_atr_size",
    "calculate_kelly_size",
    "calculate_available_capital",
]
