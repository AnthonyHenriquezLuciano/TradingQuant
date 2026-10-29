"""Capital-management bar simulator.

Entries at next bar open, stop first for ambiguous OHLC bars.
BE/trailing update after bar close and apply only to subsequent bars.
Stops use realized P&L only; not prop-firm floating-equity enforcement.
"""
from __future__ import annotations
import random
import numpy as np
from numba import njit

DEFAULT_CAPITAL = {
    "exit_mode": "atr_linked",
    "sl_atr": {"from": 1.5, "step": .1, "to": 1.5},
    "tp_multiplier": {"from": 1.0, "step": .1, "to": 1.0},
    "tp_atr": {"from": 1.5, "step": .1, "to": 1.5},
    "sl_percent": {"from": .5, "step": .1, "to": .5},
    "breakeven_enabled": False, "breakeven_r": 1.,
    "trailing_enabled": False, "trailing_atr": 1.5,
    "max_bars_in_trade": 0, "max_trades_per_day": 0,
    "cooldown_bars": 0, "stop_after_daily_pct": 0.,
}
RANGE_LIMITS = {
    "sl_atr": (.1, 10.),
    "tp_multiplier": (.1, 10.),
    "tp_atr": (.1, 12.),
    "sl_percent": (.05, 10.),
}
MODE_CODES = {"atr_linked": 0, "atr_classic": 1, "percent": 2}


def normalize_capital(cfg: dict) -> dict:
    """Validate before compute, preserving legacy single-ATR configurations."""
    raw = cfg.get("capital")
    if raw is None:
        raw = {
            "sl_atr": {"from": cfg.get("atr_multiplier", 1.5),
                       "step": .1, "to": cfg.get("atr_multiplier", 1.5)},
            "tp_multiplier": {"from": cfg.get("rr", 1.),
                              "step": .1, "to": cfg.get("rr", 1.)},
        }
    out = {**DEFAULT_CAPITAL, **raw}
    if out["exit_mode"] not in MODE_CODES:
        raise ValueError("Modo de salida no implementado. No se usará un modo alternativo sin avisar.")
    for key, (lower, upper) in RANGE_LIMITS.items():
        bounds = out[key]
        if not isinstance(bounds, dict):
            raise ValueError("Rango inválido: " + key)
        start, step, stop = (float(bounds[x]) for x in ("from", "step", "to"))
        if not np.isfinite(start + step + stop) or start < lower-1e-9 or stop > upper+1e-9 or start > stop or step <= 0:
            raise ValueError("Rango de salida inválido: " + key)
        out[key] = {"from": start, "step": step, "to": stop}
    for key, low, high in (
        ("breakeven_r", .1, 10), ("trailing_atr", .1, 10),
        ("stop_after_daily_pct", 0, 20),
        ("max_trades_per_day", 0, 100),
        ("cooldown_bars", 0, 1000),
        ("max_bars_in_trade", 0, 1000),
    ):
        val = out[key]
        if not isinstance(val, (int, float)) or not np.isfinite(val) or val < low or val > high:
            raise ValueError("Parámetro de gestión fuera de rango: " + key)
        if key in ("max_trades_per_day", "cooldown_bars", "max_bars_in_trade") and int(val) != val:
            raise ValueError("El contador debe ser entero: " + key)
    for key in ("breakeven_enabled", "trailing_enabled"):
        if not isinstance(out[key], bool):
            raise ValueError("Bandera inválida de protección: " + key)
    return out


def exit_keys(capital: dict) -> tuple[str, str]:
    return (
        ("sl_atr", "tp_atr") if capital["exit_mode"] == "atr_classic"
        else ("sl_percent", "tp_multiplier") if capital["exit_mode"] == "percent"
        else ("sl_atr", "tp_multiplier")
    )


def values_for(capital: dict, key: str) -> list[float]:
    d = capital[key]
    n = min(10000, int((d["to"]-d["from"])/d["step"] + 1e-8)+1)
    return [round(d["from"]+i*d["step"], 8) for i in range(n)]


def sample_exit(rng: random.Random, capital: dict) -> tuple[float, float]:
    keys = exit_keys(capital)
    return rng.choice(values_for(capital, keys[0])), rng.choice(values_for(capital, keys[1]))


