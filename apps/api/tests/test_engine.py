from pathlib import Path

import numpy as np
import polars as pl
import pytest

from engine import load_data, summarize, simulate, bootstrap, run_exploration


def test_import_mt5_tab_headers(tmp_path: Path):
    path = tmp_path / "mt5.csv"
    lines = ["<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>"]
    for i in range(400):
        day = 1 + i // 1440
        hour = (i // 60) % 24
        minute = i % 60
        lines.append(f"2026.10.{day:02d}\t{hour:02d}:{minute:02d}:00\t100\t101\t99\t100.1\t50")
    path.write_text("\n".join(lines))
    df = load_data(path)
    assert len(df) == 400
    assert df.columns == ["timestamp", "open", "high", "low", "close"]
    assert str(df[0, "timestamp"]).startswith("2026-10-01")


def test_stop_has_priority_when_bar_hits_both():
    n = 60
    op = np.full(n, 100.0)
    hi = np.full(n, 100.0)
    lo = np.full(n, 100.0)
    cl = np.full(n, 100.0)
    atr = np.ones(n)
    days = np.zeros(n, dtype=np.int32)
    signals = np.zeros(n, dtype=np.int8)
    signals[41] = 1
    hi[42], lo[42] = 103.0, 97.0
    outcomes, trade_days = simulate(signals, op, hi, lo, cl, atr, days, 0, n, 2., 1., 0., 0)
    assert len(outcomes) == 1
    assert outcomes[0] == pytest.approx(-1.)
    assert len(trade_days) == 1


def test_daily_and_total_static_dd():
    outcomes = np.array([-1., -1., -1., -1.])
    days = np.array([1, 1, 1, 1], dtype=np.int32)
    result = summarize(outcomes, days, risk_pct=1, daily=3, total=10)
    assert result["daily_breached"] is True
    assert result["total_breached"] is False
    assert result["trades"] == 4


def test_bootstrap_is_reproducible():
    outcomes = np.array([1., -1., 1., -1., .4])
    a = bootstrap(outcomes, .5, 100, 10, seed=123)
    b = bootstrap(outcomes, .5, 100, 10, seed=123)
    assert a == b


def test_run_search_on_synthetic_ohlc():
    n = 1250
    ts = [__import__("datetime").datetime(2026, 1, 1) +
          __import__("datetime").timedelta(minutes=i) for i in range(n)]
    close = np.array([100 + .4*np.sin(i / 12) + .001 * i for i in range(n)])
    high = close + .17
    low = close - .17
    df = pl.DataFrame({"timestamp":ts, "open":close, "high":high, "low":low, "close":close})
    config = {"timeframe":"1m", "is_ratio":70, "families":["ema_cross","rsi_reversion","breakout"],
              "candidates":8, "direction":"both","rr":1.,"atr_multiplier":1.5,
              "cost_bps":1.,"risk_pct":.5,"prop_daily_pct":3.,"prop_max_pct":10.,
              "mc_iterations":100,"min_trades":5}
    result = run_exploration(df, config)
    assert result["tested"] == 8
    assert len(result["candidates"]) <= 8
    for candidate in result["candidates"]:
        assert candidate["in_sample"]["trades"] >= 0
        assert "monte_carlo" in candidate
        assert candidate["monte_carlo"]["iterations"] == 100


def test_csv_invalid_header_rejected(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("foo,bar\n" + "1,2\n"*400)
    with pytest.raises(ValueError, match="Faltan columnas"):
        load_data(path)
