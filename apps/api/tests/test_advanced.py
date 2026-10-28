"""Behavioral tests for the configurable exploration engine."""
from datetime import datetime, timedelta
import numpy as np
import polars as pl
import pytest

from engine import simulate, summarize
from engine_advanced import run_advanced, confirmed_higher_bias


def synthetic_bars(n=2600):
    t = [datetime(2026, 1, 1) + timedelta(minutes=i) for i in range(n)]
    c = np.array([100 + 0.22*np.sin(i/19) + 0.004*i for i in range(n)])
    return pl.DataFrame({
        "timestamp": t, "open": c, "high": c+0.12,
        "low": c-0.12, "close": c,
    })


def config(**overrides):
    cfg = dict(
        name="test", symbol="XAUUSD", timeframe="1m", timeframes=["1m"],
        start_date="", end_date="", initial_deposit=5000,
        mode="random", modeling="ohlc", sizing="compound",
        multi_tf="individual", generations=3, candidates=12,
        families=["ema_cross","rsi_reversion","breakout"],
        direction="both", risk_pct=.5, rr=1., atr_multiplier=1.5,
        cost_bps=1., is_ratio=70, min_trades=2, mc_iterations=100,
        prop_daily_pct=3., prop_max_pct=10.,
    )
    cfg.update(overrides)
    return cfg


def test_advanced_random_selection_and_initial_balance():
    result = run_advanced(synthetic_bars(), config())
    assert result["tested"] == 12
    assert len(result["candidates"]) <= 12
    for c in result["candidates"]:
        assert c["timeframe"] == "1m"
        assert c["model"] == "individual"
        assert "ending_balance" in c["out_of_sample"]


def test_genetic_and_multitimeframe():
    result = run_advanced(synthetic_bars(), config(
        mode="genetic", modeling="open", sizing="fixed",
        multi_tf="combined", timeframes=["1m","5m"],
        candidates=18, generations=3,
    ))
    assert 1 <= result["tested"] <= 18
    assert all(c["context_timeframe"] == "5m" for c in result["candidates"])
    assert all(c["timeframe"] == "1m" for c in result["candidates"])


def test_future_higher_tf_not_visible():
    bars = synthetic_bars()
    bias = confirmed_higher_bias(bars, bars, "5m")
    assert bias[:250].tolist() == [0]*250


def test_modeling_open_ignores_intrabar_high_low():
    n=62
    signal=np.zeros(n, dtype=np.int8)
    signal[41]=1
    op=np.full(n,100.)
    hi=np.full(n,100.)
    lo=np.full(n,100.)
    close=np.full(n,100.)
    atr=np.ones(n)
    days=np.zeros(n, dtype=np.int32)
    hi[42],lo[42]=103.,97.
    fast,_=simulate(signal,op,hi,lo,close,atr,days,0,n,2.,1.,0.,0,1)
    only_open,_=simulate(signal,op,hi,lo,close,atr,days,0,n,2.,1.,0.,0,0)
    assert fast[0] == pytest.approx(-1.)
    assert only_open[0] == pytest.approx(0.)


def test_fixed_initial_risk_is_linear():
    r=np.array([1.,1.,-1.])
    days=np.array([1,2,3],dtype=np.int32)
    fixed=summarize(r,days,1.,3.,10.,"fixed",5000)
    compound=summarize(r,days,1.,3.,10.,"compound",5000)
    assert fixed["ending_balance"]==pytest.approx(5050)
    assert fixed["ending_balance"]!=compound["ending_balance"]


def test_ticks_never_fallback_to_ohlc():
    with pytest.raises(ValueError,match="todavía no está implementado"):
        run_advanced(synthetic_bars(), config(modeling="ticks"))
