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


def test_reject_fake_upsampling_from_five_minute_source():
    source = synthetic_bars(2600).filter(
        pl.col("timestamp").dt.minute() % 5 == 0
    )
    with pytest.raises(ValueError, match="No se generan velas"):
        run_advanced(source, config(timeframes=["1m"],timeframe="1m"))


def test_indicator_range_sampler_respects_limits():
    import random
    from engine_advanced import checked_ranges, random_gene, mutate_or_cross
    cfg = config()
    cfg["indicator_ranges"] = dict(
        ema_fast_min=9, ema_fast_max=11,
        ema_slow_min=31, ema_slow_max=34,
        rsi_period_min=13, rsi_period_max=16,
        rsi_oversold_min=26, rsi_oversold_max=29,
        breakout_lookback_min=18, breakout_lookback_max=21,
    )
    ranges = checked_ranges(cfg)
    rng = random.Random(10)
    for kind in (0, 1, 2):
        for _ in range(20):
            a = random_gene(rng, [kind], ranges)
            b = random_gene(rng, [kind], ranges)
            for gene in (a, mutate_or_cross(rng, a, b, [kind], ranges)):
                family, fast, slow = gene
                assert family == kind
                if kind == 0:
                    assert 9 <= fast <= 11
                    assert 31 <= slow <= 34
                    assert slow >= fast + 8
                elif kind == 1:
                    assert 13 <= fast <= 16
                    assert 26 <= slow <= 29
                else:
                    assert fast == 0
                    assert 18 <= slow <= 21


def test_indicator_ranges_propagate_into_candidates():
    cfg = config(candidates=12, families=["breakout"])
    cfg["indicator_ranges"] = {"breakout_lookback_min": 18, "breakout_lookback_max": 20}
    result = run_advanced(synthetic_bars(), cfg)
    assert result["tested"] <= 6
    assert all(18 <= item["params"]["lookback"] <= 20 for item in result["candidates"])


def test_invalid_indicator_ranges_rejected():
    from engine_advanced import checked_ranges
    with pytest.raises(ValueError, match="Rango inválido"):
        checked_ranges({"indicator_ranges": {"rsi_period_min": 25, "rsi_period_max": 12}})


def test_market_situation_ranges_are_independent():
    import random
    from engine_advanced import checked_ranges, random_gene, mutate_or_cross
    ranges = checked_ranges({"indicator_ranges": {
        "london_high_sweep_buffer_min": 2,
        "london_high_sweep_buffer_step": 2,
        "london_high_sweep_buffer_max": 6,
        "asia_low_sweep_buffer_min": 9,
        "asia_low_sweep_buffer_step": 3,
        "asia_low_sweep_buffer_max": 15,
    }})
    rng = random.Random(17)
    for kind, allowed in ((3, {2,4,6}),(6, {9,12,15})):
        for _ in range(30):
            a = random_gene(rng,[kind],ranges)
            b = random_gene(rng,[kind],ranges)
            c = mutate_or_cross(rng,a,b,[kind],ranges)
            assert a[1] in allowed
            assert b[1] in allowed
            assert c[1] in allowed
