from datetime import datetime, timedelta
import numpy as np
import polars as pl
import pytest

from market_setups import sweep_reference, sweep_signals


def intraday(days=3):
    start = datetime(2026, 6, 1)
    n = days*96
    ts = [start+timedelta(minutes=15*i) for i in range(n)]
    close = np.full(n,100.,dtype=float)
    high = np.full(n,101.,dtype=float)
    low = np.full(n,99.,dtype=float)
    return ts,close,high,low


def dataframe(ts,close,high,low):
    return pl.DataFrame({"timestamp":ts,"open":close.copy(),
                         "close":close,"high":high,"low":low})


def test_london_high_sweep_only_after_session_closes():
    ts,c,h,l = intraday()
    # 2026-06-01 15:30 UTC = 16:30 London (BST): range already closed.
    after = ts.index(datetime(2026,6,1,15,30))
    # 14:00 UTC = 15:00 London (inside session, level must be unavailable).
    before = ts.index(datetime(2026,6,1,14,0))
    h[after] = 102.
    h[before] = 103.
    df = dataframe(ts,c,h,l)
    level,days,valid = sweep_reference(df,3,"UTC","15m")
    assert not valid[before]
    assert valid[after]
    assert level[after] == pytest.approx(103.)  # includes the full London session
    # 102 isn't above the completed session maximum 103; no signal.
    signals = sweep_signals(h,l,c,level,days,valid,-1,0)
    assert signals[after] == 0
    # Now really sweep the completed max and close below it.
    h[after] = 104.
    signals = sweep_signals(h,l,c,level,days,valid,-1,0)
    assert signals[after] == -1
    assert np.count_nonzero(signals[:96]) == 1


def test_tokyo_low_sweep_and_buffer():
    ts,c,h,l = intraday()
    # 2026-06-01 10:00 UTC = 19:00 JST after the 09:00–17:00 session.
    after = ts.index(datetime(2026,6,1,10,0))
    l[after]=98.
    df = dataframe(ts,c,h,l)
    levels,days,valid = sweep_reference(df,6,"UTC","15m")
    assert valid[after]
    assert levels[after] == pytest.approx(99.)
    assert sweep_signals(h,l,c,levels,days,valid,1,0)[after] == 1
    assert sweep_signals(h,l,c,levels,days,valid,1,110)[after] == 0


def test_previous_day_high_only_uses_completed_prior_day():
    ts,c,h,l = intraday()
    first = ts.index(datetime(2026,6,1,9,0))
    later = ts.index(datetime(2026,6,2,9,0))
    h[first] = 103.
    h[later] = 105.
    df = dataframe(ts,c,h,l)
    level,days,valid = sweep_reference(df,7,"UTC","15m")
    assert not valid[first]
    assert valid[later]
    assert level[later] == pytest.approx(103.)
    signals=sweep_signals(h,l,c,level,days,valid,-1,1)
    assert signals[later] == -1


def test_reject_daily_bars_for_session_sweeps():
    ts,c,h,l=intraday()
    with pytest.raises(ValueError,match="M1 a H1"):
        sweep_reference(dataframe(ts,c,h,l),3,"UTC","1d")
