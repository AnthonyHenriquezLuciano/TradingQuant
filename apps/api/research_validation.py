"""Research controls: validations, execution costs, realized Sharpe and DSR.

Quality is assessed on the IS portion first and independently on untouched OOS.
DSR is an approximate Bailey/Lopez-de-Prado adjustment for the observed number
of strategy trials on the *same symbol*, not a claim of independent discoveries.
"""
from __future__ import annotations
from statistics import NormalDist
import math
import numpy as np
from optimization_objectives import _daily_returns

DEFAULT_QUALITY={
 "min_sharpe":0.,"max_drawdown_pct":100.,"min_win_rate_pct":0.,"min_dsr":0.,
 "min_trades":0,"min_frequency_unit":"auto","max_trades_per_day":0,
}
DEFAULT_WALK_FORWARD={
 "enabled":False,"test_fraction":4,"mode":"pure","top_n":20,
 "min_efficiency":.5,"min_pass_rate_pct":60.,"min_oos_sharpe":.5,
 "rolling_windows":4,"min_training_bars":250,
}
DEFAULT_MULTIVERSE={
 "enabled":False,"universes":100,"mix":"balanced","top_n":3,"regimes":3,
 "validate_fat_tails":True,"min_score":60.,"max_robust_drawdown_pct":30.,
}
DEFAULT_COSTS={
 "template":"generic","auto_mt5":False,"selected_symbol":"XAUUSD",
 "use_in_backtest":False,"instruments":[],
}


def _bounded(cfg,fields):
    for name,low,high,integer in fields:
        n=cfg[name]
        if isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) or n<low or n>high or integer and int(n)!=n:
            raise ValueError("Parámetro de investigación inválido: "+name)


def validate_quality(raw=None):
    if raw is not None and not isinstance(raw,dict):
        raise ValueError("Filtro de calidad inválido.")
    c={**DEFAULT_QUALITY,**(raw or {})}
    _bounded(c,[("min_sharpe",0,4,False),("max_drawdown_pct",0,100,False),
                ("min_win_rate_pct",0,100,False),("min_dsr",0,1,False),
                ("min_trades",0,50000,True),("max_trades_per_day",0,10000,True)])
    if c["min_frequency_unit"] not in ("auto","day","week","month"):
        raise ValueError("Unidad de frecuencia inválida.")
    return c


def validate_walkforward(raw=None):
    if raw is not None and not isinstance(raw,dict):
        raise ValueError("Walk-forward inválido.")
    c={**DEFAULT_WALK_FORWARD,**(raw or {})}
    if not isinstance(c["enabled"],bool) or c["test_fraction"] not in (2,3,4,6,8,12) or c["mode"] not in ("pure","reopt"):
        raise ValueError("Configuración walk-forward inválida.")
    _bounded(c,[("top_n",1,30,True),("rolling_windows",2,12,True),
                ("min_training_bars",100,100000,True),("min_efficiency",0,3,False),
                ("min_pass_rate_pct",0,100,False),("min_oos_sharpe",-5,10,False)])
    return c


def validate_multiverse(raw=None):
    if raw is not None and not isinstance(raw,dict):
        raise ValueError("Multiverso inválido.")
    c={**DEFAULT_MULTIVERSE,**(raw or {})}
    if not isinstance(c["enabled"],bool) or c["mix"] not in ("balanced","conservative","stress") or c["universes"] not in (50,100,250,500,1000) or c["regimes"] not in (1,2,3) or not isinstance(c["validate_fat_tails"],bool):
        raise ValueError("Multiverso: parámetro inválido.")
    _bounded(c,[("top_n",1,10,True),("min_score",0,100,False),
                ("max_robust_drawdown_pct",1,100,False)])
    return c


def validate_costs(raw=None):
    if raw is not None and not isinstance(raw,dict):
        raise ValueError("Costes inválidos.")
    c={**DEFAULT_COSTS,**(raw or {})}
    if c["template"] not in ("generic","custom") or not isinstance(c["use_in_backtest"],bool) or not isinstance(c["auto_mt5"],bool):
        raise ValueError("Configuración automática MT5 inválida.")
    if not isinstance(c["instruments"],list) or len(c["instruments"])>100:
        raise ValueError("Máximo 100 instrumentos en el catálogo.")
    seen=set()
    for row in c["instruments"]:
        if not isinstance(row,dict) or not isinstance(row.get("symbol"),str) or not 1<len(row["symbol"])<=90:
            raise ValueError("Símbolo de costes inválido.")
        sym=row["symbol"].upper()
        if sym in seen:
            raise ValueError("Símbolo de costes repetido.")
        seen.add(sym)
        for key in ("spread_pips","commission_roundtrip_usd","slippage_pips",
                    "swap_long_usd","swap_short_usd","pip_size","contract_size",
                    "quote_to_usd","hold_days_estimate"):
            v=row.get(key)
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or abs(v)>1e9:
                raise ValueError("Especificación de costes inválida: "+key)
            if key not in ("swap_long_usd","swap_short_usd") and v<0:
                raise ValueError("Coste negativo inválido: "+key)
        if c["use_in_backtest"] and (row["pip_size"]<=0 or row["contract_size"]<=0 or row["quote_to_usd"]<=0):
            raise ValueError("El catálogo activo necesita contrato, pip y conversión válidos.")
    return c


