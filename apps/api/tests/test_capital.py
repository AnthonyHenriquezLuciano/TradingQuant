"""Deterministic checks for capital, fills and ATR-linked take profit."""
import random

import numpy as np
import pytest

from engine_capital import normalize_capital, sample_exit, mutate_exit, simulate_capital


def market(n=70):
    signal=np.zeros(n,dtype=np.int8)
    op=np.full(n,100.,dtype=np.float64)
    high=np.full(n,100.,dtype=np.float64)
    low=np.full(n,100.,dtype=np.float64)
    close=np.full(n,100.,dtype=np.float64)
    atr=np.full(n,1.,dtype=np.float64)
    days=np.ones(n,dtype=np.int32)
    return signal,op,high,low,close,atr,days


def simulate(m, sl=1., tp=2., modeling=1, breakeven=False, be_r=1.,
             trailing=False, trailing_atr=1., max_hold=0, max_per_day=0,
             cooldown=0, profit_stop=0,mode=0):
    sig,op,hi,lo,cl,atr,days=m
    return simulate_capital(sig,op,hi,lo,cl,atr,days,0,len(op),
                            mode,sl,tp,0.,0,modeling,
                            .5,5000.,False,
                            breakeven,be_r,trailing,trailing_atr,max_hold,
                            max_per_day,cooldown,3.,10.,profit_stop)


def test_atr_stop_linked_tp_multiplier():
    m=market()
    m[0][41]=1
    m[2][42]=102.5    # TP 2R for ATR(1)*SL(1)
    m[3][42]=99.5
    r,days=simulate(m)
    assert len(r)==1
    assert r[0]==pytest.approx(2.)
    assert days[0]==1


def test_ohlc_stop_first_when_both_are_hit():
    m=market()
    m[0][41]=1
    m[2][42]=105.
    m[3][42]=98.
    r,_=simulate(m)
    assert r[0]==pytest.approx(-1.)


def test_be_activated_after_bar_closes_only():
    m=market()
    m[0][41]=1
    m[2][42]=101.6
    m[4][42]=101.5
    m[2][43]=101.
    m[3][43]=99.
    r,_=simulate(m,tp=4,breakeven=True,be_r=1.)
    assert r[0]==pytest.approx(0.)


def test_trailing_from_completed_bar():
    m=market()
    m[0][41]=1
    m[2][42]=102.5
    m[4][42]=102.
    m[2][43]=102.1
    m[3][43]=100.5
    r,_=simulate(m,tp=5,trailing=True,trailing_atr=1.)
    assert r[0]==pytest.approx(1.)


def test_day_trade_cap_limits_entries():
    m=market()
    m[0][41]=1
    m[0][45]=1
    m[3][42]=98.       # stop on first entry
    m[3][46]=98.       # second stopped only if it opens
    r,_=simulate(m,max_per_day=1)
    assert len(r)==1


def test_fixed_percentage_stop_and_linked_target():
    m=market()
    m[0][41]=1
    m[2][42]=102.5
    # 1% of entry 100 is 1; target is 2 units from entry
    r,_=simulate(m,sl=1.,tp=2.,mode=2)
    assert r[0]==pytest.approx(2.)


def test_range_sampling_and_genetic_step_grid():
    cap=normalize_capital({"capital":{
        "exit_mode":"atr_linked",
        "sl_atr":{"from":1.,"step":.5,"to":2.},
        "tp_multiplier":{"from":.5,"step":.25,"to":1.},
    }})
    rng=random.Random(2)
    for _ in range(30):
        a=sample_exit(rng,cap)
        b=sample_exit(rng,cap)
        mutated=mutate_exit(rng,cap,a,b)
        assert a[0] in (1.,1.5,2.)
        assert mutated[0] in (1.,1.5,2.)
        assert mutated[1] in (.5,.75,1.)


def test_reject_invalid_exit_range():
    with pytest.raises(ValueError,match="Rango de salida inválido"):
        normalize_capital({"capital":{"sl_atr":{"from":3.,"step":.1,"to":.5}}})


def test_legacy_config_uses_same_single_exit():
    cap=normalize_capital({"rr":1.5,"atr_multiplier":2.})
    assert sample_exit(random.Random(0),cap)==(2.,1.5)
