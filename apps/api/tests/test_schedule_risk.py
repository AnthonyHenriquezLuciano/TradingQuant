"""Verification of session masks, forced exits and realized-risk limits."""
from datetime import datetime,timedelta
import numpy as np
import polars as pl
import pytest
from engine_schedule import time_arrays,validate_schedule
from engine_capital import normalize_risk_rules,simulate_capital


def make_times(start, count, step=60):
    return pl.DataFrame({
        "timestamp":[start+timedelta(minutes=step*i) for i in range(count)]
    })


def test_london_session_in_utc_and_rollover():
    frame=make_times(datetime(2026,10,26),48)
    config=dict(sessions=["london"],avoid_rollover=True)
    allowed,forced,days,weeks,months=time_arrays(frame,"UTC",config)
    assert allowed[7] and allowed[15]
    assert not allowed[6] and not allowed[16]
    assert not allowed[21]
    assert not np.any(forced)
    assert weeks[0]==weeks[20]
    assert months[0]==months[47]


def test_utc_cross_midnight_asia():
    frame=make_times(datetime(2026,10,26),25)
    ok,*_=time_arrays(frame,"UTC",dict(sessions=["asian"]))
    assert ok[0] and ok[8] and not ok[9] and not ok[20] and ok[21]


def test_source_timezone_conversion_and_dst():
    frame=make_times(datetime(2026,10,26,10),4)
    # After October 25 UK transitions to standard time, 10:00 London is 10:00 UTC.
    ok,*_=time_arrays(frame,"Europe/London",dict(sessions=["london"]))
    assert ok[0]
    frame_summer=make_times(datetime(2026,7,6,7),2)
    # Summer 07:00 London = 06:00 UTC, before London UTC fixed window.
    ok,*_=time_arrays(frame_summer,"Europe/London",dict(sessions=["london"]))
    assert not ok[0] and ok[1]


def test_friday_cutoff_and_monday_open():
    friday=make_times(datetime(2026,10,30,18),4)
    ok,forced,*_=time_arrays(friday,"UTC",{
        "sessions":["all_day"],"close_before_weekend":True
    })
    assert ok[0] and not ok[1] and forced[1]
    monday=make_times(datetime(2026,11,2),2)
    ok,*_=time_arrays(monday,"UTC",{"sessions":["all_day"],"avoid_monday_open":True})
    assert not ok[0] and ok[1]


def test_ny_close_and_rollover_minutes():
    frame=pl.DataFrame({"timestamp":[
        datetime(2026,10,29,20,54),
        datetime(2026,10,29,20,55),
        datetime(2026,10,29,21,9),
        datetime(2026,10,29,21,10),
    ]})
    ok,*_=time_arrays(frame,"UTC",{"sessions":["all_day"],"avoid_rollover":True})
    assert ok.tolist()==[True,False,False,True]
    ok,forced,*_=time_arrays(frame,"UTC",{"sessions":["all_day"],"close_before_ny":True})
    assert ok.tolist()==[False]*4
    assert forced.all()


def test_reject_mixed_all_day():
    with pytest.raises(ValueError,match="24 horas"):
        validate_schedule({"sessions":["all_day","tokyo"]})


def scenario():
    n=65
    signal=np.zeros(n,dtype=np.int8)
    op=np.full(n,100.,dtype=float)
    high=op.copy();low=op.copy();close=op.copy()
    atr=np.ones(n)
    days=np.ones(n,dtype=np.int32)
    weeks=np.ones(n,dtype=np.int32)
    months=np.ones(n,dtype=np.int32)
    return signal,op,high,low,close,atr,days,weeks,months


def evaluate(m,allowed=None,forced=None,max_gains=None,max_losses=None,win_streak=0,loss_streak=0):
    sig,op,high,low,close,atr,days,weeks,months=m
    return simulate_capital(
        sig,op,high,low,close,atr,days,0,len(op),
        0,1.,1.,0.,0,1,.5,5000.,False,
        False,1.,False,1.,0,0,0,3.,10.,0.,
        allowed,forced,weeks,months,max_gains,max_losses,win_streak,loss_streak
    )


def test_filter_blocks_entries():
    m=scenario();m[0][41]=1;m[2][42]=102
    allowed=np.zeros(65,dtype=np.bool_)
    r,_=evaluate(m,allowed=allowed)
    assert len(r)==0


def test_forced_close_uses_first_available_open():
    m=scenario();m[0][41]=1
    m[1][43]=99.75
    forced=np.zeros(65,dtype=np.bool_);forced[43]=True
    r,_=evaluate(m,forced=forced)
    assert len(r)==1
    assert r[0]==pytest.approx(-.25)


def test_gain_rule_pauses_new_entries():
    m=scenario();m[0][41]=1;m[0][46]=1
    m[2][42]=105;m[2][47]=105
    gains=np.array([.01,0,0,0],dtype=np.float64)
    losses=np.zeros(4,dtype=np.float64)
    r,_=evaluate(m,max_gains=gains,max_losses=losses)
    assert len(r)==1


def test_loss_streak_daily_stop():
    m=scenario();m[0][41]=1;m[0][45]=1
    m[3][42]=98;m[3][46]=98
    r,_=evaluate(m,loss_streak=1)
    assert len(r)==1


def test_risk_rules_validation():
    with pytest.raises(ValueError,match="Valor de riesgo"):
        normalize_risk_rules({"max_monthly_loss_pct":-3})
