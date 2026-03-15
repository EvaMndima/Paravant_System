import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from src.core.strategy.backtest.engine import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.backtest.validator import SUPERVISED_THRESHOLDS
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher

async def run():
    end = datetime.now(timezone.utc)
    fetcher = MarketDataFetcher()
    factory = SignalGeneratorFactory()
    engine = BacktestEngine(signal_generator_factory=factory)
    config = BacktestConfig(initial_capital=10000.0, commission_rate=0.001, slippage_rate=0.0005)
    tests = [
        ("macd_btc","MACD_Pullback_BTC","macd_pullback","BTCUSDT",60,
         {"macd_fast":12,"macd_slow":26,"macd_signal":9,"pullback_ema_period":21,"atr_period":14,"atr_stop_multiplier":1.5,"risk_reward_ratio":2.0,"pullback_tolerance_pct":0.5}),
        ("macd_eth","MACD_Pullback_ETH","macd_pullback","ETHUSDT",60,
         {"macd_fast":12,"macd_slow":26,"macd_signal":9,"pullback_ema_period":21,"atr_period":14,"atr_stop_multiplier":1.5,"risk_reward_ratio":2.0,"pullback_tolerance_pct":0.5}),
        ("bb90","BB_Squeeze_ETH_90d","bb_squeeze_breakout","ETHUSDT",90,
         {"bb_period":20,"bb_std_dev":2.0,"squeeze_threshold":0.07,"squeeze_lookback":10,"macd_fast":12,"macd_slow":26,"macd_signal":9,"volume_threshold":1.2}),
        ("don_nv","Donchian_BTC_noVol","donchian_atr","BTCUSDT",60,
         {"donchian_period":20,"atr_period":14,"atr_threshold":0.003,"atr_stop_multiplier":2.5,"volume_ma_period":20,"volume_multiplier":1.0}),
    ]
    cache = {}
    for tid,nm,tmpl,sym,lb,params in tests:
        k=(sym,lb)
        if k not in cache:
            s=await fetcher.fetch_historical_ohlcv(symbol=sym,timeframe="1h",start_date=end-timedelta(days=lb),end_date=end)
            cache[k]=s
            print(f"Fetched {sym} {lb}d: {len(s)} bars",flush=True)
    for tid,nm,tmpl,sym,lb,params in tests:
        strat=SimpleNamespace(id=tid,name=nm,template_id=tmpl,parameters=params)
        print(f"Running {nm}...",flush=True)
        r=engine.run_backtest(strategy=strat,series=cache[(sym,lb)],config=config,thresholds=SUPERVISED_THRESHOLDS)
        m=r.metrics
        v="PASS" if r.passed_validation else ("FAIL("+r.validation_errors[0][:35]+")" if r.validation_errors else "FAIL")
        print(f"{nm:<32} ret={m.total_return_pct:+5.1f}% sh={m.sharpe_ratio:6.3f} pf={m.profit_factor:5.3f} dd={m.max_drawdown_pct:4.1f}% wr={m.win_rate_pct:4.1f}% trades={m.total_trades:3} exp=${m.expectancy:7.2f}  {v}",flush=True)

asyncio.run(run())
