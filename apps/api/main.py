"""TradingQuant API — phase 1. Research only, no live order execution."""
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from engine import load_data, describe_data
from engine_advanced import run_advanced

DATA_DIR = Path(os.getenv("TRADINGQUANT_DATA_DIR", "./data/uploads")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 150 * 1024 * 1024
app = FastAPI(title="TradingQuant Scientific API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("TRADINGQUANT_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class IndicatorRanges(BaseModel):
    ema_fast_min: int = Field(default=5, ge=2, le=100)
    ema_fast_step: int = Field(default=1, ge=1, le=30)
    ema_fast_max: int = Field(default=28, ge=2, le=100)
    ema_slow_min: int = Field(default=29, ge=10, le=250)
    ema_slow_step: int = Field(default=1, ge=1, le=30)
    ema_slow_max: int = Field(default=90, ge=10, le=250)
    rsi_period_min: int = Field(default=7, ge=2, le=60)
    rsi_period_step: int = Field(default=1, ge=1, le=30)
    rsi_period_max: int = Field(default=25, ge=2, le=60)
    rsi_oversold_min: int = Field(default=20, ge=5, le=45)
    rsi_oversold_step: int = Field(default=1, ge=1, le=30)
    rsi_oversold_max: int = Field(default=40, ge=5, le=45)
    breakout_lookback_min: int = Field(default=12, ge=5, le=250)
    breakout_lookback_step: int = Field(default=1, ge=1, le=30)
    breakout_lookback_max: int = Field(default=75, ge=5, le=250)
    london_high_sweep_buffer_min: int = Field(default=0, ge=0, le=30)
    london_high_sweep_buffer_step: int = Field(default=1, ge=1, le=30)
    london_high_sweep_buffer_max: int = Field(default=10, ge=0, le=30)
    london_low_sweep_buffer_min: int = Field(default=0, ge=0, le=30)
    london_low_sweep_buffer_step: int = Field(default=1, ge=1, le=30)
    london_low_sweep_buffer_max: int = Field(default=10, ge=0, le=30)
    asia_high_sweep_buffer_min: int = Field(default=0, ge=0, le=30)
    asia_high_sweep_buffer_step: int = Field(default=1, ge=1, le=30)
    asia_high_sweep_buffer_max: int = Field(default=10, ge=0, le=30)
    asia_low_sweep_buffer_min: int = Field(default=0, ge=0, le=30)
    asia_low_sweep_buffer_step: int = Field(default=1, ge=1, le=30)
    asia_low_sweep_buffer_max: int = Field(default=10, ge=0, le=30)
    previous_day_high_sweep_buffer_min: int = Field(default=0, ge=0, le=30)
    previous_day_high_sweep_buffer_step: int = Field(default=1, ge=1, le=30)
    previous_day_high_sweep_buffer_max: int = Field(default=10, ge=0, le=30)
    previous_day_low_sweep_buffer_min: int = Field(default=0, ge=0, le=30)
    previous_day_low_sweep_buffer_step: int = Field(default=1, ge=1, le=30)
    previous_day_low_sweep_buffer_max: int = Field(default=10, ge=0, le=30)

    @model_validator(mode="after")
    def valid_bounds(self):
        for prefix in ("ema_fast", "ema_slow", "rsi_period", "rsi_oversold", "breakout_lookback", "london_high_sweep_buffer", "london_low_sweep_buffer", "asia_high_sweep_buffer", "asia_low_sweep_buffer", "previous_day_high_sweep_buffer", "previous_day_low_sweep_buffer"):
            if getattr(self, prefix + "_min") > getattr(self, prefix + "_max"):
                raise ValueError("El mínimo de " + prefix + " supera el máximo.")
        if self.ema_fast_min + 8 > self.ema_slow_max:
            raise ValueError("Los rangos EMA no permiten una pareja válida.")
        return self


class ExplorationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    dataset_id: str
    symbol: str = Field(min_length=2, max_length=16)
    timeframe: Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d"] = "5m"
    timeframes: list[Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d"]] = Field(default_factory=lambda: ["5m"], min_length=1, max_length=7)
    start_date: str = ""
    end_date: str = ""
    initial_deposit: float = Field(default=5000, ge=100, le=100000000)
    mode: Literal["random","genetic"] = "random"
    modeling: Literal["open","ohlc"] = "ohlc"
    sizing: Literal["compound","fixed"] = "compound"
    multi_tf: Literal["individual","combined","both"] = "individual"
    generations: int = Field(default=8, ge=2, le=30)
    candidates: int = Field(default=100, ge=10, le=2000)
    families: list[Literal["ema_cross", "rsi_reversion", "breakout",
                           "london_high_sweep", "london_low_sweep",
                           "asia_high_sweep", "asia_low_sweep",
                           "previous_day_high_sweep", "previous_day_low_sweep"]]
    indicator_ranges: IndicatorRanges = Field(default_factory=IndicatorRanges)
    macro_indicators: list[str] = Field(default_factory=list, max_length=200)
    macro_rules: dict[str, dict] = Field(default_factory=dict)
    source_timezone: Literal["UTC","Europe/London","Europe/Athens","America/New_York","America/Santo_Domingo","Asia/Tokyo"] = "UTC"
    direction: Literal["long", "short", "both"] = "both"
    risk_pct: float = Field(default=0.5, ge=0.05, le=2)
    rr: float = Field(default=1, ge=0.2, le=5)
    atr_multiplier: float = Field(default=1.5, ge=0.5, le=6)
    cost_bps: float = Field(default=2, ge=0, le=100)
    is_ratio: int = Field(default=70, ge=50, le=85)
    min_trades: int = Field(default=12, ge=1, le=100)
    mc_iterations: Literal[100, 500, 1000] = 500
    prop_daily_pct: float = Field(default=3, ge=0.5, le=10)
    prop_max_pct: float = Field(default=10, ge=1, le=20)

    @model_validator(mode="after")
    def valid(self):
        if not self.families:
            raise ValueError("Selecciona al menos una familia de señales.")
        if self.macro_indicators:
            raise ValueError("Las series macroeconómicas necesitan datos point-in-time antes de ejecutar; aún no están habilitadas.")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("El inicio del periodo no puede ser posterior al final.")
        if self.multi_tf != "individual" and len(set(self.timeframes)) < 2:
            raise ValueError("Multi-TF combinado requiere 2 intervalos.")
        if self.prop_daily_pct > self.prop_max_pct:
            raise ValueError("El límite diario no debe superar el máximo total.")
        return self

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0", "live_trading_enabled": False}

@app.post("/api/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Se requiere un archivo .csv.")
    dataset_id = str(uuid.uuid4())
    path = DATA_DIR / (dataset_id + ".csv")
    total = 0
    try:
        with path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise HTTPException(413, "Máximo 150 MB por CSV.")
                out.write(chunk)
        if not total:
            raise HTTPException(400, "El archivo está vacío.")
        bars = load_data(path)
        info = describe_data(bars)
        return {
            "id": dataset_id,
            "filename": Path(file.filename).name[:150],
            "rows": info["rows"],
            "start": info["start"],
            "end": info["end"],
            "timeframe": "source",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    except (ValueError, OSError) as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()

@app.post("/api/explorations/run")
def explore(config: ExplorationRequest):
    try:
        dataset_uuid = uuid.UUID(config.dataset_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "Dataset id inválido.") from None
    path = DATA_DIR / f"{dataset_uuid}.csv"
    if not path.is_file():
        raise HTTPException(404, "Dataset no encontrado en esta instancia de la API. Reimporta el CSV.")
    try:
        frame = load_data(path)
        result = run_advanced(frame, config.model_dump())
        return {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset_id": config.dataset_id,
            "config": config.model_dump(),
            **result,
        }
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
