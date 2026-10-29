"""Real job and candidate trace regression checks; no invented trades or progress."""
import time
import numpy as np
import pytest
from execution_jobs import ResearchJobs
from engine_advanced import run_advanced
from preflight import preflight
from test_advanced import config,synthetic_bars


def test_jobs_report_real_progress_and_final_result():
    jobs=ResearchJobs(max_queued=1)
    def loader(path):
        return {"path":str(path)}
    def run(frame,cfg,on_progress=None):
        for i in (2,4,6):
            on_progress(i,6,"explorando")
        on_progress(1,2,"validando")
        return {"tested":6,"accepted":1,"candidates":[{"id":"candidate-1"}]}
    submitted=jobs.launch("fake.csv",{"dataset_id":"test","candidates":6},loader,run)
    job_id=submitted["id"]
    assert submitted["status"] in ("queued","running","completed")
    for _ in range(200):
        state=jobs.status(job_id)
        if state["status"]=="completed":
            break
        time.sleep(.01)
    assert state["status"]=="completed"
    assert state["percent"]==100
    assert state["checked"]==6
    result=jobs.result(job_id)
    assert result["tested"]==6
    assert result["candidates"][0]["id"]=="candidate-1"


def test_job_error_does_not_report_fake_success():
    jobs=ResearchJobs()
    def broken(frame,config,on_progress=None):
        raise ValueError("No hay datos OHLC válidos")
    job=jobs.launch("data.csv",{"dataset_id":"a","candidates":10},lambda p:None,broken)
    for _ in range(200):
        state=jobs.status(job["id"])
        if state["status"]=="failed":break
        time.sleep(.01)
    assert state["status"]=="failed"
    assert state["percent"]<100
    assert jobs.result(job["id"]) is None


def test_ohlc_preflight_measures_true_atr_and_frequency():
    frame=synthetic_bars(2600)
    profile=preflight(frame,config(timeframes=["5m"],families=["ema_cross","rsi_reversion"],rr=1.))
    info=profile["timeframes"][0]
    assert info["rows"]>=400
    assert 0<info["atr_price_units"]["p05"]<=info["atr_price_units"]["median"]<=info["atr_price_units"]["p95"]
    assert info["daily_bars_max"]>=info["daily_bars_median"]
    assert info["signal_samples"]


def test_ledger_reconciles_net_result_and_uses_actual_timestamps():
    report=run_advanced(synthetic_bars(2750),config(candidates=12))
    assert report["tested"]>0
    assert len(report["candidates"])<=12
    for c in report["candidates"]:
        ledger=c["ledger"]
        assert c["ledger_scope"]=="OOS"
        assert len(ledger)==c["out_of_sample"]["trades"]
        assert c["market_chart"]
        assert all(x["entry_time"]<=x["exit_time"] for x in ledger)
        assert all(np.isfinite(x["entry_price"]) and np.isfinite(x["exit_price"]) for x in ledger)
        pnl=sum(x["pnl_usd"] for x in ledger)
        net_return=c["out_of_sample"]["net_return_pct"]*5000/100.
        assert abs(pnl-net_return)<2.0


def test_default_quality_filters_historical_no_fake_pass():
    result=run_advanced(synthetic_bars(2600),config(candidates=12,
        quality={"min_sharpe":4,"max_drawdown_pct":.00001,"min_win_rate_pct":99,"min_dsr":.95}))
    assert result["tested"]>0
    assert result["total_shortlist"]<=12
    assert all((c["quality_is"]["sharpe"]>=4 and not c["quality_is"]["max_drawdown_pct"]> .00001) or not c["accepted"] for c in result["candidates"])
    assert all("quality_is" in c for c in result["candidates"])
