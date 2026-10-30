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
from market_setups import SITUATIONS, SOURCE_ZONES, sweep_reference, sweep_signals
from technical_signals import SUPPORTED as EXTENDED_FAMILIES, technical_signals
from engine_capital import normalize_capital,normalize_risk_rules,MODE_CODES,exit_keys,sample_exit,mutate_exit,simulate_capital
from engine_schedule import time_arrays,validate_schedule
from optimization_objectives import validate_objective,objective_score,reproducible_seed,_daily_returns
from funding_simulator import validate_funding,simulate_funding
from advanced_modifiers import validate_advanced,is_active,execution_arguments,ENTRY_CODES
from engine_advanced_orders import simulate_advanced_orders
from research_validation import (
    validate_quality, validate_walkforward, validate_multiverse, validate_costs,
    estimated_roundtrip_bps, realized_quality, evaluate_quality,
)
from research_robustness import (
    walkforward_bounds, walkforward_report, synthetic_ohlc,
    gaussian_hmm_regimes, stylized_fact_score, multiverse_report,
)

ORDER = list(INTERVALS)



def market_chart_candles(op,hi,lo,close,timestamps,start,end,limit=260):
    start=max(start,end-limit)
    return [{
        "time":np.datetime_as_string(np.datetime64(timestamps[i]),unit="m"),
        "open":round(float(op[i]),6),"high":round(float(hi[i]),6),
        "low":round(float(lo[i]),6),"close":round(float(close[i]),6),
    } for i in range(start,end)]

def build_trade_ledger(outcomes,trace,timestamps,initial_deposit,risk_pct,sizing):
    """Faithful executed-trade accounting from the SAME Numba kernel as metrics.

    A trace comes from the independent held-out window (OOS); it must never
    be displayed as a whole-sample backtest. No fake entry/exit timestamps.
    """
    ledger=[]
    balance=float(initial_deposit)
    for idx,r in enumerate(outcomes):
        record=trace[idx]
        if not np.all(np.isfinite(record)):
            raise ValueError("El motor produjo una operación sin traza auditable.")
        entry_idx,exit_idx=int(record[0]),int(record[1])
        risk_base=balance if sizing=="compound" else initial_deposit
        cash_risk=risk_base*risk_pct/100.
        pnl=float(r)*cash_risk
        fees=float(record[7])*cash_risk
        gross=pnl+fees
        balance=max(0.,balance+pnl)
        ledger.append(dict(
            number=idx+1,
            entry_time=np.datetime_as_string(np.datetime64(timestamps[entry_idx]),unit="m"),
            exit_time=np.datetime_as_string(np.datetime64(timestamps[exit_idx]),unit="m"),
            entry_price=round(float(record[2]),8),
            exit_price=round(float(record[3]),8),
            average_price=round(float(record[5]),8),
            direction="long" if record[4]>0 else "short",
            result="win" if pnl>0 else "loss" if pnl<0 else "flat",
            pnl_usd=round(pnl,4),gross_usd=round(gross,4),
            costs_usd=round(fees,4),r_multiple=round(float(r),6),
            balance_usd=round(balance,4),
            duration_bars=max(1,exit_idx-entry_idx+1),
        ))
    return ledger



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


DEFAULT_RANGES = {
    "tech_period_min": 10, "tech_period_step": 5, "tech_period_max": 30,
    "ema_fast_min": 5, "ema_fast_step": 1, "ema_fast_max": 28,
    "ema_slow_min": 29, "ema_slow_step": 1, "ema_slow_max": 90,
    "rsi_period_min": 7, "rsi_period_step": 1, "rsi_period_max": 25,
    "rsi_oversold_min": 20, "rsi_oversold_step": 1, "rsi_oversold_max": 40,
    "breakout_lookback_min": 12, "breakout_lookback_step": 1,
    "breakout_lookback_max": 75,
    "london_high_sweep_buffer_min": 0, "london_high_sweep_buffer_step": 1,
    "london_high_sweep_buffer_max": 10,
    "london_low_sweep_buffer_min": 0, "london_low_sweep_buffer_step": 1,
    "london_low_sweep_buffer_max": 10,
    "asia_high_sweep_buffer_min": 0, "asia_high_sweep_buffer_step": 1,
    "asia_high_sweep_buffer_max": 10,
    "asia_low_sweep_buffer_min": 0, "asia_low_sweep_buffer_step": 1,
    "asia_low_sweep_buffer_max": 10,
    "previous_day_high_sweep_buffer_min": 0, "previous_day_high_sweep_buffer_step": 1,
    "previous_day_high_sweep_buffer_max": 10,
    "previous_day_low_sweep_buffer_min": 0, "previous_day_low_sweep_buffer_step": 1,
    "previous_day_low_sweep_buffer_max": 10,
}


