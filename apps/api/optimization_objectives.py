"""In-sample-only optimization objectives for TradingQuant.

All annualization uses a 252-trading-day convention and includes zero-return
days present in the observed dataset. We only have realized trade closes, not
daily mark-to-market equity, so volatility and drawdown are approximations.

Funding pass rate is a Monte Carlo *proxy*, not verified probability of passing:
128 block-of-trading-day bootstrap paths, two sequential phases (8%, 5%),
60 trading days per phase, 3% daily and 10% total default realized-balance
limits, zero minimum trading days. No floating drawdown, min hold or news rules.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
from funding_simulator import validate_funding,simulate_funding

OBJECTIVES = (
    "balanced", "sharpe", "sortino", "calmar", "net_profit",
    "min_drawdown", "profit_factor", "expectancy", "win_rate",
    "recovery_factor", "funding_pass_rate",
)
FUNDING_PHASE_TARGETS = (8.0, 5.0)
FUNDING_PHASE_DAYS = 60
FUNDING_SIMULATIONS = 128


def validate_objective(value: str) -> str:
    if value not in OBJECTIVES:
        raise ValueError("Objetivo de optimización no reconocido.")
    return value


def _realized_equity(
    outcomes: np.ndarray, risk_pct: float, sizing: str
) -> np.ndarray:
    equity = np.empty(len(outcomes) + 1, dtype=np.float64)
    equity[0] = 1.0
    risk = risk_pct / 100.0
    for i, r in enumerate(outcomes):
        equity[i + 1] = max(
            0.0,
            equity[i] + float(r) * risk * (1.0 if sizing == "fixed" else equity[i])
        )
    return equity


def _daily_returns(
    r: np.ndarray, dates: np.ndarray,
    all_days: np.ndarray, risk_pct: float, sizing: str
) -> np.ndarray:
    """Close-to-close realized daily returns, including observed no-trade days."""
    daily = np.zeros(len(all_days), dtype=np.float64)
    if len(r) == 0:
        return daily
    # The date labels come from the exit bar and are never inferred from
    # the future. For daily compounding, aggregate changes to equity.
    equity = _realized_equity(r, risk_pct, sizing)
    for i, day in enumerate(all_days):
        matches = np.flatnonzero(dates == day)
        if matches.size:
            before = equity[matches[0]]
            after = equity[matches[-1] + 1]
            daily[i] = (after / before - 1.0) if before > 0 else -1.0
    return daily


def funding_pass_rate(
    daily_returns: np.ndarray, daily_dd_pct: float, total_dd_pct: float,
    seed: int, simulations: int = FUNDING_SIMULATIONS,
    max_days: int = FUNDING_PHASE_DAYS,
) -> float:
    """Estimated two-stage pass frequency (percentage).

    Independently resamples observed completed *days*, not trade ticks.
    A path fails when its realized end-of-day equity breaches either floor.
    Daily limits are evaluated from the previous day's close; overnight and
    floating P&L cannot be reconstructed from trade-only outcomes.
    """
    if daily_returns.size < 10 or simulations < 1:
        return 0.0
    rng = np.random.default_rng(seed)
    paths = rng.choice(daily_returns, size=(simulations, len(FUNDING_PHASE_TARGETS), max_days), replace=True)
    equity = np.ones(simulations, dtype=np.float64)
    alive = np.ones(simulations, dtype=np.bool_)
    for stage, target in enumerate(FUNDING_PHASE_TARGETS):
        equity[:] = 1.0
        passed = np.zeros(simulations, dtype=np.bool_)
        for day in range(max_days):
            active = alive & ~passed
            if not np.any(active):
                break
            # Pre-day account equity is the reference used for daily stop.
            before = equity[active]
            equity[active] = before * np.maximum(0., 1. + paths[active,stage,day])
            loss_pct = (1. - np.divide(equity[active],before,out=np.zeros_like(before),where=before>0)) * 100.
            failed_now = (loss_pct >= daily_dd_pct) | ((1. - equity[active]) * 100. >= total_dd_pct)
            indices = np.flatnonzero(active)
            alive[indices[failed_now]] = False
            passed[indices[(~failed_now) & (equity[active] >= 1. + target/100.)]] = True
        alive &= passed
    return float(alive.mean() * 100.)


def objective_score(
    metric: str, outcomes: np.ndarray, exit_days: np.ndarray,
    observed_days: np.ndarray, risk_pct: float, sizing: str,
    initial_deposit: float, daily_dd_pct: float, total_dd_pct: float,
    seed: int = 0, funding_config: dict | None = None,
) -> tuple[float, dict]:
    """Higher score is better for every objective. Selection is entirely IS."""
    validate_objective(metric)
    r = np.asarray(outcomes, dtype=np.float64)
    days = np.asarray(exit_days, dtype=np.int32)
    calendar = np.unique(np.asarray(observed_days, dtype=np.int32))
    if calendar.size < 2 or r.size == 0:
        return -1e6, {"objective_score": -1e6}

    equity = _realized_equity(r, risk_pct, sizing)
    daily = _daily_returns(r, days, calendar, risk_pct, sizing)
    span = max(1, len(calendar))
    peaks = np.maximum.accumulate(equity)
    max_dd_fraction = float(np.max((peaks - equity) / np.maximum(peaks, 1e-12)))
    dd_pct = 100.0 * max_dd_fraction
    pnl_usd = float((equity[-1] - 1.) * initial_deposit)

    profits_usd = max(0., float(np.sum(np.maximum(np.diff(equity),0.))) * initial_deposit)
    losses_usd = max(0., float(-np.sum(np.minimum(np.diff(equity),0.))) * initial_deposit)
    pf = min(100., profits_usd / losses_usd) if losses_usd > 1e-9 else (100. if profits_usd > 0 else 0.)
    expectancy = pnl_usd / r.size
    win_rate = float(np.mean(r > 0) * 100.)
    max_dd_absolute_usd = float(np.max(peaks - equity) * initial_deposit)
    recovery = (pnl_usd / max_dd_absolute_usd) if max_dd_absolute_usd > 1e-9 else (100. if pnl_usd>0 else 0.)

    mu = float(daily.mean())
    std = float(daily.std(ddof=1))
    downside = float(np.sqrt(np.mean(np.minimum(daily, 0.) ** 2)))
    sharpe = math.sqrt(252.) * mu / std if std > 1e-12 else (100. if mu > 0 else 0.)
    sortino = math.sqrt(252.) * mu / downside if downside > 1e-12 else (100. if mu > 0 else 0.)
    # Annualized realized return, including days when no trade closed.
    annual_return = (max(0., equity[-1]) ** (252./span) - 1.) if equity[-1] > 0 else -1.
    calmar = annual_return / max_dd_fraction if max_dd_fraction>1e-10 else (100. if annual_return>0 else 0.)
    funding = 0.
    funding_result = None
    if funding_config is not None and validate_funding(funding_config)["enabled"]:
        normalized=validate_funding(funding_config)
        activity=np.isin(calendar,days)
        funding_result=simulate_funding(daily,activity,normalized,seed)
        funding=funding_result["pass_rate_pct"]
        # We prefer strategies with the same pass rate that pass sooner.
        # P20 is CONDITIONAL on success and must never replace pass rate.
        selected=funding_result["selected_percentile_days"]
        if metric=="funding_pass_rate" and selected is not None:
            funding=funding/(1.+selected/365.)
        if not funding_result["eligible"]:
            funding-=100000.
    elif metric == "funding_pass_rate":
        funding=funding_pass_rate(daily, daily_dd_pct, total_dd_pct, seed)

    values = {
        "balanced": 2.*sharpe - max(0., dd_pct - 30.) - 0.5*max(0., dd_pct-30.) +
                    (min(5., pf-1.5) if pf>1.5 else 0.),
        "sharpe": sharpe, "sortino": sortino, "calmar": calmar,
        "net_profit": pnl_usd,
        "min_drawdown": -dd_pct, "profit_factor": pf,
        "expectancy": expectancy, "win_rate": win_rate,
        "recovery_factor": recovery,
        "funding_pass_rate": funding,
    }
    score = float(np.clip(values[metric], -1e6, 1e6))
    return score, {
        "objective_score": round(score, 6),
        "funding_evaluation_is": funding_result,
        "annualized_sharpe": round(float(np.clip(sharpe,-1e6,1e6)), 4),
        "annualized_sortino": round(float(np.clip(sortino,-1e6,1e6)), 4),
        "calmar": round(float(np.clip(calmar,-1e6,1e6)), 4),
        "pnl_usd": round(pnl_usd,2),
        "drawdown_pct": round(dd_pct, 4),
        "expectancy_usd_per_trade": round(expectancy, 4),
        "recovery_factor": round(float(np.clip(recovery,-1e6,1e6)),4),
        "funding_pass_rate_estimated_pct": funding_result["pass_rate_pct"] if funding_result is not None else round(funding, 4) if metric=="funding_pass_rate" else None,
        "observed_trading_days": span,
    }


def reproducible_seed(gene: tuple, side: int, pair: tuple) -> int:
    key = repr((gene, side, pair)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "little")
