import pytest
from src.data.models import Account, Strategy, StrategyAssignment, AssignmentStatus, StrategyType, StrategyStatus

def test_enum_assignment(db_session):
    print(f"DEBUG IN TEST: AssignmentStatus.ACTIVE = {AssignmentStatus.ACTIVE}")
    print(f"DEBUG IN TEST: AssignmentStatus.ACTIVE.value = '{AssignmentStatus.ACTIVE.value}'")
    print(f"DEBUG IN TEST: type = {type(AssignmentStatus.ACTIVE)}")
    
    account = Account(name="Test", broker="binance")
    strategy = Strategy(
        name="Test",
        type=StrategyType.TREND_FOLLOWING,
        status=StrategyStatus.LIVE,
        template_id="tmp_123"
    )
    db_session.add(account)
    db_session.add(strategy)
    db_session.commit()

    print(f"DEBUG IN TEST: Creating Assignment with status={AssignmentStatus.ACTIVE}")
    assignment = StrategyAssignment(
        account_id=account.id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        status=AssignmentStatus.ACTIVE,
        regime_filter=["trending_up"]
    )
    db_session.add(assignment)
    db_session.commit()
    print("DEBUG IN TEST: Success")
