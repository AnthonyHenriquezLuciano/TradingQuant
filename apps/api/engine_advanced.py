"""TradingQuant research engine, configurable exploration modes.

The OOS window is held out and never used to rank, evolve or crossover a candidate.
This is a preliminary bar-based research model, not an exchange-grade fill simulator.
"""
from __future__ import annotations

from datetime import date
from typing import Any
import math
import random

import numpy as np
import polars as pl

from engine import (
    FAMILIES, INTERVALS, resample, ema, atr_wilder, make_signals,
    simulate, summarize, bootstrap,
)

ORDER = list(INTERVALS)


def filter_period(source: pl.DataFrame, cfg: dict[str, Any]) -> pl.DataFrame:
    frame = source
    for key, op in (("start_date", "gte"), ("end_date", "lte")):
        value = cfg.get(key) or ""
        if value:
            try:
                parsed = date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Las fechas deben tener formato AAAA-MM-DD.") from exc
            condition = pl.col("timestamp").dt.date() >= parsed if op == "gte" else pl.col("timestamp").dt.date() <= parsed
            frame = frame.filter(condition)
    if len(frame) < 400:
        raise ValueError("El periodo seleccionado contiene menos de 400 velas; amplía el rango.")
    return frame


def confirmed_higher_bias(source: pl.DataFrame, lower: pl.DataFrame, htf: str) -> np.ndarray:
    """EMA20/EMA50 of completed higher timeframe candles only.

    Each HTF candle's signal becomes available at *the end of that candle*,
    as-of joined to the LTF bar OPEN. Incomplete/future HTF bars are never visible.
    """
    h = (
        source.group_by_dynamic("timestamp", every=INTERVALS[htf])
        .agg(pl.col("close").last())
        .drop_nulls()
        .sort("timestamp")
    )
    if len(h) < 65:
        raise ValueError("No hay al menos 65 velas completas de contexto en " + htf)
    close = h["close"].to_numpy()
    a = ema(close, 20)
    b = ema(close, 50)
    bias = np.where(a > b, 1, np.where(a < b, -1, 0)).astype(np.int8)
    bias[:55] = 0
    completed = (
        h.select(pl.col("timestamp").dt.offset_by(INTERVALS[htf]).alias("available_at"))
        .with_columns(pl.Series("bias", bias))
        .sort("available_at")
    )
    joined = lower.select("timestamp").join_asof(
        completed, left_on="timestamp", right_on="available_at", strategy="backward"
    )
    return joined["bias"].fill_null(0).to_numpy().astype(np.int8)


def random_gene(rng: random.Random, families: list[int]) -> tuple[int, int, int]:
    kind = rng.choice(families)
    if kind == 0:
        fast = rng.randint(5, 28)
        slow = rng.randint(max(29, fast+8), 90)
    elif kind == 1:
        fast = rng.randint(7, 25)
        slow = rng.randint(20, 40)
    else:
        fast = 0
        slow = rng.randint(12, 75)
    return (kind, fast, slow)


def mutate_or_cross(rng: random.Random, a: tuple[int, int, int],
                    b: tuple[int, int, int], families: list[int]) -> tuple[int, int, int]:
    if rng.random() < .13:
        return random_gene(rng, families)
    kind = rng.choice((a[0], b[0]))
    if kind == 0:
        fast = max(5, min(28, rng.choice((a[1], b[1])) + rng.randint(-3, 3)))
        slow = max(29, min(90, rng.choice((a[2], b[2])) + rng.randint(-7, 7)))
        slow = max(slow, fast + 8)
    elif kind == 1:
        fast = max(7, min(25, rng.choice((a[1], b[1])) + rng.randint(-3, 3)))
        slow = max(20, min(40, rng.choice((a[2], b[2])) + rng.randint(-4, 4)))
    else:
        fast = 0
        slow = max(12, min(75, rng.choice((a[2], b[2])) + rng.randint(-8, 8)))
    return (kind, fast, slow)


def sharpe_of_daily_trades(outcomes: np.ndarray, days: np.ndarray) -> float:
    """Annualized Sharpe approximation from trade R sums on trading days with exits.

    For short samples the estimator is noisy; fewer than 10 traded days get
    a heavy training penalty. This is *not* daily mark-to-market Sharpe.
    """
    if len(outcomes) < 4:
        return -100.
    unique, inverse = np.unique(days, return_inverse=True)
    if len(unique) < 2:
        return -100.
    daily_r = np.zeros(len(unique), dtype=np.float64)
    np.add.at(daily_r, inverse, outcomes)
    std = float(np.std(daily_r, ddof=1))
    if std <= 1e-12:
        return -100.
    raw = math.sqrt(252.) * float(np.mean(daily_r)) / std
    return float(max(-50., min(50., raw))) * min(1.0, len(unique)/10.)


def derive_scenarios(timeframes: list[str], mode: str) -> list[tuple[str, str, str | None]]:
    ordered = sorted(set(timeframes), key=ORDER.index)
    jobs: list[tuple[str, str, str | None]] = []
    if mode in ("individual", "both"):
        jobs.extend(("individual", tf, None) for tf in ordered)
    if mode in ("combined", "both"):
        if len(ordered) < 2:
            raise ValueError("Multi-TF combinado requiere al menos dos intervalos.")
        jobs.append(("combined", ordered[0], ordered[-1]))
    return jobs


