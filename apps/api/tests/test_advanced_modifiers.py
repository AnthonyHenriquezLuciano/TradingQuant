"""Advanced execution guarantees: pending entries, RR, capped composite risk and lookahead safety."""
from datetime import datetime,timedelta
import numpy as np
import pytest
from advanced_modifiers import DEFAULT_ADVANCED,validate_advanced,is_active,execution_arguments
from engine_advanced_orders import simulate_advanced_orders
from engine_advanced import run_advanced
from test_advanced import config,synthetic_bars


def market(n=80):
    signals=np.zeros(n,dtype=np.int8)
    op=np.full(n,100.,dtype=np.float64)
    hi=np.full(n,100.,dtype=np.float64)
    lo=np.full(n,100.,dtype=np.float64)
    close=np.full(n,100.,dtype=np.float64)
    atr=np.ones(n,dtype=np.float64)
    days=np.ones(n,dtype=np.int32)
    weeks=np.ones(n,dtype=np.int32)
    months=np.ones(n,dtype=np.int32)
    return signals,op,hi,lo,close,atr,days,weeks,months


def run(m,entry="market",**patch):
    cfg=validate_advanced({"entry_modes":[entry],**patch})
    sig,op,hi,lo,close,atr,days,weeks,months=m
    n=len(sig)
    return simulate_advanced_orders(
        sig,op,hi,lo,close,atr,days,0,n,
        0,1.,2.,0.,0,1,
        .5,5000.,False,
        False,1.,False,1.,0,
        0,0,3.,10.,0.,
        np.ones(n,dtype=np.bool_),np.zeros(n,dtype=np.bool_),
        weeks,months,np.zeros(4),np.zeros(4),0,0,
        {"market":0,"stop":1,"limit":2}[entry],*execution_arguments(cfg)
    )


def test_market_default_equivalence():
    from engine_capital import simulate_capital
    m=market()
    m[0][41]=1
    m[2][42]=105.
    args=m[:7]
    r,_=run(m)
    plain,_=simulate_capital(*args,0,len(m[0]),0,1.,2.,0.,0,1,.5,5000.,False,
                             False,1.,False,1.,0,0,0,3.,10.,0.,
                             np.ones(len(m[0]),bool),np.zeros(len(m[0]),bool),
                             m[7],m[8],np.zeros(4),np.zeros(4),0,0)
    assert r.tolist()==pytest.approx(plain.tolist())


def test_fixed_rr_overrides_exit_ratio():
    m=market();m[0][41]=1;m[2][42]=104.
    r,_=run(m,fixed_rr_enabled=True,fixed_rr=3)
    assert r.tolist()==pytest.approx([3.])


def test_stop_fills_at_previous_confirmed_high_then_next_bar_tp():
    m=market();m[0][41]=1
    m[2][42]=100.5
    m[2][43]=105.
    r,_=run(m,entry="stop")
    assert len(r)==1
    assert r[0]==pytest.approx(2.)


def test_unfilled_limit_order_expires_no_fake_fills():
    m=market();m[0][41]=1
    r,_=run(m,entry="limit",order_expiry_bars=3)
    assert len(r)==0


def test_limit_order_fills_on_retracement():
    m=market();m[0][41]=1;m[3][42]=99.5;m[2][43]=104.
    r,_=run(m,entry="limit")
    assert len(r)==1
    assert r[0]==pytest.approx(2.)


def test_multiple_winners_anti_martingale_increases_next_r():
    m=market();m[0][41]=1;m[0][45]=1
    m[2][42]=105.;m[2][46]=105.
    r,_=run(m,variable_risk_enabled=True,variable_risk_mode="anti_martingale",risk_multiplier=1.5)
    assert len(r)==2
    assert r[0]==pytest.approx(2.)
    assert r[1]==pytest.approx(3.)


def test_martingale_trades_budget_capped_at_2pct():
    m=market();m[0][41]=1;m[0][44]=1
    m[3][42]=98.
    m[2][45]=105.
    r,_=run(m,variable_risk_enabled=True,variable_risk_mode="martingale",risk_multiplier=3)
    assert r[0]==pytest.approx(-1.)
    assert r[1]==pytest.approx(6.)


def test_dca_reserves_risk_for_entire_composite_position():
    m=market();m[0][41]=1
    m[3][43]=99.4
    m[3][44]=98.5
    r,_=run(m,dca_enabled=True,dca_levels=3,dca_spacing=0.5)
    assert len(r)==1
    assert -1.0000001<=r[0]<0


def test_pyramid_composite_does_not_double_risk():
    m=market();m[0][41]=1
    m[2][43]=100.6
    m[3][44]=98.5
    r,_=run(m,pyramid_enabled=True,pyramid_levels=3,pyramid_spacing=.5)
    assert len(r)==1
    assert -1.0000001<=r[0]<0


def test_break_even_only_active_after_close():
    m=market();m[0][41]=1
    m[4][43]=101.5
    m[3][44]=99.
    r,_=run(m,be_enabled=True,be_unit="r",be_trigger=1.)
    assert r.tolist()==pytest.approx([0.])


def test_reject_non_ohlc_execution_for_pending_orders():
    with pytest.raises(ValueError,match="requieren modelado OHLC"):
        run_advanced(synthetic_bars(),config(modeling="open",
               advanced_modifiers={"entry_modes":["stop"]}))


def test_invalid_modifiers_rejected():
    with pytest.raises(ValueError,match="tamaño real de pip"):
        validate_advanced({"be_enabled":True,"be_offset_pips":2,"pip_size":0})
    with pytest.raises(ValueError,match="entrada"):
        validate_advanced({"entry_modes":[]})


@pytest.mark.parametrize("entry",["market","stop","limit"])
def test_run_advanced_exports_entry_variant(entry):
    result=run_advanced(synthetic_bars(2600),config(
       candidates=10,advanced_modifiers={"entry_modes":[entry],"fixed_rr_enabled":True,"fixed_rr":1.5}
    ))
    assert result["tested"]<=10
    assert all(c["entry_mode"]==entry for c in result["candidates"])