def estimated_roundtrip_bps(costs:dict, symbol:str, reference_price:float, side:int, fallback:float):
    """Estimate cost per notional from user-provided, *unverified* contract specs.

    Spread/slippage expressed in quote price units, commission & swaps as USD
    per lot; returns comparable all-in round trip bps for the current candidate.
    """
    if not costs["use_in_backtest"]:
        return float(fallback)
    row=next((r for r in costs["instruments"] if r["symbol"].upper()==symbol.upper()),None)
    if row is None:
        raise ValueError("Instrumento sin especificaciones de costes: "+symbol)
    if reference_price<=0 or not math.isfinite(reference_price):
        raise ValueError("Precio de referencia inválido para convertir los costes.")
    notional=reference_price*row["contract_size"]*row["quote_to_usd"]
    price_cost=(row["spread_pips"]+2*row["slippage_pips"])*row["pip_size"]
    quote_usd=price_cost*row["contract_size"]*row["quote_to_usd"]
    financing=row["swap_long_usd"] if side>0 else row["swap_short_usd"]
    cash=quote_usd+row["commission_roundtrip_usd"]-financing*row["hold_days_estimate"]
    return max(0.,cash/notional*1e4)


def realized_quality(r,days,observed_days,risk,sizing,metrics,trial_count=1):
    """Realized daily Sharpe/DSR and trade frequency, no inferred floating equity."""
    r=np.asarray(r,dtype=float)
    days=np.asarray(days,dtype=np.int32)
    unique=np.unique(np.asarray(observed_days,dtype=np.int32))
    daily=_daily_returns(r,days,unique,risk,sizing)
    n=len(daily)
    sharpe=0.
    dsr=0.
    if n>3 and r.size:
        mu=float(np.mean(daily))
        sigma=float(np.std(daily,ddof=1))
        if sigma>1e-12:
            sr=mu/sigma
            sharpe=sr*np.sqrt(252.)
            centered=(daily-mu)/sigma
            skew=float(np.mean(centered**3))
            kurt=float(np.mean(centered**4))
            trials=max(1,int(trial_count))
            if trials>1:
                norm=NormalDist()
                expected_max=(1-.5772156649)*norm.inv_cdf(1.-1./trials)+.5772156649*norm.inv_cdf(1.-1./(trials*math.e))
            else:
                expected_max=0.
            error=math.sqrt(max(1e-12,(1.-skew*sr+(kurt-1.)*sr*sr/4.)/(n-1.)))
            dsr=NormalDist().cdf((sr-expected_max)/error)
    duration=max(1,n)
    return {
      "sharpe":round(float(sharpe),5),
      "dsr":round(float(dsr),5),"dsr_trials":int(trial_count),
      "trades":int(r.size),"win_rate_pct":float(np.mean(r>0)*100.) if r.size else 0.,
      "max_drawdown_pct":float(metrics["max_drawdown_pct"]),
      "trades_per_day":float(r.size/duration),
      "max_trades_observed_day":int(np.unique(days,return_counts=True)[1].max()) if len(days) else 0,
      "trades_per_week":float(r.size/(duration/5.)),
      "trades_per_month":float(r.size/(duration/21.)),
      "observed_days":duration,
      "metric_type":"realized_balance_close_only",
    }


def evaluate_quality(info, config):
    c=validate_quality(config)
    reasons=[]
    if c["min_sharpe"] and info["sharpe"]<c["min_sharpe"]:
        reasons.append("Sharpe inferior al mínimo")
    if info["max_drawdown_pct"]>c["max_drawdown_pct"]+1e-9:
        reasons.append("Drawdown superior al máximo")
    if c["min_win_rate_pct"] and info["win_rate_pct"]<c["min_win_rate_pct"]:
        reasons.append("Win Rate inferior al mínimo")
    if c["min_dsr"] and info["dsr"]<c["min_dsr"]:
        reasons.append("DSR inferior al umbral anti-suerte")
    frequency=c["min_frequency_unit"]
    if frequency=="auto":
        if c["min_trades"] and info["trades"]<c["min_trades"]:
            reasons.append("Número de operaciones inferior al mínimo")
    else:
        key={"day":"trades_per_day","week":"trades_per_week","month":"trades_per_month"}[frequency]
        if info[key]<c["min_trades"]:
            reasons.append("Frecuencia de operaciones inferior al mínimo")
    if c["max_trades_per_day"] and info["max_trades_observed_day"]>c["max_trades_per_day"]:
        reasons.append("Exceso de operaciones por día")
    return reasons