def run_advanced(source: pl.DataFrame, cfg: dict[str, Any]) -> dict:
    mode = cfg.get("mode", "random")
    modeling = cfg.get("modeling", "ohlc")
    sizing = cfg.get("sizing", "compound")
    multi = cfg.get("multi_tf", "individual")
    if mode not in ("random", "genetic"):
        raise ValueError("Motor de búsqueda no admitido.")
    if modeling not in ("ohlc", "open"):
        raise ValueError("El modelado M1/tick necesita datos externos y todavía no está implementado.")
    if sizing not in ("compound", "fixed"):
        raise ValueError("Modo de sizing no admitido.")
    if multi not in ("individual", "combined", "both"):
        raise ValueError("Modo Multi-TF no admitido.")
    timeframes = cfg.get("timeframes") or [cfg.get("timeframe", "5m")]
    if not timeframes or any(x not in INTERVALS for x in timeframes):
        raise ValueError("Selecciona uno o varios intervalos válidos.")
    if cfg.get("start_date") and cfg.get("end_date") and cfg["start_date"] > cfg["end_date"]:
        raise ValueError("La fecha de inicio debe ser anterior a la fecha final.")
    budget = cfg.get("candidates", 100)
    if not isinstance(budget, int) or budget < 1 or budget > 2000:
        raise ValueError("El presupuesto debe estar entre 1 y 2,000 combinaciones.")
    if cfg.get("initial_deposit", 5000) < 100:
        raise ValueError("El depósito inicial debe ser al menos USD 100.")
    families = [i for i,name in FAMILIES.items() if name in cfg["families"]]
    if not families:
        raise ValueError("Selecciona alguna familia de indicadores.")
    source = filter_period(source, cfg)
    # Never label M5 source bars as M1 by "resampling" into empty minute buckets.
    source_step = source.select(
        pl.col("timestamp").diff().dt.total_minutes().median()
    ).item()
    interval_minutes = {"1m":1,"5m":5,"15m":15,"30m":30,"1h":60,"4h":240,"1d":1440}
    if source_step is not None and any(interval_minutes[tf] < float(source_step) - 1e-6 for tf in timeframes):
        raise ValueError(
            "El CSV tiene una resolución aproximada de "
            + str(round(float(source_step),2))
            + " minutos; selecciona intervalos iguales o mayores. No se generan velas de menor resolución."
        )
    jobs = derive_scenarios(timeframes, multi)
    if budget < len(jobs):
        raise ValueError("El presupuesto debe permitir al menos una evaluación por intervalo.")
    rng = random.Random(20261028)
    direction = {"both":0,"long":1,"short":-1}[cfg["direction"]]
    directions = [1,-1] if direction == 0 else [direction]
    sampling_model = 0 if modeling == "open" else 1
    per = [budget//len(jobs) + (i<budget%len(jobs)) for i in range(len(jobs))]
    all_trials: list[dict] = []
    warnings: list[str] = []
    if mode == "genetic":
        warnings.append("Sharpe genético estimado a partir de resultados R diarios en días con operaciones; no equivale al Sharpe mark-to-market.")

    for (job_type, tf, htf), max_eval in zip(jobs,per):
        df = resample(source, tf)
        n = len(df)
        cut = int(n * cfg["is_ratio"] / 100)
        if cut < 250 or n-cut < 100:
            raise ValueError("El intervalo "+tf+" no tiene suficientes velas IS/OOS.")
        op,hi,lo,close = (df[k].to_numpy() for k in ("open","high","low","close"))
        days = df["timestamp"].dt.date().cast(pl.Int32).to_numpy()
        atr = atr_wilder(hi,lo,close,14)
        higher_bias = confirmed_higher_bias(source,df,htf) if htf else None
        seen: set[tuple[int,int,int,int]] = set()
        evaluated: list[dict] = []

        def assess(gene: tuple[int,int,int], side: int) -> dict | None:
            key = (*gene, side)
            if key in seen:
                return None
            seen.add(key)
            kind,fast,slow = gene
            signals = make_signals(kind,fast,slow,close,hi,lo)
            if higher_bias is not None:
                signals = np.where(signals == higher_bias,signals,0).astype(np.int8)
            r_is,d_is = simulate(
                signals,op,hi,lo,close,atr,days,0,cut,
                cfg["rr"],cfg["atr_multiplier"],cfg["cost_bps"],side,sampling_model,
            )
            metrics_is = summarize(
                r_is,d_is,cfg["risk_pct"],cfg["prop_daily_pct"],cfg["prop_max_pct"],
                sizing,cfg["initial_deposit"],
            )
            score = sharpe_of_daily_trades(r_is,d_is) if mode=="genetic" else metrics_is["expectancy_r"]
            if metrics_is["trades"] < max(4,cfg["min_trades"]):
                score -= 100.
            return dict(
                gene=gene,side=side,score=float(score),signals=signals,in_sample=metrics_is,
                dataframe=(op,hi,lo,close,atr,days,cut,n),
                timeframe=tf,context=htf,model=job_type,
            )

        if mode == "random":
            attempts = 0
            while len(evaluated) < max_eval and attempts < max_eval*25:
                attempts += 1
                gene = random_gene(rng,families)
                for side in directions:
                    if len(evaluated) >= max_eval:
                        break
                    trial = assess(gene,side)
                    if trial is not None:
                        evaluated.append(trial)
        else:
            generations = max(2,min(30,int(cfg.get("generations",8))))
            pop_size = max(2, min(24,max_eval//generations))
            population: list[dict] = []
            attempts = 0
            # Evolve across generations while respecting the global evaluation budget.
            for gen in range(generations):
                new_gen: list[dict] = []
                target = min(max_eval-len(evaluated),pop_size)
                while len(new_gen)<target and attempts < max_eval*50:
                    attempts += 1
                    if not population or gen == 0:
                        gene = random_gene(rng,families)
                    else:
                        elite = sorted(population,key=lambda t:t["score"],reverse=True)[:max(2,len(population)//2)]
                        mother = rng.choice(elite)["gene"]
                        father = rng.choice(elite)["gene"]
                        gene = mutate_or_cross(rng,mother,father,families)
                    for side in directions:
                        if len(new_gen) >= target:
                            break
                        trial = assess(gene,side)
                        if trial is not None:
                            new_gen.append(trial)
                            evaluated.append(trial)
                if not new_gen:
                    break
                # Elitism is based ONLY on in-sample scores.
                population = sorted(population+new_gen,key=lambda t:t["score"],reverse=True)[:pop_size]
            while len(evaluated)<max_eval and attempts<max_eval*50:
                attempts += 1
                gene = random_gene(rng,families)
                for side in directions:
                    if len(evaluated) >= max_eval:
                        break
                    trial = assess(gene,side)
                    if trial is not None:
                        evaluated.append(trial)
        all_trials.extend(evaluated)

    # Only training metrics determine the shortlist; never rank by OOS.
    shortlist = sorted(all_trials,key=lambda t:(t["score"],t["in_sample"]["trades"]),reverse=True)[:12]
    candidates = []
    for i,trial in enumerate(shortlist):
        gene = trial["gene"]
        kind,fast,slow = gene
        op,hi,lo,cl,atr,days,cut,n = trial["dataframe"]
        r_oos,d_oos = simulate(
            trial["signals"],op,hi,lo,cl,atr,days,cut,n,
            cfg["rr"],cfg["atr_multiplier"],cfg["cost_bps"],trial["side"],sampling_model,
        )
        metrics_oos = summarize(
            r_oos,d_oos,cfg["risk_pct"],cfg["prop_daily_pct"],cfg["prop_max_pct"],
            sizing,cfg["initial_deposit"],
        )
        mc = bootstrap(
            r_oos,cfg["risk_pct"],cfg["mc_iterations"],cfg["prop_max_pct"],1000+i,sizing,
        )
        reasons = []
        if metrics_oos["trades"]<cfg["min_trades"]:
            reasons.append("Muestra OOS insuficiente")
        if metrics_oos["expectancy_r"]<=0:
            reasons.append("Expectativa OOS no positiva")
        if metrics_oos["profit_factor"] is None or metrics_oos["profit_factor"]<=1.05:
            reasons.append("Profit factor OOS insuficiente")
        if metrics_oos["daily_breached"] or metrics_oos["total_breached"]:
            reasons.append("Límites de riesgo superados")
        if mc["p95_drawdown_pct"] is not None and mc["p95_drawdown_pct"]>=cfg["prop_max_pct"]:
            reasons.append("Drawdown Monte Carlo P95 supera el límite")
        params = ({"fast":fast,"slow":slow} if kind==0 else
                  {"rsi_period":fast,"oversold":slow} if kind==1 else {"lookback":slow})
        candidates.append(dict(
            id="candidate-"+str(i+1),family=FAMILIES[kind],params=params,
            timeframe=trial["timeframe"],context_timeframe=trial["context"],
            direction="long" if trial["side"] == 1 else "short",
            model=trial["model"],in_sample=trial["in_sample"],
            out_of_sample=metrics_oos,monte_carlo=mc,
            accepted=not reasons,reasons=reasons,
        ))
    warnings += [
        "Evaluación exploratoria: el split IS/OOS no sustituye walk-forward ni forward testing.",
        "Comisiones, spread variable, swaps, slippage y ejecución tick a tick no están modelados.",
        "El capital inicial y sizing afectan el balance estimado, no generan cotizaciones reales.",
        "El multi-TF combinado aplica únicamente una tendencia HTF EMA20/50 con barras completas.",
        "Monte Carlo remuestrea operaciones OOS; no simula caminos de mercado.",
    ]
    return dict(
        tested=len(all_trials),accepted=sum(1 for c in candidates if c["accepted"]),
        candidates=candidates,warnings=warnings,
    )