def steps(r: dict[str,int], name: str) -> range:
    return range(r[name+"_min"], r[name+"_max"]+1, r[name+"_step"])


def checked_ranges(config: dict[str, Any]) -> dict[str, int]:
    r = {**DEFAULT_RANGES, **(config.get("indicator_ranges") or {})}
    bounds = {
        "tech_period": (2, 150),
        "ema_fast": (2, 100), "ema_slow": (10, 250),
        "rsi_period": (2, 60), "rsi_oversold": (5, 45),
        "breakout_lookback": (5, 250),
        "london_high_sweep_buffer": (0, 30),
        "london_low_sweep_buffer": (0, 30),
        "asia_high_sweep_buffer": (0, 30),
        "asia_low_sweep_buffer": (0, 30),
        "previous_day_high_sweep_buffer": (0, 30),
        "previous_day_low_sweep_buffer": (0, 30),
    }
    for name, (lower, upper) in bounds.items():
        a, step, b = (r[name + "_" + s] for s in ("min", "step", "max"))
        if any(not isinstance(v, int) or isinstance(v, bool) for v in (a, step, b)):
            raise ValueError("Los parámetros deben ser enteros: " + name)
        if not lower <= a <= b <= upper or not 1 <= step <= 30:
            raise ValueError("Rango inválido para " + name)
    if not any(fast+8<=slow for fast in steps(r,"ema_fast") for slow in steps(r,"ema_slow")):
        raise ValueError("Los rangos EMA no permiten una pareja rápida/lenta válida.")
    return r


def snap(r: dict[str,int], name: str, proposed: int, at_least: int | None = None) -> int:
    valid = (x for x in steps(r,name) if at_least is None or x>=at_least)
    return min(valid,key=lambda x:abs(x-proposed))


def random_gene(rng: random.Random, families: list[int],
                ranges: dict[str,int] | None = None) -> tuple[int,int,int]:
    r = ranges or DEFAULT_RANGES
    kind = rng.choice(families)
    if kind == 0:
        fasts = [f for f in steps(r,"ema_fast") if any(s>=f+8 for s in steps(r,"ema_slow"))]
        fast = rng.choice(fasts)
        slow = rng.choice([s for s in steps(r,"ema_slow") if s>=fast+8])
    elif kind == 1:
        fast = rng.choice(steps(r,"rsi_period"))
        slow = rng.choice(steps(r,"rsi_oversold"))
    elif kind == 2:
        fast, slow = 0, rng.choice(steps(r,"breakout_lookback"))
    elif FAMILIES[kind] in EXTENDED_FAMILIES:
        fast, slow = rng.choice(steps(r,"tech_period")), 0
    else:
        fast, slow = rng.choice(steps(r,FAMILIES[kind]+"_buffer")), 0
    return kind, fast, slow


def mutate_or_cross(rng: random.Random, a: tuple[int,int,int],
                    b: tuple[int,int,int], families: list[int],
                    ranges: dict[str,int] | None = None) -> tuple[int,int,int]:
    r = ranges or DEFAULT_RANGES
    if rng.random() < .13:
        return random_gene(rng, families, r)
    kind = rng.choice((a[0],b[0]))
    if kind==0:
        candidates = [f for f in steps(r,"ema_fast") if any(s>=f+8 for s in steps(r,"ema_slow"))]
        target_fast = rng.choice((a[1],b[1]))+rng.randint(-3,3)
        fast = min(candidates,key=lambda v:abs(v-target_fast))
        slow = snap(r,"ema_slow",rng.choice((a[2],b[2]))+rng.randint(-7,7),fast+8)
    elif kind==1:
        fast = snap(r,"rsi_period",rng.choice((a[1],b[1]))+rng.randint(-3,3))
        slow = snap(r,"rsi_oversold",rng.choice((a[2],b[2]))+rng.randint(-4,4))
    elif kind==2:
        fast = 0
        slow = snap(r,"breakout_lookback",rng.choice((a[2],b[2]))+rng.randint(-8,8))
    elif FAMILIES[kind] in EXTENDED_FAMILIES:
        fast = snap(r,"tech_period",rng.choice((a[1],b[1]))+rng.randint(-5,5))
        slow = 0
    else:
        fast = snap(r,FAMILIES[kind]+"_buffer",rng.choice((a[1],b[1]))+rng.randint(-2,2))
        slow = 0
    return kind,fast,slow


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


