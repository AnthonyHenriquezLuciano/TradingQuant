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

from engine import load_data, run_exploration, describe_data

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

class ExplorationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    dataset_id: str
    symbol: str = Field(min_length=2, max_length=16)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h"] = "5m"
    mode: Literal["random"] = "random"
    candidates: int = Field(default=40, ge=1, le=100)
    families: list[Literal["ema_cross", "rsi_reversion", "breakout"]]
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
        result = run_exploration(frame, config.model_dump())
        return {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset_id": config.dataset_id,
            "config": config.model_dump(),
            **result,
        }
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
