"""Deterministic objective scoring: IS-only, annualization, funding proxy and ranking."""
import numpy as np
import pytest

from optimization_objectives import (
    OBJECTIVES, FUNDING_PHASE_TARGETS, funding_pass_rate,
    objective_score, reproducible_seed, validate_objective,
)
from engine_advanced import run_advanced
from test_advanced import config, synthetic_bars


def score(metric, r, days=None, dates=None, risk=1., sizing="fixed", seed=4):
    outcomes=np.asarray(r,dtype=np.float64)
    exit_days=np.asarray(days if days is not None else list(range(1,len(r)+1)),dtype=np.int32)
    observed=np.asarray(dates if dates is not None else list(range(1,len(r)+1)),dtype=np.int32)
    return objective_score(metric,outcomes,exit_days,observed,risk,sizing,5000.,3.,10.,seed)


@pytest.mark.parametrize("metric",OBJECTIVES)
def test_each_objective_produces_finite_score(metric):
    s,data=score(metric,[1.,1.,-.4,.7,-.3,.5,0.,.7,-.2,1.],dates=list(range(1,21)))
    assert np.isfinite(s)
    assert data["objective_score"]==pytest.approx(round(s,6))
    assert data["observed_trading_days"]==20


def test_net_profit_is_in_usd_and_respects_fixed_sizing():
    result,details=score("net_profit",[1.,1.,-1.])
    assert result==pytest.approx(50.)
    assert details["pnl_usd"]==50.


def test_win_rate_and_mean_expectancy():
    w,_=score("win_rate",[1.,1.,-1.])
    e,_=score("expectancy",[1.,1.,-1.])
    assert w==pytest.approx(200./3.)
    assert e==pytest.approx(50./3.)


def test_minimum_drawdown_prioritizes_smaller_loss():
    a,_=score("min_drawdown",[1.,-.5,1.])
    b,_=score("min_drawdown",[1.,-2.,1.])
    assert a>b


def test_sharpe_uses_no_trade_days_in_252_convention():
    r=np.array([1.,-1.,1.,1.])
    a,_=score("sharpe",r,days=[1,2,3,4],dates=[1,2,3,4])
    b,_=score("sharpe",r,days=[1,2,3,4],dates=list(range(1,21)))
    assert a!=b


def test_funding_two_phases_pass_and_fail_deterministically():
    positive=np.full(15,.02,dtype=np.float64)
    negative=np.full(15,-.02,dtype=np.float64)
    assert funding_pass_rate(positive,3.,10.,42)==pytest.approx(100.)
    assert funding_pass_rate(negative,3.,10.,42)==pytest.approx(0.)
    assert FUNDING_PHASE_TARGETS==(8.,5.)


def test_funding_requires_nontrivial_is_days_and_is_reproducible():
    assert funding_pass_rate(np.full(9,.01),3.,10.,42)==0.
    r=np.tile([.02,-.025,.008,.002],8).astype(float)
    a=funding_pass_rate(r,3.,10.,seed=5)
    b=funding_pass_rate(r,3.,10.,seed=5)
    assert a==b and 0<=a<=100
    assert reproducible_seed((0,5,30),1,(1.,1.))==reproducible_seed((0,5,30),1,(1.,1.))


def test_invalid_objective_rejected():
    with pytest.raises(ValueError,match="Objetivo"):
        validate_objective("inexistent")


@pytest.mark.parametrize("objective",["balanced","sharpe","profit_factor","funding_pass_rate"])
def test_objective_propagated_through_engine(objective):
    # One sample per object, full OOS remains unused during candidate selection.
    result=run_advanced(synthetic_bars(2700),config(optimization_objective=objective,candidates=12))
    assert result["optimization_objective"]==objective
    for cand in result["candidates"]:
        assert cand["optimization_objective"]==objective
        assert "optimization_score" in cand
        assert "optimization_metrics_is" in cand
        assert "out_of_sample" in cand
