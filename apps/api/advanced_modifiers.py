"""Validated advanced execution rules for bar-close signal strategies.

Runtime is backed by engine_advanced_orders.simulate_advanced_orders (Numba).
Defaults preserve the classic portfolio simulator. Composite orders reserve all
configured legs within one capped overall trade risk. No margin/ticks modeled.
"""
from __future__ import annotations
import math
from copy import deepcopy

DEFAULT_ADVANCED = {
 "entry_modes":["market"],"stop_lookback":5,"order_expiry_bars":3,"limit_offset_atr":.5,
 "fixed_rr_enabled":False,"fixed_rr":2.,
 "variable_risk_enabled":False,"variable_risk_mode":"anti_martingale",
 "risk_multiplier":1.5,"risk_max_levels":5,"risk_reset_on_win":True,
 "be_enabled":False,"be_unit":"atr","be_trigger":1.,"be_offset_pips":0.,"pip_size":0.,
 "trailing_enabled":False,"trailing_activation_unit":"atr","trailing_activation":1.5,
 "trailing_distance_unit":"atr","trailing_distance":1.,
 "dca_enabled":False,"dca_levels":3,"dca_size_multiplier":1.,
 "dca_spacing_unit":"atr","dca_spacing":1.,
 "pyramid_enabled":False,"pyramid_levels":3,"pyramid_size_multiplier":1.,
 "pyramid_spacing_unit":"atr","pyramid_spacing":1.,"sl_tp_from_average":True,
}
ENTRY_CODES={"market":0,"stop":1,"limit":2}
UNIT_CODES={"atr":0,"r":1,"percent":2}


def validate_advanced(raw:dict | None) -> dict:
    if raw is not None and not isinstance(raw,dict):
        raise ValueError("Avanzado debe ser un objeto.")
    cfg={**deepcopy(DEFAULT_ADVANCED),**(raw or {})}
    entry=cfg["entry_modes"]
    if not isinstance(entry,list) or not entry or len(entry)>3 or len(set(entry))!=len(entry) or any(x not in ENTRY_CODES for x in entry):
        raise ValueError("Selecciona uno o más tipos de entrada válidos.")
    if cfg["variable_risk_mode"] not in ("anti_martingale","martingale"):
        raise ValueError("Modo de riesgo variable inválido.")
    for key in ("be_unit","trailing_activation_unit","trailing_distance_unit","dca_spacing_unit","pyramid_spacing_unit"):
        if cfg[key] not in UNIT_CODES:
            raise ValueError("Unidad no reconocida: "+key)
    boolean_fields=("fixed_rr_enabled","variable_risk_enabled","risk_reset_on_win","be_enabled","trailing_enabled","dca_enabled","pyramid_enabled","sl_tp_from_average")
    for key in boolean_fields:
        if not isinstance(cfg[key],bool):
            raise ValueError("Modificador booleano inválido: "+key)
    limits={
      "stop_lookback":(2,100,True),"order_expiry_bars":(1,100,True),
      "limit_offset_atr":(.1,10,False),"fixed_rr":(.1,20,False),
      "risk_multiplier":(1.,3.,False),"risk_max_levels":(1,10,True),
      "be_trigger":(.05,20,False),"be_offset_pips":(0,1000,False),
      "pip_size":(0,1000,False),"trailing_activation":(.05,20,False),
      "trailing_distance":(.05,20,False),
      "dca_levels":(2,8,True),"dca_size_multiplier":(.25,3,False),
      "dca_spacing":(.1,10,False),"pyramid_levels":(2,8,True),
      "pyramid_size_multiplier":(.25,3,False),"pyramid_spacing":(.1,10,False)
    }
    for key,(low,high,integer) in limits.items():
        n=cfg[key]
        if isinstance(n,bool) or not isinstance(n,(float,int)) or not math.isfinite(n) or n<low or n>high or integer and int(n)!=n:
            raise ValueError("Parámetro avanzado fuera de rango: "+key)
    if cfg["be_enabled"] and cfg["be_offset_pips"]>0 and cfg["pip_size"]<=0:
        raise ValueError("El offset del break-even requiere el tamaño real de pip del instrumento.")
    return cfg


def is_active(cfg:dict) -> bool:
    return cfg["entry_modes"]!=["market"] or any(cfg[key] for key in
       ("fixed_rr_enabled","variable_risk_enabled","be_enabled","trailing_enabled","dca_enabled","pyramid_enabled"))


def execution_arguments(cfg:dict) -> tuple:
    """Small numeric ABI for numba; all defaults checked upstream."""
    return (
      cfg["stop_lookback"],cfg["order_expiry_bars"],cfg["limit_offset_atr"],
      cfg["fixed_rr_enabled"],cfg["fixed_rr"],cfg["variable_risk_enabled"],
      0 if cfg["variable_risk_mode"]=="anti_martingale" else 1,
      cfg["risk_multiplier"],cfg["risk_max_levels"],cfg["risk_reset_on_win"],
      cfg["be_enabled"],UNIT_CODES[cfg["be_unit"]],cfg["be_trigger"],
      cfg["be_offset_pips"]*cfg["pip_size"],
      cfg["trailing_enabled"],UNIT_CODES[cfg["trailing_activation_unit"]],cfg["trailing_activation"],
      UNIT_CODES[cfg["trailing_distance_unit"]],cfg["trailing_distance"],
      cfg["dca_enabled"],cfg["dca_levels"],cfg["dca_size_multiplier"],UNIT_CODES[cfg["dca_spacing_unit"]],cfg["dca_spacing"],
      cfg["pyramid_enabled"],cfg["pyramid_levels"],cfg["pyramid_size_multiplier"],UNIT_CODES[cfg["pyramid_spacing_unit"]],cfg["pyramid_spacing"],
      cfg["sl_tp_from_average"],
    )
