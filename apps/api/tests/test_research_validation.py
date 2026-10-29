"""No-lookahead validations for the four quantitative laboratory tabs."""
import numpy as np
import pytest

from engine_advanced import run_advanced
from research_validation import (
 validate_quality, validate_walkforward, validate_multiverse, validate_costs,
 estimated_roundtrip_bps, realized_quality, evaluate_quality,
)
from research_robustness import (
 walkforward_bounds,walkforward_report,synthetic_ohlc,
 gaussian_hmm_regimes,stylized_fact_score,multiverse_report,
)
from engine import summarize
from test_advanced import config,synthetic_bars


def test_quality_defaults_do_not_filter_old_sessions():
    q=validate_quality()
    metrics=summarize(np.array([1.,-1.,2.,1.]),np.array([1,2,3,4]),.5,3,10)
    x=realized_quality([1.,-1.,2.,1.],[1,2,3,4],np.arange(1,100),.5,"fixed",metrics,16)
    assert evaluate_quality(x,q)==[]
    assert 0<=x["dsr"]<=1
    assert x["dsr_trials"]==16


def test_quality_thresholds_and_dsr_respond_to_number_of_trials():
    r=np.array([1.,1.,-1.,2.,1.,-1.,1.,0.])
    days=np.arange(1,9,dtype=np.int32)
    met=summarize(r,days,.5,3,10)
    rare=realized_quality(r,days,np.arange(1,91),.5,"compound",met,1)
    many=realized_quality(r,days,np.arange(1,91),.5,"compound",met,1000)
    assert rare["dsr"]>=many["dsr"]
    cfg=validate_quality({"min_win_rate_pct":99,"max_drawdown_pct":.01,"min_dsr":.99})
    assert evaluate_quality(rare,cfg)


def test_frequency_auto_and_per_day():
    m=summarize(np.array([1.,1.]),np.array([1,2]),.5,3,10)
    q=realized_quality([1.,1.],[1,2],np.arange(1,11),.5,"fixed",m)
    assert evaluate_quality(q,{"min_trades":3})
    assert evaluate_quality(q,{"min_frequency_unit":"day","min_trades":1})
    assert evaluate_quality(q,{"max_trades_per_day":0})==[]


def test_user_costs_convert_spread_commission_and_swaps():
    row=dict(symbol="EURUSD",spread_pips=1.,commission_roundtrip_usd=7.,
             slippage_pips=.5,swap_long_usd=-2.,swap_short_usd=2.,
             pip_size=.0001,contract_size=100000,quote_to_usd=1.,
             hold_days_estimate=2.)
    c=validate_costs({"use_in_backtest":True,"instruments":[row]})
    long_cost=estimated_roundtrip_bps(c,"EURUSD",1.1,1,2)
    short_cost=estimated_roundtrip_bps(c,"EURUSD",1.1,-1,2)
    # Spread+slippage 0.0002 * 100k=$20; comm=$7; financing=$4 long, -$4 short
    assert long_cost==pytest.approx(31/110000*10000)
    assert short_cost==pytest.approx(23/110000*10000)
    with pytest.raises(ValueError,match="Instrumento"):
        estimated_roundtrip_bps(c,"XAUUSD",2000,1,2)
    assert estimated_roundtrip_bps(validate_costs(), "XAUUSD",2000,1,4)==4


def test_invalid_costs_and_mt5_not_allowed():
    with pytest.raises(ValueError,match="MT5"):
        validate_costs({"auto_mt5":True})
    with pytest.raises(ValueError,match="contrato"):
        validate_costs({"use_in_backtest":True,"instruments":[{
            "symbol":"EURUSD","pip_size":0,"contract_size":100000,"quote_to_usd":1,
            "spread_pips":0,"slippage_pips":0,"commission_roundtrip_usd":0,
            "swap_long_usd":0,"swap_short_usd":0,"hold_days_estimate":0}]})


def test_walkforward_bounds_nonoverlap_and_chronology():
    cfg=validate_walkforward({"enabled":True,"test_fraction":4,"rolling_windows":4})
    windows=walkforward_bounds(1000,2000,cfg)
    assert windows==[(1000,1250),(1250,1500),(1500,1750),(1750,2000)]
    assert all(a<b for a,b in windows)


