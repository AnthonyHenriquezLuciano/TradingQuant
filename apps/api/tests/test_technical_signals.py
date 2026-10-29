"""Regression coverage for every enabled completed-bar OHLC indicator."""
import numpy as np
from technical_signals import SUPPORTED,technical_signals


def sample(n=600,seed=101):
    rng=np.random.default_rng(seed)
    close=100+np.cumsum(rng.normal(0,.3,n))+3*np.sin(np.arange(n)/7)
    op=np.concatenate(([close[0]],close[:-1]))
    high=np.maximum(op,close)+rng.uniform(.01,.45,n)
    low=np.minimum(op,close)-rng.uniform(.01,.45,n)
    return op,high,low,close


def test_every_enabled_technical_family_uses_completed_candles_only():
    o,h,l,c=sample()
    cut=430
    for name in SUPPORTED:
        signals=technical_signals(name,14,o,h,l,c)
        assert signals.shape==(len(c),),name
        assert signals.dtype==np.int8,name
        assert set(np.unique(signals)).issubset({-1,0,1}),name
        assert not np.any(signals[:40]),name
        truncated=technical_signals(name,14,o[:cut],h[:cut],l[:cut],c[:cut])
        # Full future must not change ANY earlier signal.
        assert np.array_equal(signals[:cut],truncated),name


def test_completed_bar_signal_is_not_repainted_by_far_future_changes():
    o,h,l,c=sample()
    altered_c=c.copy();altered_c[300:]+=200
    altered_h=h.copy();altered_h[300:]+=200
    altered_l=l.copy();altered_l[300:]+=200
    altered_o=o.copy();altered_o[300:]+=200
    for name in SUPPORTED:
        base=technical_signals(name,14,o,h,l,c)
        altered=technical_signals(name,14,altered_o,altered_h,altered_l,altered_c)
        assert np.array_equal(base[:300],altered[:300]),name
