"""Research-only event backtester: Polars ingestion and Numba simulation.

Assumptions: next-bar OPEN entries; previous completed bar indicators/ATR;
stop-first on bars hitting stop and target; one position at a time;
no position carried across IS/OOS boundary; fixed/compounding sizing;
simplified round-trip basis-point cost, not broker-accurate.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from numba import njit

FAMILIES = {0: "ema_cross", 1: "rsi_reversion", 2: "breakout"}
INTERVALS = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d"}


def load_data(path: Path) -> pl.DataFrame:
    with path.open("rb") as handle:
        first = handle.readline().decode("utf-8-sig", errors="replace")
    delimiter = "\t" if first.count("\t") > first.count(",") else ";" if first.count(";") > first.count(",") else ","
    try:
        df = pl.read_csv(path, separator=delimiter, encoding="utf8-lossy", infer_schema_length=10000)
    except Exception as exc:
        raise ValueError(f"No se pudo leer el CSV: {exc}") from exc
    renames = {col: col.strip().strip("<>").lower().replace(" ", "_") for col in df.columns}
    if len(set(renames.values())) != len(df.columns):
        raise ValueError("El CSV contiene encabezados duplicados.")
    df = df.rename(renames)
    missing = set(("open", "high", "low", "close")) - set(df.columns)
    if missing:
        raise ValueError("Faltan columnas OHLC: " + ", ".join(sorted(missing)))
    if "timestamp" in df.columns:
        text_expr = pl.col("timestamp").cast(pl.String)
    elif "datetime" in df.columns:
        text_expr = pl.col("datetime").cast(pl.String)
    elif "date" in df.columns and "time" in df.columns:
        text_expr = pl.concat_str((pl.col("date").cast(pl.String), pl.col("time").cast(pl.String)), separator=" ")
    else:
        raise ValueError("El CSV debe tener timestamp/datetime o las columnas date y time.")
    try:
        df = df.with_columns(
            text_expr.str.replace_all(r"[./]", "-").str.to_datetime(strict=False).alias("timestamp"),
            *[pl.col(c).cast(pl.Float64, strict=False).alias(c) for c in ("open", "high", "low", "close")],
        )
        df = (
            df.select("timestamp", "open", "high", "low", "close")
            .drop_nulls()
            .filter(
                (pl.col("open") > 0)
                & (pl.col("high") >= pl.max_horizontal("open", "close"))
                & (pl.col("low") <= pl.min_horizontal("open", "close"))
                & (pl.col("high") >= pl.col("low"))
            )
            .unique(subset=["timestamp"], keep="last")
            .sort("timestamp")
        )
    except Exception as exc:
        raise ValueError(f"Fechas u OHLC inválidos: {exc}") from exc
    if len(df) < 300:
        raise ValueError("Se requieren al menos 300 velas OHLC válidas y con fechas reconocibles.")
    if len(df) > 5_000_000:
        raise ValueError("Más de 5 millones de barras. Divide el archivo para esta fase.")
    return df


def describe_data(df: pl.DataFrame) -> dict:
    return {"rows": len(df), "start": str(df[0, "timestamp"]), "end": str(df[-1, "timestamp"])}


def resample(df: pl.DataFrame, timeframe: str) -> pl.DataFrame:
    if timeframe not in INTERVALS:
        raise ValueError("Temporalidad no admitida.")
    bars = df.group_by_dynamic("timestamp", every=INTERVALS[timeframe]).agg(
        pl.col("open").first(),
        pl.col("high").max(),
        pl.col("low").min(),
        pl.col("close").last(),
    ).drop_nulls().sort("timestamp")
    if len(bars) < 400:
        raise ValueError(f"No hay suficientes barras tras agrupar a {timeframe}; mínimo 400.")
    if len(bars) > 750_000:
        raise ValueError("Más de 750.000 velas a esta temporalidad; utiliza un timeframe superior o reduce el CSV.")
    return bars


@njit(cache=True)
def ema(close, length):
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    alpha = 2.0 / (length + 1)
    out[0] = close[0]
    for i in range(1, n):
        out[i] = alpha * close[i] + (1.0 - alpha) * out[i - 1]
    return out


@njit(cache=True)
def atr_wilder(high, low, close, length=14):
    n = len(close)
    out = np.empty(n, dtype=np.float64)
    out[0] = high[0] - low[0]
    for i in range(1, n):
        tr = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        out[i] = (out[i - 1] * (length - 1) + tr) / length
    return out


@njit(cache=True)
def rsi_wilder(close, length):
    n = len(close)
    out = np.full(n, 50.0, dtype=np.float64)
    if n <= length:
        return out
    up = 0.0
    down = 0.0
    for i in range(1, length + 1):
        delta = close[i] - close[i - 1]
        up += max(delta, 0.0)
        down += max(-delta, 0.0)
    up /= length
    down /= length
    for i in range(length + 1, n):
        delta = close[i] - close[i - 1]
        up = (up * (length - 1) + max(delta, 0.0)) / length
        down = (down * (length - 1) + max(-delta, 0.0)) / length
        out[i] = 100.0 if down == 0.0 else 100.0 - 100.0 / (1.0 + up / down)
    return out


@njit(cache=True)
def make_signals(kind, fast, slow, close, high, low):
    n = len(close)
    signals = np.zeros(n, dtype=np.int8)
    warmup = max(40, slow + 2)
    if kind == 0:
        a = ema(close, fast)
        b = ema(close, slow)
        for i in range(warmup, n):
            if a[i-1] <= b[i-1] and a[i] > b[i]:
                signals[i] = 1
            elif a[i-1] >= b[i-1] and a[i] < b[i]:
                signals[i] = -1
    elif kind == 1:
        r = rsi_wilder(close, fast)
        for i in range(warmup, n):
            if r[i-1] <= slow and r[i] > slow:
                signals[i] = 1
            elif r[i-1] >= 100 - slow and r[i] < 100 - slow:
                signals[i] = -1
    else:
        for i in range(warmup, n):
            hh = high[i-slow]
            ll = low[i-slow]
            for j in range(i-slow+1, i):
                hh = max(hh, high[j])
                ll = min(ll, low[j])
            if close[i] > hh:
                signals[i] = 1
            elif close[i] < ll:
                signals[i] = -1
    return signals


@njit(cache=True)
def simulate(signals, op, high, low, close, atr, days, start, end,
             rr, atr_multiplier, cost_bps, direction, modeling=1):
    """One trade per time, conservative stop-first bar collision; fill at next-bar open."""
    outcomes = np.empty(end-start, dtype=np.float64)
    trade_days = np.empty(end-start, dtype=np.int32)
    ntr = 0
    side = 0
    entry = 0.0
    sl = 0.0
    tp = 0.0
    distance = 1.0
    for i in range(max(41, start), end):
        if side == 0:
            signal = signals[i - 1]
            if signal == 0 or (direction == 1 and signal < 0) or (direction == -1 and signal > 0):
                continue
            distance = atr[i - 1] * atr_multiplier
            if not np.isfinite(distance) or distance <= 0.0:
                continue
            side = signal
            entry = op[i]
            sl = entry - side * distance
            tp = entry + side * distance * rr
            trade_day = days[i]
        exit_price = np.nan
        if modeling == 0:
            if (side == 1 and (op[i] <= sl or op[i] >= tp)) or (side == -1 and (op[i] >= sl or op[i] <= tp)):
                exit_price = op[i]
        elif side == 1:
            if op[i] <= sl:
                exit_price = op[i]  # adverse gap at open
            elif low[i] <= sl:
                exit_price = sl  # stop first on ambiguous bar
            elif high[i] >= tp:
                exit_price = tp
        else:
            if op[i] >= sl:
                exit_price = op[i]
            elif high[i] >= sl:
                exit_price = sl
            elif low[i] <= tp:
                exit_price = tp
        if i == end - 1 and np.isnan(exit_price):
            exit_price = op[i] if modeling == 0 else close[i]
        if not np.isnan(exit_price):
            gross = (exit_price - entry) * side
            round_trip_cost = entry * cost_bps / 10000.0
            outcomes[ntr] = (gross - round_trip_cost) / distance
            trade_days[ntr] = trade_day
            ntr += 1
            side = 0
    return outcomes[:ntr], trade_days[:ntr]


def summarize(r: np.ndarray, days: np.ndarray, risk_pct: float, daily: float, total: float, sizing: str = "compound", initial_deposit: float = 5000.) -> dict:
    if len(r) == 0:
        return dict(trades=0, win_rate=0., profit_factor=None, expectancy_r=0.,
                    max_drawdown_pct=0., net_return_pct=0., daily_breached=False, total_breached=False, ending_balance=round(initial_deposit, 2))
    risk = risk_pct / 100.0
    equity = 1.0
    peak = 1.0
    day_open = 1.0
    prev_day = days[0]
    dd = 0.0
    daily_breached = False
    total_breached = False
    for outcome, trade_day in zip(r, days):
        if trade_day != prev_day:
            day_open = equity
            prev_day = trade_day
        if sizing == "fixed":
            equity = max(0.0, equity + float(outcome) * risk)
        else:
            equity *= max(0.0, 1.0 + float(outcome) * risk)
        peak = max(peak, equity)
        dd = max(dd, (peak - equity) / peak * 100.0)
        daily_breached |= equity < day_open * (1.0 - daily / 100.0)
        total_breached |= equity < (1.0 - total / 100.0)
    gains = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    pf = round(gains / losses, 3) if losses > 0 else None
    return dict(trades=len(r), win_rate=round(float(np.mean(r > 0)) * 100, 2),
                profit_factor=pf, expectancy_r=round(float(np.mean(r)), 4),
                max_drawdown_pct=round(dd, 2), net_return_pct=round((equity - 1) * 100, 2),
                daily_breached=bool(daily_breached), total_breached=bool(total_breached),
                ending_balance=round(initial_deposit * equity, 2))


def bootstrap(r: np.ndarray, risk_pct: float, count: int, max_dd: float, seed: int, sizing: str = "compound") -> dict:
    if len(r) == 0:
        return dict(p95_drawdown_pct=None, probability_10pct_drawdown=None, iterations=count, trade_count=0)
    generator = np.random.default_rng(seed)
    drawdowns = np.empty(count)
    risk = risk_pct / 100.0
    for idx in range(count):
        sample = generator.choice(r, size=len(r), replace=True)
        if sizing == "fixed":
            equity = np.maximum(0.0, np.concatenate(([1.], 1. + np.cumsum(sample * risk))))
        else:
            equity = np.concatenate(([1.], np.cumprod(np.maximum(0.0, 1.0 + sample * risk))))
        peaks = np.maximum.accumulate(equity)
        drawdowns[idx] = float(np.max((peaks - equity) / peaks) * 100)
    return dict(p95_drawdown_pct=round(float(np.percentile(drawdowns, 95)), 2),
                probability_10pct_drawdown=round(float(np.mean(drawdowns >= max_dd)) * 100., 2),
                iterations=count, trade_count=len(r))


def run_exploration(source: pl.DataFrame, cfg: dict[str, Any]) -> dict:
    df = resample(source, cfg["timeframe"])
    n = len(df)
    cut = int(n * cfg["is_ratio"] / 100)
    if cut < 250 or n-cut < 100:
        raise ValueError("Se necesitan barras suficientes en IS y OOS.")
    op = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    days = df["timestamp"].dt.date().cast(pl.Int32).to_numpy()
    atr = atr_wilder(high, low, close, 14)
    rng = random.Random(20261028)
    direction = {"both": 0, "long": 1, "short": -1}[cfg["direction"]]
    selected_families = [i for i, name in FAMILIES.items() if name in cfg["families"]]
    evaluated = []
    seen = set()
    attempts = 0
    while len(evaluated) < cfg["candidates"] and attempts < cfg["candidates"] * 10:
        attempts += 1
        kind = rng.choice(selected_families)
        if kind == 0:
            fast = rng.randint(5, 28)
            slow = rng.randint(max(29, fast + 8), 90)
        elif kind == 1:
            fast = rng.randint(7, 25)
            slow = rng.randint(20, 40)
        else:
            fast = 0
            slow = rng.randint(12, 75)
        key = (kind, fast, slow)
        if key in seen:
            continue
        seen.add(key)
        signals = make_signals(kind, fast, slow, close, high, low)
        r_is, d_is = simulate(signals, op, high, low, close, atr, days, 0, cut,
                              cfg["rr"], cfg["atr_multiplier"], cfg["cost_bps"], direction)
        metrics_is = summarize(r_is, d_is, cfg["risk_pct"], cfg["prop_daily_pct"], cfg["prop_max_pct"])
        params = ({"fast": fast, "slow": slow} if kind == 0 else
                  {"rsi_period": fast, "oversold": slow} if kind == 1 else
                  {"lookback": slow})
        evaluated.append((metrics_is["expectancy_r"], metrics_is["trades"], kind, params, signals, metrics_is))
    # ONLY training metrics choose finalists. Out-of-sample is never used for selection/ranking.
    shortlisted = sorted(evaluated, key=lambda x: (x[0], x[1]), reverse=True)[:12]
    candidates = []
    for ix, (_, _, kind, params, signals, met_is) in enumerate(shortlisted):
        r_oos, d_oos = simulate(signals, op, high, low, close, atr, days, cut, n,
                                cfg["rr"], cfg["atr_multiplier"], cfg["cost_bps"], direction)
        met_oos = summarize(r_oos, d_oos, cfg["risk_pct"], cfg["prop_daily_pct"], cfg["prop_max_pct"])
        mc = bootstrap(r_oos, cfg["risk_pct"], cfg["mc_iterations"], cfg["prop_max_pct"], seed=1000 + ix)
        reasons = []
        if met_oos["trades"] < cfg["min_trades"]:
            reasons.append("Muestra OOS insuficiente")
        if met_oos["expectancy_r"] <= 0:
            reasons.append("Expectativa OOS no positiva")
        if met_oos["profit_factor"] is None or met_oos["profit_factor"] <= 1.05:
            reasons.append("Factor de beneficio OOS no concluyente")
        if met_oos["daily_breached"] or met_oos["total_breached"]:
            reasons.append("Límite de pérdida infringido")
        if mc["p95_drawdown_pct"] is not None and mc["p95_drawdown_pct"] >= cfg["prop_max_pct"]:
            reasons.append("Drawdown P95 supera el límite")
        candidates.append({
            "id": f"candidate-{ix+1}",
            "family": FAMILIES[kind],
            "params": params,
            "in_sample": met_is,
            "out_of_sample": met_oos,
            "monte_carlo": mc,
            "accepted": not reasons,
            "reasons": reasons,
        })
    warnings = [
        "Filtros preliminares, no validación definitiva. Bootstrap de trades OOS, no mercado sintético.",
        "Costes expresados en bps genéricos; no incluyen comisiones, swaps, ejecución ni spreads intradía reales.",
        "Orden de ranking definido SOLO por entrenamiento (IS); no se optimiza con OOS.",
        "No se ejecuta walk-forward rodante, pruebas de significancia múltiple ni modelado tick a tick en esta versión.",
    ]
    return {
        "tested": len(evaluated),
        "accepted": sum(c["accepted"] for c in candidates),
        "candidates": candidates,
        "warnings": warnings,
    }
