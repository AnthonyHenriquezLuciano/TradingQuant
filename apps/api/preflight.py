"""Point-in-time safe profile of imported OHLC data and configuration conflicts.

These are DESCRIPTIVE historical limits. They cannot guarantee the true upper
bound of a generator whose parameters and order execution may vary.
"""
from __future__ import annotations
import numpy as np
from engine import resample,atr_wilder,make_signals

def preflight(frame, cfg):
    timeframes=cfg.get("timeframes") or [cfg.get("timeframe","5m")]
    info=[]
    warnings=[]
    for timeframe in timeframes:
        bars=resample(frame,timeframe)
        hi=bars["high"].to_numpy()
        lo=bars["low"].to_numpy()
        close=bars["close"].to_numpy()
        atr=atr_wilder(hi,lo,close,14)
        atr=atr[np.isfinite(atr)&(atr>0)]
        if len(atr)<30:
            raise ValueError("Histórico insuficiente para estimar el ATR.")
        d=np.asarray([x.date().toordinal() for x in bars["timestamp"].to_list()],dtype=np.int64)
        _,perday=np.unique(d,return_counts=True)
        family_set=set(cfg.get("families") or [])
        samples=[]
        for name,kind,a,b in (("ema_cross",0,14,40),
                              ("rsi_reversion",1,14,30),
                              ("breakout",2,0,20)):
            if name in family_set:
                signals=make_signals(kind,a,b,close,hi,lo)
                _,counts=np.unique(d[signals!=0],return_counts=True)
                samples.append({"family":name,
                                "max_signals_day":int(np.max(counts)) if len(counts) else 0,
                                "median_signals_active_day":float(np.median(counts)) if len(counts) else 0})
        quantiles=np.percentile(atr,[5,25,50,75,95])
        info.append({
            "timeframe":timeframe,"rows":len(bars),"days":len(perday),
            "atr_period":14,
            "atr_price_units":{"p05":round(float(quantiles[0]),8),
                               "p25":round(float(quantiles[1]),8),
                               "median":round(float(quantiles[2]),8),
                               "p75":round(float(quantiles[3]),8),
                               "p95":round(float(quantiles[4]),8)},
            "atr_pct_of_price_median":round(float(100*quantiles[2]/np.median(close)),5),
            "daily_bars_max":int(np.max(perday)),
            "daily_bars_median":float(np.median(perday)),
            "signal_samples":samples,
            "price_min":float(np.min(lo)),"price_max":float(np.max(hi)),
        })
        cap=cfg.get("capital") or {}
        maximum=int(cap.get("max_trades_per_day",0))
        if maximum>0 and samples and max(x["max_signals_day"] for x in samples)<maximum:
            warnings.append(f"{timeframe.upper()}: en el muestreo preliminar ninguna familia produjo {maximum} señales diarias. La regla puede ser redundante; parámetros alternativos podrían producir más.")
        if cap.get("max_bars_in_trade",0)>0 and maximum>int(np.max(perday)):
            warnings.append(f"{timeframe.upper()}: {maximum} operaciones por día exceden las {int(np.max(perday))} barras diarias disponibles (cota teórica sin posiciones superpuestas).")
    cap=cfg.get("capital") or {}
    riskrules=cap.get("risk_rules") or {}
    advanced=cfg.get("advanced_modifiers") or {}
    quality=cfg.get("quality") or {}
    funding=cfg.get("funding") or {}
    if cap.get("max_trades_per_day",0)>0 and quality.get("max_trades_per_day",0)>=cap["max_trades_per_day"]:
        warnings.append("Filtro: máximo de trades por día ≥ límite operativo de Gestión de capital; el filtro no agrega restricciones.")
    if advanced.get("fixed_rr_enabled"):
        warnings.append("R:R fijo avanzado sustituye el Take Profit configurado en Gestión de capital; ese rango TP no se explora mientras esté activo.")
    if advanced.get("be_enabled") and cap.get("breakeven_enabled"):
        warnings.append("Break-even avanzado tiene prioridad sobre el básico; desactiva uno para evitar duplicidad.")
    if advanced.get("trailing_enabled") and cap.get("trailing_enabled"):
        warnings.append("Trailing avanzado tiene prioridad sobre el básico; desactiva uno para simplificar.")
    if funding.get("enabled") and (funding.get("daily_loss_pct")!=cfg.get("prop_daily_pct") or funding.get("total_loss_pct")!=cfg.get("prop_max_pct")):
        warnings.append("Gestión de capital usa límites operativos; Fondeo simula límites de evaluación diferentes. Ambos pueden coexistir, pero se aplican en etapas distintas.")
    if cfg.get("rr") is not None or cfg.get("atr_multiplier") is not None:
        warnings.append("Los campos heredados 'rr' y 'atr_multiplier' no controlan el motor actual. La salida se configura exclusivamente en Gestión de capital y Avanzado.")
    return {"dataset_id":cfg.get("dataset_id"),"timeframes":info,
            "warnings":warnings,"historical_only":True,
            "message":"Percentiles históricos observados, no predicciones ni límites matemáticos garantizados. Se usa el CSV aportado."}
