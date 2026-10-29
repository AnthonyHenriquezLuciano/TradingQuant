"""Point-in-time disclaimers aside, all realized-equity funding rules are executable."""
import numpy as np
import pytest

from funding_simulator import DEFAULT_FUNDING, validate_funding, _run_phase, simulate_funding
from optimization_objectives import objective_score


def conf(**kw):
    return validate_funding({**DEFAULT_FUNDING,**kw})


def test_1_2_3_phases_and_invalid_ranges():
    for n in (1,2,3):
        assert len(conf(phases=[{"target_pct":5,"max_days":30,"min_days":0}]*n)["phases"])==n
    with pytest.raises(ValueError,match="entre 1 y 3"):
        conf(phases=[])
    with pytest.raises(ValueError,match="días mínimos"):
        conf(phases=[{"min_days":4,"max_days":3}])
    with pytest.raises(ValueError,match="percentil"):
        conf(pass_day_percentile=33)


def test_profitable_day_minimum_threshold_and_zero_any_trade():
    phase={"target_pct":2,"max_days":5,"min_days":3,"min_profit_day_pct":.5}
    cfg=conf(phases=[phase],daily_loss_pct=0)
    # 1.0% / -0.1% / +1.2% / +1.0% -> only 3 profitable days
    status,day=_run_phase(np.array([.01,-.001,.012,.01,0]),np.ones(5,dtype=bool),phase,cfg)
    assert status=="passed" and day==4
    zero=dict(phase,min_profit_day_pct=0)
    status,day=_run_phase(np.array([.02,0,0,0,0]),np.array([1,1,1,0,0],dtype=bool),zero,cfg)
    assert status=="passed" and day==3


def test_min_days_ignores_no_trade_days():
    phase={"target_pct":1,"max_days":5,"min_days":2,"min_profit_day_pct":0}
    cfg=conf(phases=[phase])
    status,day=_run_phase(np.array([.02,0,0,0,0]),np.array([1,0,0,0,0],dtype=bool),phase,cfg)
    assert status=="time_limit"
    assert day==5


def test_daily_reference_modes():
    phase={"target_pct":20,"max_days":3,"min_days":0,"min_profit_day_pct":0}
    daily=np.array([.1,-.05,0])
    a=conf(phases=[phase],daily_loss_pct=4,daily_loss_basis="previous_close")
    b=conf(phases=[phase],daily_loss_pct=4,daily_loss_basis="initial")
    assert _run_phase(daily,np.ones(3,dtype=bool),phase,a)[0]=="breached"
    assert _run_phase(daily,np.ones(3,dtype=bool),phase,b)[0]=="time_limit"


def test_trailing_eod_and_lock_at_initial():
    phase={"target_pct":50,"max_days":3,"min_days":0,"min_profit_day_pct":0}
    daily=np.array([.15,-.15,0])  # breached the locked-at-initial trailing floor
    trailing=conf(phases=[phase],daily_loss_pct=0,total_loss_pct=10,total_loss_mode="trailing_eod",trailing_lock_initial=True)
    static=conf(phases=[phase],daily_loss_pct=0,total_loss_pct=10,total_loss_mode="static")
    assert _run_phase(daily,np.ones(3,dtype=bool),phase,trailing)[0]=="breached"
    assert _run_phase(daily,np.ones(3,dtype=bool),phase,static)[0]=="time_limit"


def test_best_day_consistency_by_total_and_target():
    phase={"target_pct":8,"max_days":5,"min_days":0,"min_profit_day_pct":0}
    values=np.array([.08,0,.01,.01,.01])
    cfg=conf(phases=[phase],consistency_mode="best_day_total",consistency_max_pct=50)
    assert _run_phase(values,np.ones(5,dtype=bool),phase,cfg)[0]=="time_limit"
    cfg=conf(phases=[phase],consistency_mode="best_day_target",consistency_max_pct=50)
    assert _run_phase(values,np.ones(5,dtype=bool),phase,cfg)[0]=="time_limit"


def test_many_positive_paths_pass_two_stages_and_time_cap_rejects():
    days=np.full(25,.02,dtype=float)
    active=np.ones(25,dtype=bool)
    cfg=conf(enabled=True,phases=[{"target_pct":8,"max_days":30,"min_days":0},
                                  {"target_pct":5,"max_days":30,"min_days":0}],
             simulations=64,pass_day_percentile=20,max_pass_days_percentile=4,
             min_pass_rate_pct=50)
    result=simulate_funding(days,active,cfg,21)
    assert result["pass_rate_pct"]==100
    assert result["p20_days"]>=7
    assert result["min_rate_pass"]
    assert not result["days_limit_pass"]
    assert result["pass_within_day_cap_pct"]==0
    assert not result["eligible"]


def test_threshold_zero_only_measures_even_zero_winners():
    cfg=conf(enabled=True,phases=[{"target_pct":20,"max_days":15,"min_days":0}],
             simulations=64,min_pass_rate_pct=0,max_pass_days_percentile=0)
    result=simulate_funding(np.full(12,-.02),np.ones(12,bool),cfg,5)
    assert result["pass_rate_pct"]==0
    assert result["eligible"]
    assert result["p20_days"] is None


def test_max_pass_rate_and_time_scoring_uses_config():
    cfg=conf(enabled=True,phases=[{"target_pct":4,"max_days":30,"min_days":0}],
             simulations=64,pass_day_percentile=20)
    r=np.full(20,2.)
    dates=np.arange(1,21,dtype=np.int32)
    score,data=objective_score("funding_pass_rate",r,dates,dates,1.,"fixed",5000.,3.,10.,seed=1,funding_config=cfg)
    assert np.isfinite(score)
    assert data["funding_evaluation_is"] is not None
    assert data["funding_evaluation_is"]["p20_days"] is not None
    assert data["funding_pass_rate_estimated_pct"]==data["funding_evaluation_is"]["pass_rate_pct"]
