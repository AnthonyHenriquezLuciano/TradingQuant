"""Configurable, realized-equity prop evaluation Monte Carlo.

IMPORTANT: days are based on trades *closed*, not opened. Tick data, unrealized
equity, intraday margin, news and real execution conditions are not available.
Never describe this as a broker-accurate challenge pass probability.
"""
from __future__ import annotations
import math
import numpy as np

DEFAULT_FUNDING = {
    "enabled": False,
    "preset": "custom",
    "phases": [{"target_pct": 8., "max_days": 120, "min_days": 0, "min_profit_day_pct": 0.},
               {"target_pct": 5., "max_days": 120, "min_days": 0, "min_profit_day_pct": 0.}],
    "daily_loss_pct": 3.,
    "daily_loss_basis": "previous_close",
    "total_loss_pct": 10.,
    "total_loss_mode": "static",
    "trailing_lock_initial": True,
    "consistency_mode": "none",
    "consistency_max_pct": 50.,
    "min_pass_rate_pct": 0.,
    "pass_day_percentile": 20,
    "max_pass_days_percentile": 0,
    "simulations": 128,
    "bootstrap_block_days": 1,
}
BASIS = ("previous_close", "initial")
TOTAL_MODES = ("static", "trailing_eod")
CONSISTENCY = ("none", "best_day_total", "best_day_target")


def validate_funding(value: dict | None) -> dict:
    if value is not None and not isinstance(value, dict):
        raise ValueError("La configuración de fondeo debe ser un objeto.")
    cfg={**DEFAULT_FUNDING, **(value or {})}
    if not isinstance(cfg["enabled"], bool):
        raise ValueError("Fondeo.enabled debe ser booleano.")
    phases=cfg["phases"]
    if not isinstance(phases,list) or not 1 <= len(phases) <= 3:
        raise ValueError("Configura entre 1 y 3 fases.")
    checked=[]
    for j,phase in enumerate(phases):
        if not isinstance(phase,dict):
            raise ValueError("Cada fase debe contener sus reglas.")
        data={"target_pct":8., "max_days":120,"min_days":0,"min_profit_day_pct":0.,**phase}
        for key,lower,upper in (("target_pct",.1,50),("max_days",1,730),
                                ("min_days",0,365),("min_profit_day_pct",0,20)):
            val=data[key]
            if not isinstance(val,(int,float)) or isinstance(val,bool) or not math.isfinite(val) or not lower<=val<=upper:
                raise ValueError(f"Fase {j+1}: {key} fuera de rango.")
        if any(int(data[x])!=data[x] for x in ("max_days","min_days")):
            raise ValueError("Los días de cada fase deben ser enteros.")
        if data["min_days"]>data["max_days"]:
            raise ValueError("Los días mínimos no pueden superar el máximo de la fase.")
        checked.append(data)
    cfg["phases"]=checked
    if cfg["daily_loss_basis"] not in BASIS or cfg["total_loss_mode"] not in TOTAL_MODES or cfg["consistency_mode"] not in CONSISTENCY:
        raise ValueError("Modelo de drawdown o consistencia desconocido.")
    if not isinstance(cfg["trailing_lock_initial"],bool):
        raise ValueError("Bloqueo del trailing inválido.")
    for key,lo,hi in (("daily_loss_pct",0,50),("total_loss_pct",.1,50),
                      ("consistency_max_pct",1,100),("min_pass_rate_pct",0,100),
                      ("max_pass_days_percentile",0,2190),("simulations",32,2000),
                      ("bootstrap_block_days",1,20)):
        val=cfg[key]
        if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val) or not lo<=val<=hi:
            raise ValueError(f"Valor de fondeo inválido: {key}.")
    for k in ("simulations","bootstrap_block_days","pass_day_percentile","max_pass_days_percentile"):
        if cfg[k]!=int(cfg[k]):
            raise ValueError("Los contadores y percentiles deben ser enteros.")
    if cfg["pass_day_percentile"] not in (10,20,25,50,75,80,90,95):
        raise ValueError("Percentil de días no admitido.")
    return cfg


def _sample_blocks(rng:np.random.Generator, returns:np.ndarray, activity:np.ndarray, horizon:int, block:int):
    """Contiguous block bootstrap keeps some clustering and idle days."""
    n=len(returns)
    result_r=np.empty(horizon,dtype=float)
    result_active=np.empty(horizon,dtype=bool)
    loc=0
    while loc<horizon:
        start=int(rng.integers(0,n))
        length=min(block,horizon-loc,n-start)
        result_r[loc:loc+length]=returns[start:start+length]
        result_active[loc:loc+length]=activity[start:start+length]
        loc+=length
    return result_r,result_active


