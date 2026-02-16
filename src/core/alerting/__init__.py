"""Multi-channel alerting system for PARAVANT Trading System.

Provides alert management with:
- Multi-channel delivery (Telegram, Email, SMS)
- Alert level routing (INFO, WARNING, ERROR, CRITICAL)
- Rate limiting to prevent spam
- Emergency contact escalation
- Alert triggers for system events

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from src.core.alerting.manager import Alert, AlertLevel, AlertManager
from src.core.alerting.triggers import AlertTriggers

__all__ = [
    "Alert",
    "AlertLevel",
    "AlertManager",
    "AlertTriggers",
]