def mutate_exit(rng: random.Random, capital: dict, a: tuple[float,float],
                b: tuple[float,float]) -> tuple[float,float]:
    keys = exit_keys(capital)
    results = []
    for j, key in enumerate(keys):
        options = values_for(capital, key)
        target = rng.choice((a[j],b[j])) + rng.choice((-1,0,1))*capital[key]["step"]
        results.append(min(options, key=lambda x: abs(x-target)))
    return results[0],results[1]


DEFAULT_RISK_RULES = {
    "max_daily_gain_pct": 0., "max_weekly_gain_pct": 0.,
    "max_monthly_gain_pct": 0., "max_account_gain_pct": 0.,
    "max_consecutive_wins": 0, "max_daily_loss_pct": 0.,
    "max_weekly_loss_pct": 0., "max_monthly_loss_pct": 0.,
    "max_account_loss_pct": 0., "max_consecutive_losses": 0,
    "min_reward_risk_ratio": 0.,
}

def normalize_risk_rules(config: dict) -> dict:
    if not isinstance(config,dict):
        raise ValueError("La configuración de riesgo debe ser un objeto.")
    rules={**DEFAULT_RISK_RULES,**config}
    for key in DEFAULT_RISK_RULES:
        val=rules[key]
        limit=100 if "consecutive" in key else 200 if key=="max_account_gain_pct" else 100
        if not isinstance(val,(int,float)) or isinstance(val,bool) or not np.isfinite(val) or val<0 or val>limit:
            raise ValueError("Valor de riesgo inválido: "+key)
        if "consecutive" in key and int(val)!=val:
            raise ValueError("Las rachas deben ser enteras.")
    return rules