def test_walkforward_report_and_threshold_reject():
    c=validate_walkforward({"enabled":True,"min_efficiency":.5,
                            "min_pass_rate_pct":75.,"min_oos_sharpe":-.5})
    windows=[(200,250),(250,300),(300,350),(350,400)]
    data=[]
    for j in range(4):
        day=np.arange(j*50+1,j*50+51,dtype=np.int32)
        r=np.array([1.,1.,-1.]) if j<2 else np.array([-1.,-1.,-1.])
        data.append((r,day[:3],day))
    report=walkforward_report(windows,data,.0001,c,.5,"fixed",5000,3,10)
    assert report["tested_windows"]==4
    assert report["pass_rate_pct"]<75
    assert not report["eligible"]


def test_synthetic_ohlc_has_valid_candles_and_reproducible_seed():
    n=550
    close=100.+np.cumsum(.02*np.sin(np.arange(n)/9.)+.005)
    op=np.r_[close[0],close[:-1]]
    hi=np.maximum(op,close)+.05
    lo=np.minimum(op,close)-.05
    x=synthetic_ohlc(op,hi,lo,close,np.random.default_rng(9),"balanced",0)
    y=synthetic_ohlc(op,hi,lo,close,np.random.default_rng(9),"balanced",0)
    assert all(np.array_equal(a,b) for a,b in zip(x,y))
    so,sh,sl,sc=x
    assert np.all(sl<=np.minimum(so,sc)) and np.all(sh>=np.maximum(so,sc))
    assert np.all(sc>0) and np.allclose(so[1:],sc[:-1])
    assert 0<=stylized_fact_score(close,sc)<=100


def test_hmm_em_regimes_returns_normalized_weights():
    rng=np.random.default_rng(41)
    x=np.r_[rng.normal(0,.002,400),rng.normal(0,.02,400)]
    result=gaussian_hmm_regimes(x,2,iterations=5)
    assert result["fitted"]
    assert len(result["volatilities"])==2
    assert result["volatilities"][0]<=result["volatilities"][1]
    assert sum(result["regime_weights"])==pytest.approx(1.,abs=.001)


def test_multiverse_scores_are_based_on_all_scenarios():
    cfg=validate_multiverse({"enabled":True,"universes":50,"min_score":65})
    paths=[(1.,5.,90)]*30+[(-1.,50.,20)]*20
    report=multiverse_report(paths,cfg,{"regime_weights":[1.],"fitted":False})
    assert report["universes"]==50
    assert report["survival_pct"]==60.
    assert not report["eligible"]


def test_full_integration_quality_costs_and_walkforward():
    bars=synthetic_bars(2750)
    cfg=config(candidates=10,
        quality={"min_sharpe":0,"max_drawdown_pct":100,"min_win_rate_pct":0,"min_dsr":0},
        walk_forward={"enabled":True,"test_fraction":4,"rolling_windows":4,"min_training_bars":250,
                      "min_oos_sharpe":-5,"min_efficiency":0,"min_pass_rate_pct":0},
        costs={"use_in_backtest":True,"instruments":[{
            "symbol":"XAUUSD","pip_size":.1,"contract_size":100,"quote_to_usd":1,
            "spread_pips":2,"slippage_pips":.2,"commission_roundtrip_usd":7,
            "swap_long_usd":0,"swap_short_usd":0,"hold_days_estimate":0}],"auto_mt5":False})
    result=run_advanced(bars,cfg)
    assert result["tested"]>0
    assert result["quality_config"]["max_drawdown_pct"]==100
    for c in result["candidates"]:
        assert c["estimated_cost_bps"]>0
        assert "quality_is" in c and "quality_oos" in c
        assert c["walk_forward"] is not None


def test_full_multiverse_recomputes_signals_on_synthetic_bars():
    bars=synthetic_bars(2600)
    result=run_advanced(bars,config(candidates=10,
        multiverse={"enabled":True,"universes":50,"mix":"conservative",
                    "top_n":1,"regimes":1,"validate_fat_tails":False,
                    "min_score":0,"max_robust_drawdown_pct":100}))
    if result["candidates"]:
        report=result["candidates"][0]["multiverse"]
        assert report is not None
        assert report.get("universes")==50
        assert report.get("hidden_regimes") is not None


def test_maximum_daily_trades_applies_to_worst_day_not_average():
    # Five trades distributed 3 on day one, 1 each on day 2/3. Mean 1/day
    # over five observed days but individual day exceeds a cap of 2.
    r=np.ones(5)
    exit_days=np.array([1,1,1,2,3],dtype=np.int32)
    met=summarize(r,exit_days,.5,3,10)
    q=realized_quality(r,exit_days,np.arange(1,6),.5,"fixed",met)
    assert q["trades_per_day"]==1.
    assert q["max_trades_observed_day"]==3
    assert evaluate_quality(q,{"max_trades_per_day":2})