def run_advanced(source: pl.DataFrame, cfg: dict[str, Any], on_progress=None) -> dict:
    mode = cfg.get("mode", "random")
    modeling = cfg.get("modeling", "ohlc")
    sizing = cfg.get("sizing", "compound")
    multi = cfg.get("multi_tf", "individual")
    optimization = validate_objective(cfg.get("optimization_objective", "balanced"))
    funding=validate_funding(cfg.get("funding"))
    quality_cfg=validate_quality(cfg.get("quality"))
    wf_cfg=validate_walkforward(cfg.get("walk_forward"))
    mv_cfg=validate_multiverse(cfg.get("multiverse"))
    costs_cfg=validate_costs(cfg.get("costs"))
    if costs_cfg["use_in_backtest"] and not any(r["symbol"].upper()==cfg["symbol"].upper() for r in costs_cfg["instruments"]):
        raise ValueError("El instrumento no tiene especificaciones de costes; edita el catálogo o desactiva su uso.")
    modifiers=validate_advanced(cfg.get("advanced_modifiers"))
    advanced_active=is_active(modifiers)
    if modeling=="open" and (any(x!="market" for x in modifiers["entry_modes"]) or modifiers["dca_enabled"] or modifiers["pyramid_enabled"]):
        raise ValueError("Stop/Limit y escaleras DCA/Pirámide requieren modelado OHLC (no solo precios de apertura).")
    advanced_args=execution_arguments(modifiers)
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
    ranges = checked_ranges(cfg)
    capital = normalize_capital(cfg)
    risk_rules=normalize_risk_rules(capital.get("risk_rules") or {})
    schedule=validate_schedule(cfg.get("schedule"))
    exit_code=MODE_CODES[capital["exit_mode"]]
    source_timezone = cfg.get("source_timezone", "UTC")
    if source_timezone not in SOURCE_ZONES:
        raise ValueError("Zona horaria de los datos inválida.")
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
    if all(k in SITUATIONS for k in families) and not any(
        SITUATIONS[k][4] in directions for k in families
    ):
        raise ValueError("Las situaciones elegidas no generan señales en la dirección seleccionada.")

    def sides_for(gene):
        return ([side for side in directions if side == SITUATIONS[gene[0]][4]]
                if gene[0] in SITUATIONS else directions)

    sampling_model = 0 if modeling == "open" else 1
    per = [budget//len(jobs) + (i<budget%len(jobs)) for i in range(len(jobs))]
    all_trials: list[dict] = []
    warnings: list[str] = []
    if mode == "genetic":
        warnings.append("Selección genética por "+optimization+" calculada exclusivamente con trades IS; la evaluación OOS no influye en la selección.")

    max_gains=np.array([risk_rules[x] for x in ("max_daily_gain_pct","max_weekly_gain_pct","max_monthly_gain_pct","max_account_gain_pct")],dtype=np.float64)
    max_losses=np.array([risk_rules[x] for x in ("max_daily_loss_pct","max_weekly_loss_pct","max_monthly_loss_pct","max_account_loss_pct")],dtype=np.float64)
    current_cost_bps=float(cfg["cost_bps"])

    def simulate_configured(signals,op,hi,lo,close,atr,days,begin,end,side,pair,
                            entry_variant,allow_entry,forced_exit,weeks,months,cost_reference,trace=None):
        shared=(signals,op,hi,lo,close,atr,days,begin,end,
                exit_code,pair[0],pair[1],estimated_roundtrip_bps(costs_cfg,cfg["symbol"],cost_reference,side,cfg["cost_bps"]),side,sampling_model,
                cfg["risk_pct"],cfg["initial_deposit"],sizing=="fixed",
                capital["breakeven_enabled"],capital["breakeven_r"],
                capital["trailing_enabled"],capital["trailing_atr"],capital["max_bars_in_trade"],
                capital["max_trades_per_day"],capital["cooldown_bars"],
                cfg["prop_daily_pct"],cfg["prop_max_pct"],capital["stop_after_daily_pct"],
                allow_entry,forced_exit,weeks,months,max_gains,max_losses,
                int(risk_rules["max_consecutive_wins"]),int(risk_rules["max_consecutive_losses"]))
        if advanced_active:
            return simulate_advanced_orders(*shared,entry_variant,*advanced_args,trace)
        return simulate_capital(*shared,trace=trace)


    for (job_type, tf, htf), max_eval in zip(jobs,per):
        df = resample(source, tf)
        n = len(df)
        cut = int(n * cfg["is_ratio"] / 100)
        if cut < 250 or n-cut < 100:
            raise ValueError("El intervalo "+tf+" no tiene suficientes velas IS/OOS.")
        op,hi,lo,close = (df[k].to_numpy() for k in ("open","high","low","close"))
        timestamps = df["timestamp"].to_numpy()
        allow_entry,forced_exit,days,weeks,months=time_arrays(df,source_timezone,schedule)
        atr = atr_wilder(hi,lo,close,14)
        # Calibrate user-specified contract costs from IS prices only; freeze for OOS.
        cost_reference=float(np.median(op[:cut]))
        is_prices_cost={side:estimated_roundtrip_bps(costs_cfg,cfg["symbol"],
                         cost_reference,side,cfg["cost_bps"]) for side in directions}
        higher_bias = confirmed_higher_bias(source,df,htf) if htf else None
        references = {
            k: sweep_reference(df,k,source_timezone,tf)
            for k in families if k in SITUATIONS
        }
        seen: set[tuple] = set()
        evaluated: list[dict] = []
        processed_count=0

        def assess(gene: tuple[int,int,int], side: int, pair: tuple[float,float]) -> dict | None:
            nonlocal processed_count
            entry_variant=ENTRY_CODES[rng.choice(modifiers["entry_modes"])]
            key = (*gene, side, *pair, entry_variant)
            if key in seen:
                return None
            seen.add(key)
            kind,fast,slow = gene
            if kind in SITUATIONS:
                level, session_days, valid = references[kind]
                signals = sweep_signals(hi,lo,close,level,session_days,valid,
                                        SITUATIONS[kind][4],fast)
            elif FAMILIES[kind] in EXTENDED_FAMILIES:
                signals = technical_signals(FAMILIES[kind],fast,op,hi,lo,close)
            else:
                signals = make_signals(kind,fast,slow,close,hi,lo)
            if higher_bias is not None:
                signals = np.where(signals == higher_bias,signals,0).astype(np.int8)
            min_rr=risk_rules["min_reward_risk_ratio"]
            estimated_rr=modifiers["fixed_rr"] if modifiers["fixed_rr_enabled"] else pair[1] if exit_code in (0,2) else pair[1]/pair[0]
            if min_rr>0 and estimated_rr+1e-9<min_rr:
                return None
            r_is,d_is = simulate_configured(
                signals,op,hi,lo,close,atr,days,0,cut,side,pair,
                entry_variant,allow_entry,forced_exit,weeks,months,cost_reference,
            )
            metrics_is = summarize(
                r_is,d_is,cfg["risk_pct"],cfg["prop_daily_pct"],cfg["prop_max_pct"],
                sizing,cfg["initial_deposit"],
            )
            score, optimization_metrics = objective_score(
                optimization,r_is,d_is,days[:cut],cfg["risk_pct"],sizing,
                cfg["initial_deposit"],cfg["prop_daily_pct"],cfg["prop_max_pct"],
                seed=reproducible_seed(gene,side,pair),funding_config=funding,
            )
            if metrics_is["trades"] < max(4,cfg["min_trades"]):
                score = -1e8 + metrics_is["trades"]
            processed_count+=1
            if on_progress is not None and processed_count%4==0:
                on_progress(len(all_trials)+processed_count,budget,"explorando")
            return dict(
                gene=gene,side=side,exit_pair=pair,entry_variant=entry_variant,score=float(score),in_sample=metrics_is,
                reference_cost_price=cost_reference,
                timestamp=timestamps,
                trades_is=r_is,days_is=d_is,estimated_cost_bps=is_prices_cost[side],
                optimization_metrics=optimization_metrics,
                dataframe=(op,hi,lo,close,atr,days,cut,n,allow_entry,forced_exit,weeks,months),
                timeframe=tf,context=htf,model=job_type,
            )

        if mode == "random":
            attempts = 0
            while len(evaluated) < max_eval and attempts < max_eval*25:
                attempts += 1
                gene = random_gene(rng,families,ranges)
                pair = sample_exit(rng,capital)
                for side in sides_for(gene):
                    if len(evaluated) >= max_eval:
                        break
                    trial = assess(gene,side,pair)
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
                        gene = random_gene(rng,families,ranges)
                        pair = sample_exit(rng,capital)
                    else:
                        elite = sorted(population,key=lambda t:t["score"],reverse=True)[:max(2,len(population)//2)]
                        mother = rng.choice(elite)
                        father = rng.choice(elite)
                        gene = mutate_or_cross(rng,mother["gene"],father["gene"],families,ranges)
                        pair = mutate_exit(rng,capital,mother["exit_pair"],father["exit_pair"])
                    for side in sides_for(gene):
                        if len(new_gen) >= target:
                            break
                        trial = assess(gene,side,pair)
                        if trial is not None:
                            new_gen.append(trial)
                            evaluated.append(trial)
                if not new_gen:
                    break
                # Elitism is based ONLY on in-sample scores.
                population = sorted(population+new_gen,key=lambda t:t["score"],reverse=True)[:pop_size]
            while len(evaluated)<max_eval and attempts<max_eval*50:
                attempts += 1
                gene = random_gene(rng,families,ranges)
                pair = sample_exit(rng,capital)
                for side in sides_for(gene):
                    if len(evaluated) >= max_eval:
                        break
                    trial = assess(gene,side,pair)
                    if trial is not None:
                        evaluated.append(trial)
        all_trials.extend(evaluated)
        if on_progress is not None:
            on_progress(len(all_trials),budget,"explorando")

    # DSR's multiple-test correction counts attempted strategies on this SAME market.
    # Applying quality to all IS candidates before selecting the shortlist avoids
    # accidentally using OOS metrics to tune the quality thresholds.
    valid_trials=[]
    attempted_same_market=max(1,len(all_trials))
    for trial in all_trials:
        bars=trial["dataframe"]
        realized=realized_quality(trial["trades_is"],trial["days_is"],bars[5][:bars[6]],
                                  cfg["risk_pct"],sizing,trial["in_sample"],attempted_same_market)
        trial["quality_is"]=realized
        trial["quality_reasons_is"]=evaluate_quality(realized,quality_cfg)
        if not trial["quality_reasons_is"]:
            valid_trials.append(trial)
    # Only IS metrics determine the shortlist; never rank by held-out OOS.
    # Keep failed strategies visible and auditable; place successful IS filter
    # candidates first, then failed candidates as clearly rejected comparisons.
    rejected_trials=[t for t in all_trials if t["quality_reasons_is"]]
    sort_key=lambda t:(t["score"],t["in_sample"]["trades"])
    shortlist=(sorted(valid_trials,key=sort_key,reverse=True)
               +sorted(rejected_trials,key=sort_key,reverse=True))[:min(50,budget)]
    if len(valid_trials)<len(all_trials):
        warnings.append(f"Filtro de calidad IS: {len(all_trials)-len(valid_trials)} de {len(all_trials)} candidatos descartados antes de evaluar OOS.")
    if not valid_trials and all_trials:
        warnings.append("Los filtros de calidad rechazaron todos los candidatos en IS; reduce restricciones si deseas ampliar la exploración.")

    # Keep complete OHLC history, but do not retain a 1-byte-per-bar signal
    # vector for every evaluated candidate. With 5M bars and 2,000 trials
    # that would occupy ~10 GB before accounting for prices and trades.
    # Reconstruct deterministic signals only for the final IS-ranked shortlist.
    # Sort reconstruction by market scenario / family to reuse session references.
    cached_sweep_key = None
    cached_sweep_reference = None
    bias_cache = {}
    for trial in sorted(shortlist, key=lambda t: (
        t["model"], t["timeframe"], t["context"] or "", t["gene"][0]
    )):
        kind, fast, slow = trial["gene"]
        op, hi, lo, close = trial["dataframe"][:4]
        if kind in SITUATIONS:
            sweep_key = (trial["model"], trial["timeframe"], trial["context"], kind)
            if sweep_key != cached_sweep_key:
                reference_frame = pl.DataFrame({
                    "timestamp": trial["timestamp"], "high": hi, "low": lo,
                })
                cached_sweep_reference = sweep_reference(
                    reference_frame, kind, source_timezone, trial["timeframe"]
                )
                cached_sweep_key = sweep_key
            level, session_days, valid = cached_sweep_reference
            signals = sweep_signals(
                hi, lo, close, level, session_days, valid, SITUATIONS[kind][4], fast
            )
        elif FAMILIES[kind] in EXTENDED_FAMILIES:
            signals = technical_signals(FAMILIES[kind], fast, op, hi, lo, close)
        else:
            signals = make_signals(kind, fast, slow, close, hi, lo)
        if trial["context"] is not None:
            bias_key = (trial["model"], trial["timeframe"], trial["context"])
            if bias_key not in bias_cache:
                lower_frame = pl.DataFrame({"timestamp": trial["timestamp"]})
                bias_cache[bias_key] = confirmed_higher_bias(
                    source, lower_frame, trial["context"]
                )
            signals = np.where(signals == bias_cache[bias_key], signals, 0).astype(np.int8)
        trial["signals"] = signals
    cached_sweep_reference = None
    bias_cache.clear()
    candidates = []
    if on_progress is not None:
        on_progress(len(all_trials),budget,"validando")
    for i,trial in enumerate(shortlist):
        gene = trial["gene"]
        kind,fast,slow = gene
        op,hi,lo,cl,atr,days,cut,n,allow_entry,forced_exit,weeks,months = trial["dataframe"]
        pair=trial["exit_pair"]
        # Every written trace row is populated by the execution kernel.
        trade_trace=np.empty((max(1,n-cut),8),dtype=np.float64)
        r_oos,d_oos = simulate_configured(
            trial["signals"],op,hi,lo,cl,atr,days,cut,n,trial["side"],pair,
            trial["entry_variant"],allow_entry,forced_exit,weeks,months,trial["reference_cost_price"],trade_trace,
        )
        trade_ledger=build_trade_ledger(r_oos,trade_trace,trial["timestamp"],
                                        cfg["initial_deposit"],cfg["risk_pct"],sizing)
        if on_progress is not None:
            on_progress(i+1,len(shortlist),"validando")
        metrics_oos = summarize(
            r_oos,d_oos,cfg["risk_pct"],cfg["prop_daily_pct"],cfg["prop_max_pct"],
            sizing,cfg["initial_deposit"],
        )
        mc = bootstrap(
            r_oos,cfg["risk_pct"],cfg["mc_iterations"],cfg["prop_max_pct"],1000+i,sizing,
        )
        quality_oos=realized_quality(r_oos,d_oos,days[cut:n],cfg["risk_pct"],sizing,metrics_oos,attempted_same_market)
        reasons=["Filtro IS: "+reason for reason in trial["quality_reasons_is"]]
        reasons+=["Filtro OOS: "+reason for reason in evaluate_quality(quality_oos,quality_cfg)]

        # Chronological OOS windows. Pure uses the selected candidate unchanged;
        # reopt selects from an IS-discovered pool using ONLY the past before
        # each fold; it does NOT regenerate genetic strategies.
        wf_report=None
        if wf_cfg["enabled"] and i<wf_cfg["top_n"]:
            try:
                if cut<wf_cfg["min_training_bars"]:
                    raise ValueError("El tramo de entrenamiento es insuficiente para walk-forward.")
                windows=walkforward_bounds(cut,n,wf_cfg)
                fold_data=[]
                for begin,finish in windows:
                    chosen=trial
                    if wf_cfg["mode"]=="reopt":
                        pool=[x for x in shortlist if x["timeframe"]==trial["timeframe"] and x["model"]==trial["model"] and x["context"]==trial["context"]]
                        best=-1e15
                        for alternative in pool:
                            aa,bb,cc,dd,ee,days_alt,cut_alt,nn,allow_alt,force_alt,weeks_alt,months_alt=alternative["dataframe"]
                            train_r,train_days=simulate_configured(
                                alternative["signals"],aa,bb,cc,dd,ee,days_alt,0,begin,
                                alternative["side"],alternative["exit_pair"],alternative["entry_variant"],
                                allow_alt,force_alt,weeks_alt,months_alt,alternative["reference_cost_price"])
                            train_score=(float(np.mean(train_r)) if len(train_r)>0 else -1e12)
                            if train_score>best:
                                best=train_score
                                chosen=alternative
                    xx=chosen["dataframe"]
                    w_r,w_d=simulate_configured(
                        chosen["signals"],xx[0],xx[1],xx[2],xx[3],xx[4],xx[5],begin,finish,
                        chosen["side"],chosen["exit_pair"],chosen["entry_variant"],
                        xx[8],xx[9],xx[10],xx[11],chosen["reference_cost_price"])
                    fold_data.append((w_r,w_d,xx[5][begin:finish]))
                training_span=max(1,len(np.unique(days[:cut])))
                is_daily=trial["in_sample"]["net_return_pct"]/training_span
                wf_report=walkforward_report(windows,fold_data,is_daily,wf_cfg,
                    cfg["risk_pct"],sizing,cfg["initial_deposit"],cfg["prop_daily_pct"],cfg["prop_max_pct"])
                if wf_cfg["mode"]=="reopt":
                    wf_report["method"]="chronological_reselection_from_IS_discovered_pool"
                if not wf_report["eligible"]:
                    reasons.append("Walk-Forward: ratio de ventanas satisfactorias inferior al mínimo")
            except ValueError as exc:
                wf_report={"enabled":True,"eligible":False,"error":str(exc),"windows":[]}
                reasons.append("Walk-Forward: "+str(exc))

        # Synthetic universes are drawn solely from the IS historical window.
        # Recompute signals on synthetic OHLC, never reuse signals from reality.
        multiverse=None
        if mv_cfg["enabled"] and i<mv_cfg["top_n"]:
            try:
                lookback=min(cut,6000)
                offset=cut-lookback
                real_open=op[offset:cut]
                real_hi=hi[offset:cut]
                real_lo=lo[offset:cut]
                real_close=cl[offset:cut]
                regimes=gaussian_hmm_regimes(np.diff(np.log(real_close)),mv_cfg["regimes"])
                mv_random=np.random.default_rng(reproducible_seed(trial["gene"],trial["side"],pair)+91828)
                simulated=[]
                for u in range(mv_cfg["universes"]):
                    so,sh,sl,sc=synthetic_ohlc(real_open,real_hi,real_lo,real_close,mv_random,mv_cfg["mix"],u)
                    satr=atr_wilder(sh,sl,sc,14)
                    if kind in SITUATIONS or trial["context"] is not None:
                        synthetic_df=pl.DataFrame({"timestamp":trial["timestamp"][offset:cut],"open":so,"high":sh,"low":sl,"close":sc})
                    if kind in SITUATIONS:
                        lev,local_days,valid=sweep_reference(synthetic_df,kind,source_timezone,trial["timeframe"])
                        sg=sweep_signals(sh,sl,sc,lev,local_days,valid,SITUATIONS[kind][4],fast)
                    elif FAMILIES[kind] in EXTENDED_FAMILIES:
                        sg=technical_signals(FAMILIES[kind],fast,so,sh,sl,sc)
                    else:
                        sg=make_signals(kind,fast,slow,sc,sh,sl)
                    if trial["context"] is not None:
                        bias=confirmed_higher_bias(synthetic_df,synthetic_df,trial["context"])
                        sg=np.where(sg==bias,sg,0).astype(np.int8)
                    x_r,x_d=simulate_configured(
                        sg,so,sh,sl,sc,satr,days[offset:cut],0,lookback,
                        trial["side"],pair,trial["entry_variant"],
                        allow_entry[offset:cut],forced_exit[offset:cut],weeks[offset:cut],months[offset:cut],
                        trial["reference_cost_price"])
                    x_metrics=summarize(x_r,x_d,cfg["risk_pct"],cfg["prop_daily_pct"],cfg["prop_max_pct"],
                                        sizing,cfg["initial_deposit"])
                    x_style=stylized_fact_score(real_close,sc)
                    simulated.append((x_metrics["expectancy_r"],x_metrics["max_drawdown_pct"],x_style))
                multiverse=multiverse_report(simulated,mv_cfg,regimes)
                multiverse["historical_bars_used"]=lookback
                if not multiverse["eligible"]:
                    reasons.append("Multiverso: score de robustez o drawdown P95 fuera de los límites")
            except ValueError as exc:
                multiverse={"enabled":True,"eligible":False,"error":str(exc)}
                reasons.append("Multiverso: "+str(exc))
        # OOS funding diagnostics never influence candidate score or genetic selection.
        funding_is=trial["optimization_metrics"].get("funding_evaluation_is")
        funding_oos=None
        if funding["enabled"]:
            observed=np.unique(days[cut:n])
            oos_daily=_daily_returns(r_oos,d_oos,observed,cfg["risk_pct"],sizing)
            funding_oos=simulate_funding(oos_daily,np.isin(observed,d_oos),funding,
                                         seed=reproducible_seed(trial["gene"],trial["side"],pair)+1)
            if funding_is is not None and not funding_is["eligible"]:
                reasons.append("Tasa mínima de aprobación o tiempo P"+str(funding["pass_day_percentile"])+" no alcanzado en IS")
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
                  {"rsi_period":fast,"oversold":slow} if kind==1 else
                  {"lookback":slow} if kind==2 else
                  {"sweep_buffer_bps":fast})
        candidates.append(dict(
            id="candidate-"+str(i+1),family=FAMILIES[kind],params=params,
            timeframe=trial["timeframe"],context_timeframe=trial["context"],
            direction="long" if trial["side"] == 1 else "short",
            model=trial["model"],entry_mode=next(k for k,v in ENTRY_CODES.items() if v==trial["entry_variant"]),
            advanced_modifiers=modifiers,exit_mode=capital["exit_mode"],
            exit_parameters={exit_keys(capital)[0]:pair[0],exit_keys(capital)[1]:pair[1]},
            optimization_objective=optimization,optimization_score=trial["score"],
            optimization_metrics_is=trial["optimization_metrics"],
            funding_evaluation_is=funding_is,funding_evaluation_oos=funding_oos,
            in_sample=trial["in_sample"],
            quality_is=trial["quality_is"],quality_oos=quality_oos,
            walk_forward=wf_report,multiverse=multiverse,
            estimated_cost_bps=trial["estimated_cost_bps"],
            ledger=trade_ledger,ledger_scope="OOS",
            market_chart=market_chart_candles(op,hi,lo,cl,trial["timestamp"],cut,n),
            out_of_sample=metrics_oos,monte_carlo=mc,
            accepted=not reasons,reasons=reasons,
        ))
    warnings += [
        "Avanzado: Stop/Limit requieren ejecución OHLC intrabar conservadora; si se llenan durante una barra, SL/TP se evalúa desde la siguiente. DCA/pirámide comparten presupuesto de riesgo y no simulan margen, slippage ni liquidez.",
        "Walk-Forward: validación OOS cronológica; reoptimización significa re-selección del conjunto descubierto en IS utilizando únicamente datos anteriores a cada ventana, no búsqueda genética desde cero.",
        "Multiverso: universos sintéticos generados solo de IS, con HMM de estados gaussianos y recálculo de señales; no sustituyen testing de mercado ni validan causalidad.",
        "Objetivo de optimización: "+optimization+"; ranking, selección genética y shortlist usan solo datos IS.",
        "Sharpe/Sortino/Calmar usan anualización 252 con PnL realizado al cierre del trade; no reconstruyen mark-to-market diario.",
        "Pass Rate de fondeo usa las fases, límites, consistencia, días mínimos y percentiles configurados; es un proxy Monte Carlo con balance realizado, NO cumplimiento íntegro de reglas de la firma.",
        "Evaluación exploratoria: el split IS/OOS no sustituye walk-forward ni forward testing.",
        "Costes manuales: cuando se activan, spread/slippage, comisión y financiación estimada se convierten a bps con contratos introducidos por el usuario, calibrados solo con precio IS. Swap usa días estimados, no el holding real; MT5 no está conectado.",
        "El capital inicial y sizing afectan el balance estimado, no generan cotizaciones reales.",
        "El multi-TF combinado aplica únicamente una tendencia HTF EMA20/50 con barras completas.",
        "Barridas: Londres 08:00–16:00 (Europe/London), Tokio 09:00–17:00 (Asia/Tokyo); después del cierre de la sesión y hasta medianoche local. Confirma la zona horaria de origen del CSV.",
        "Monte Carlo remuestrea operaciones OOS; no simula caminos de mercado.",
        "Los límites de pérdida y operaciones usan balance realizado, no drawdown flotante intrabar.",
        "BE y trailing se actualizan tras cerrar vela. Sin datos tick, los gaps y salidas parciales no están completamente modelados.",
        "Horarios y filtros por día se calculan en UTC fijo; se respetan cierres forzados al precio de la primera vela disponible.",
        "Límites semanales/mensuales y rachas se evalúan sobre balance realizado; no equivalen a protección intrabar de fondeo.",
    ]
    return dict(
        tested=len(all_trials),accepted=sum(1 for c in candidates if c["accepted"]),
        total_shortlist=len(shortlist),
        optimization_objective=optimization,funding_config=funding,quality_config=quality_cfg,
        cost_config=costs_cfg,walk_forward_config=wf_cfg,multiverse_config=mv_cfg,candidates=candidates,warnings=warnings,
    )