@njit(cache=True)
def simulate_capital(
    signals, op, high, low, close, atr, days, start, end,
    exit_code, sl_factor, tp_factor, cost_bps, direction, modeling,
    risk_pct, initial_deposit, fixed_sizing,
    breakeven, be_trigger_r, trailing, trailing_atr, max_hold_bars,
    max_trades_day, cooldown_bars, daily_stop_pct, total_stop_pct,
    profit_stop_pct,
    allow_entry=None,forced_exit=None,weeks=None,months=None,
    max_gains=None,max_losses=None,max_consecutive_wins=0,max_consecutive_losses=0,
):
    """Output entry-day R multiples and entry days for comparable summaries.

    Daily/total stops are on *realized* equity only. No tick-based broker
    leverage, intrabar floating DD, partial fills, swaps, margin or spread.
    """
    n=end-start
    outcomes=np.empty(n,dtype=np.float64)
    trade_days=np.empty(n,dtype=np.int32)
    count=0
    side=0
    entry=0.
    stop=0.
    target=0.
    initial_distance=1.
    entry_bar=-1
    trade_day=0
    equity=1.
    daily_open=1.
    current_day=days[max(0,start)]
    current_week=weeks[max(0,start)] if weeks is not None else 0
    current_month=months[max(0,start)] if months is not None else 0
    week_open=1.
    month_open=1.
    consecutive_wins=0
    consecutive_losses=0
    paused_for_streak=False
    trades_today=0
    last_exit=-1000000
    for i in range(max(41,start),end):
        if days[i] != current_day:
            current_day=days[i]
            daily_open=equity
            trades_today=0
            consecutive_wins=0
            consecutive_losses=0
            paused_for_streak=False
        if weeks is not None and weeks[i]!=current_week:
            current_week=weeks[i]
            week_open=equity
        if months is not None and months[i]!=current_month:
            current_month=months[i]
            month_open=equity
        if side == 0:
            if allow_entry is not None and not allow_entry[i]:
                continue
            if paused_for_streak:
                continue
            if max_gains is not None and max_losses is not None:
                d_pct=(equity/daily_open-1.)*100. if daily_open>0. else -100.
                w_pct=(equity/week_open-1.)*100. if week_open>0. else -100.
                m_pct=(equity/month_open-1.)*100. if month_open>0. else -100.
                a_pct=(equity-1.)*100.
                if ((max_gains[0]>0 and d_pct>=max_gains[0]) or
                    (max_gains[1]>0 and w_pct>=max_gains[1]) or
                    (max_gains[2]>0 and m_pct>=max_gains[2]) or
                    (max_gains[3]>0 and a_pct>=max_gains[3]) or
                    (max_losses[0]>0 and d_pct<=-max_losses[0]) or
                    (max_losses[1]>0 and w_pct<=-max_losses[1]) or
                    (max_losses[2]>0 and m_pct<=-max_losses[2]) or
                    (max_losses[3]>0 and a_pct<=-max_losses[3])):
                    continue
            if equity <= 0 or equity < 1.-total_stop_pct/100.:
                continue
            day_pct=(equity/daily_open-1.)*100. if daily_open>0. else -100.
            if day_pct <= -daily_stop_pct or (profit_stop_pct>0 and day_pct>=profit_stop_pct):
                continue
            if max_trades_day>0 and trades_today>=max_trades_day:
                continue
            if i<=last_exit+cooldown_bars:
                continue
            signal=signals[i-1]
            if signal==0 or (direction==1 and signal<0) or (direction==-1 and signal>0):
                continue
            entry=op[i]
            if exit_code==2:
                initial_distance=entry*sl_factor/100.
            else:
                initial_distance=atr[i-1]*sl_factor
            if initial_distance<=0 or not np.isfinite(initial_distance):
                continue
            side=signal
            entry_bar=i
            trade_day=days[i]
            trades_today+=1
            stop=entry-side*initial_distance
            take_distance=tp_factor*initial_distance if exit_code in (0,2) else atr[i-1]*tp_factor
            target=entry+side*take_distance
        exit_price=np.nan
        if forced_exit is not None and forced_exit[i]:
            exit_price=op[i]
        elif modeling==0:
            if side==1 and (op[i]<=stop or op[i]>=target):
                exit_price=op[i]
            elif side==-1 and (op[i]>=stop or op[i]<=target):
                exit_price=op[i]
        elif side==1:
            if op[i]<=stop:
                exit_price=op[i]       # adverse gap
            elif low[i]<=stop:
                exit_price=stop
            elif high[i]>=target:
                exit_price=target
        else:
            if op[i]>=stop:
                exit_price=op[i]
            elif high[i]>=stop:
                exit_price=stop
            elif low[i]<=target:
                exit_price=target
        if np.isnan(exit_price) and max_hold_bars>0 and i-entry_bar+1>=max_hold_bars:
            exit_price=op[i] if modeling==0 else close[i]
        if np.isnan(exit_price) and i==end-1:
            exit_price=op[i] if modeling==0 else close[i]
        if not np.isnan(exit_price):
            roundtrip_cost=entry*cost_bps/10000.
            r=((exit_price-entry)*side-roundtrip_cost)/initial_distance
            outcomes[count]=r
            trade_days[count]=trade_day
            count+=1
            if fixed_sizing:
                equity=max(0.,equity+r*risk_pct/100.)
            else:
                equity=max(0.,equity*(1.+r*risk_pct/100.))
            if r>0:
                consecutive_wins+=1
                consecutive_losses=0
            elif r<0:
                consecutive_losses+=1
                consecutive_wins=0
            if (max_consecutive_wins>0 and consecutive_wins>=max_consecutive_wins) or (max_consecutive_losses>0 and consecutive_losses>=max_consecutive_losses):
                paused_for_streak=True
            side=0
            last_exit=i
        else:
            # Changes apply to following bar ONLY, using completed bar data.
            observed_price=op[i] if modeling==0 else close[i]
            observed_atr=atr[i-1] if modeling==0 else atr[i]
            if breakeven and (observed_price-entry)*side>=initial_distance*be_trigger_r:
                if side==1 and entry>stop:
                    stop=entry
                elif side==-1 and entry<stop:
                    stop=entry
            if trailing and np.isfinite(observed_atr) and observed_atr>0:
                proposal=observed_price-side*observed_atr*trailing_atr
                if side==1 and proposal>stop:
                    stop=proposal
                elif side==-1 and proposal<stop:
                    stop=proposal
    return outcomes[:count],trade_days[:count]