def _run_phase(
    returns:np.ndarray,active:np.ndarray,phase:dict,cfg:dict
) -> tuple[str,int]:
    equity=1.
    peak_eod=1.
    best_day_profit=0.
    profitable_days=0
    for day,(ret,traded) in enumerate(zip(returns,active),start=1):
        before=equity
        equity=max(0.,before*(1.+float(ret)))
        # Daily risk is normalized to initial balance; previous_close lets the
        # floor float with previous realized balance. Same-day intrabar breaches
        # cannot be observed.
        daily_floor=(before if cfg["daily_loss_basis"]=="previous_close" else 1.)-cfg["daily_loss_pct"]/100.
        total_floor=(1.-cfg["total_loss_pct"]/100. if cfg["total_loss_mode"]=="static"
                     else peak_eod-cfg["total_loss_pct"]/100.)
        if cfg["total_loss_mode"]=="trailing_eod" and cfg["trailing_lock_initial"]:
            total_floor=min(total_floor,1.)
        if (cfg["daily_loss_pct"]>0 and equity<=daily_floor+1e-12) or equity<=total_floor+1e-12:
            return "breached",day
        profit=equity-before
        best_day_profit=max(best_day_profit,profit)
        if traded:
            min_gain=phase["min_profit_day_pct"]/100.
            if phase["min_profit_day_pct"]==0 or profit>=min_gain-1e-12:
                profitable_days+=1
        if cfg["total_loss_mode"]=="trailing_eod":
            peak_eod=max(peak_eod,equity)
        if equity >= 1.+phase["target_pct"]/100. and profitable_days>=phase["min_days"]:
            if cfg["consistency_mode"]=="best_day_total":
                if (equity-1.)<=0 or best_day_profit/(equity-1.)*100.>cfg["consistency_max_pct"]+1e-12:
                    continue
            elif cfg["consistency_mode"]=="best_day_target":
                # Topstep-like: a dominating day raises required total profit,
                # rather than failing immediately.
                required=max(phase["target_pct"]/100.,best_day_profit/(cfg["consistency_max_pct"]/100.))
                if equity-1.+1e-12<required:
                    continue
            return "passed",day
    return "time_limit",len(returns)


def simulate_funding(
    daily_returns:np.ndarray,active_days:np.ndarray,cfg:dict | None,seed:int=0
) -> dict:
    """Independent phase evaluations from IS-only completed daily returns.

    Passing times exclude failed paths. The unconditional fraction of ALL
    attempts passed by the selected day cap is also reported to avoid a
    misleading P20 among only the rare successes.
    """
    cfg=validate_funding(cfg)
    x=np.asarray(daily_returns,dtype=float)
    act=np.asarray(active_days,dtype=bool)
    if x.ndim!=1 or act.shape!=x.shape or not np.all(np.isfinite(x)):
        raise ValueError("Retornos diarios y actividad deben tener idéntica forma.")
    total_horizon=sum(p["max_days"] for p in cfg["phases"])
    base={"pass_rate_pct":0.,"p20_days":None,"p50_days":None,"p80_days":None,
          "selected_percentile_days":None,"mean_days_success":None,
          "pass_within_day_cap_pct":0.,"days_limit_pass":False,
          "min_rate_pass":False,"eligible":False,
          "phase_pass_rate_pct":[0.]*len(cfg["phases"]),
          "fail_reasons":{"breached":0,"time_limit":0},
          "successful_paths":0,"simulations":int(cfg["simulations"]),
          "estimated":True}
    if x.size<10 or not np.any(act):
        base["insufficient_history"]=True
        return base
    rng=np.random.default_rng(seed)
    successful_days=[]
    stage_reached=np.zeros(len(cfg["phases"]),dtype=np.int64)
    failures={"breached":0,"time_limit":0}
    for _ in range(int(cfg["simulations"])):
        total_days=0
        ok=True
        for index,phase in enumerate(cfg["phases"]):
            sample,activity=_sample_blocks(rng,x,act,int(phase["max_days"]),int(cfg["bootstrap_block_days"]))
            status,used=_run_phase(sample,activity,phase,cfg)
            total_days+=used
            if status=="passed":
                stage_reached[index]+=1
            else:
                failures[status]+=1
                ok=False
                break
        if ok:
            successful_days.append(total_days)
    n=int(cfg["simulations"])
    count=len(successful_days)
    rate=100.*count/n
    base.update(pass_rate_pct=round(rate,2),successful_paths=count,
                phase_pass_rate_pct=[round(100.*k/n,2) for k in stage_reached],
                fail_reasons=failures,
                min_rate_pass=rate+1e-9>=cfg["min_pass_rate_pct"])
    if count:
        base["p20_days"]=float(np.percentile(successful_days,20))
        base["p50_days"]=float(np.percentile(successful_days,50))
        base["p80_days"]=float(np.percentile(successful_days,80))
        selected=float(np.percentile(successful_days,cfg["pass_day_percentile"]))
        base["selected_percentile_days"]=round(selected,2)
        base["mean_days_success"]=round(float(np.mean(successful_days)),2)
    cap=cfg["max_pass_days_percentile"]
    base["days_limit_pass"]=bool(cap==0 or (count and base["selected_percentile_days"]<=cap))
    base["pass_within_day_cap_pct"]=round(
        (100.*sum(1 for n_days in successful_days if n_days<=cap)/n) if cap else rate,2)
    base["eligible"]=bool(base["min_rate_pass"] and base["days_limit_pass"] and count)
    base["insufficient_history"]=False
    return base
