"""TradingQuant API — phase 1. Research only, no live order execution."""
from __future__ import annotations
import os
import uuid
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from engine import load_data, describe_data
from engine_advanced import run_advanced
from engine_capital import normalize_capital,normalize_risk_rules
from engine_schedule import validate_schedule
from optimization_objectives import OBJECTIVES
from funding_simulator import validate_funding
from advanced_modifiers import validate_advanced
from research_validation import validate_quality,validate_walkforward,validate_multiverse,validate_costs
from execution_jobs import JOBS
from preflight import preflight
from dataset_uploads import UploadManager,UploadInit,CHUNK_BYTES
from mt5_gateway import MT5Bridge,ConnectRequest,HistoryRequest

DATA_DIR = Path(os.getenv("TRADINGQUANT_DATA_DIR", "./data/uploads")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = min(max(int(os.getenv("TRADINGQUANT_MAX_UPLOAD_MB", "150")), 1), 4096) * 1024 * 1024
app = FastAPI(title="TradingQuant Scientific API", version="0.1.0")
UPLOADS=UploadManager(DATA_DIR)
MT5=MT5Bridge(DATA_DIR.parent)
class PrivateResearchMiddleware(BaseHTTPMiddleware):
    """Optional single-user API access control for public Docker deployments.

    This is a service-level shared token, not full user authentication.
    Keep the token out of NEXT_PUBLIC env vars and source control.
    """
    async def dispatch(self,request:Request,call_next):
        if request.url.path.startswith("/api/") and request.method!="OPTIONS":
            if os.getenv("TRADINGQUANT_REQUIRE_AUTH","0")=="1":
                key=os.getenv("TRADINGQUANT_ACCESS_TOKEN","")
                if not key:
                    return JSONResponse({"detail":"Falta configurar el token privado del servidor."},status_code=503)
                authorization=request.headers.get("authorization","")
                if not secrets.compare_digest(authorization,"Bearer "+key):
                    return JSONResponse({"detail":"Token de acceso inválido o ausente."},status_code=401)
        if request.url.path.startswith("/api/") and request.method!="OPTIONS" and os.getenv("TRADINGQUANT_REQUIRE_ACCOUNT","0")=="1":
            if not request.url.path.startswith("/api/accounts/") and request.url.path!="/api/auth/check":
                # Account selection is not a secret/token. It identifies the
                # authenticated MT5 terminal currently attached to this PC.
                account_id=request.headers.get("x-tradingquant-account","")
                if not account_id or account_id!=MT5.active_id:
                    return JSONResponse({"detail":"Conecta una cuenta MT5 en Principal → Cuentas antes de acceder al laboratorio."},status_code=403)
        return await call_next(request)

# Register security before CORS so preflight and all error responses keep
# the correct allowed-origin headers.
app.add_middleware(PrivateResearchMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("TRADINGQUANT_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if x.strip()],
    allow_origin_regex=r"https://tradingquant(?:-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type","Authorization","X-Chunk-SHA256","X-TradingQuant-Account"],
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
    optimization_objective: Literal["balanced","sharpe","sortino","calmar","net_profit","min_drawdown","profit_factor","expectancy","win_rate","recovery_factor","funding_pass_rate"] = "balanced"
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
    capital: dict | None = None
    schedule: dict | None = None
    funding: dict | None = None
    advanced_modifiers: dict | None = None
    quality: dict | None = None
    walk_forward: dict | None = None
    multiverse: dict | None = None
    costs: dict | None = None
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
        try:
            capital=normalize_capital({"capital": self.capital, "rr": self.rr, "atr_multiplier": self.atr_multiplier})
            normalize_risk_rules(capital.get("risk_rules") or {})
            validate_schedule(self.schedule)
            validate_funding(self.funding)
            validate_advanced(self.advanced_modifiers)
            validate_quality(self.quality)
            validate_walkforward(self.walk_forward)
            validate_multiverse(self.multiverse)
            validate_costs(self.costs)
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(str(exc)) from exc
        if self.macro_indicators:
            raise ValueError("Las series macroeconómicas necesitan datos point-in-time antes de ejecutar; aún no están habilitadas.")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("El inicio del periodo no puede ser posterior al final.")
        if self.multi_tf != "individual" and len(set(self.timeframes)) < 2:
            raise ValueError("Multi-TF combinado requiere 2 intervalos.")
        if self.prop_daily_pct > self.prop_max_pct:
            raise ValueError("El límite diario no debe superar el máximo total.")
        return self

@app.get("/api/auth/check")
def check_access():
    return {"authorized":True,"research_enabled":True}

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0", "live_trading_enabled": False}



@app.get("/api/accounts/status")
def accounts_status():
    return MT5.list()

@app.post("/api/accounts/connect")
def accounts_connect(payload:ConnectRequest):
    return MT5.connect(payload)

class ActivateAccount(BaseModel):
    account_id:str=Field(min_length=5,max_length=180)

@app.post("/api/accounts/activate")
def accounts_activate(payload:ActivateAccount):
    return MT5.activate(payload.account_id)

@app.get("/api/accounts/symbols/all")
def symbols_all():
    return MT5.all_symbols()

@app.get("/api/accounts/{account_id}/symbols")
def account_symbols(account_id:str):
    return MT5.symbols(account_id,refresh=True)

@app.get("/api/accounts/{account_id}/symbols/{symbol}/specification")
def account_specification(account_id:str,symbol:str):
    return MT5.specification(account_id,symbol)

@app.post("/api/accounts/history/import")
def account_history_import(payload:HistoryRequest):
    return MT5.import_history(payload,DATA_DIR)

@app.post("/api/datasets/uploads",status_code=201)
def begin_chunked_upload(options:UploadInit):
    """Return upload id and max chunk size. Browser never sends one huge POST."""
    return {**UPLOADS.begin(options),"chunk_bytes":CHUNK_BYTES}

@app.put("/api/datasets/uploads/{upload_id}/chunks/{index}")
async def upload_chunk(upload_id:str,index:int,request:Request):
    size_header=request.headers.get("content-length")
    if size_header and int(size_header)>CHUNK_BYTES:
        raise HTTPException(413,"Bloque demasiado grande (máximo 2 MiB).")
    parts=[]
    total=0
    async for part in request.stream():
        total+=len(part)
        if total>CHUNK_BYTES:
            raise HTTPException(413,"El bloque excede 2 MiB.")
        parts.append(part)
    sha=request.headers.get("x-chunk-sha256","")
    return UPLOADS.write(upload_id,index,b"".join(parts),sha)

@app.post("/api/datasets/uploads/{upload_id}/complete",status_code=202)
def complete_chunked_upload(upload_id:str):
    return UPLOADS.finish(upload_id)

@app.get("/api/datasets/uploads/{upload_id}")
def check_chunked_upload(upload_id:str):
    return UPLOADS.status(upload_id)

@app.get("/api/local/inbox")
def list_local_inbox():
    """List CSV files manually placed in the PC inbox. Never scan other folders."""
    if os.getenv("TRADINGQUANT_LOCAL_MODE")!="1":
        raise HTTPException(404,"Importación directa deshabilitada fuera del modo local.")
    inbox=DATA_DIR.parent/"inbox"
    inbox.mkdir(parents=True,exist_ok=True)
    files=[]
    for p in sorted(inbox.iterdir(),key=lambda x:x.name.lower()):
        if p.is_file() and not p.is_symlink() and p.suffix.lower()==".csv":
            stat=p.stat()
            files.append({"filename":p.name,"size_bytes":stat.st_size})
        if len(files)>=200:
            break
    return {"files":files,"local":True,"max_bytes":MAX_BYTES}


class LocalImportRequest(BaseModel):
    filename:str=Field(min_length=5,max_length=200)


@app.post("/api/local/import",status_code=202)
def import_local_csv(payload:LocalImportRequest):
    if os.getenv("TRADINGQUANT_LOCAL_MODE")!="1":
        raise HTTPException(404,"Importación directa deshabilitada fuera del modo local.")
    return UPLOADS.import_local(payload.filename,DATA_DIR.parent/"inbox")


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


def dataset_path(dataset_id:str)->Path:
    try:
        file_id=uuid.UUID(dataset_id)
    except (ValueError,TypeError,AttributeError):
        raise HTTPException(400,"Dataset id inválido.") from None
    path=DATA_DIR/f"{file_id}.csv"
    if not path.is_file():
        raise HTTPException(404,"Dataset no encontrado en la API. Reimporta el archivo CSV.")
    return path

@app.post("/api/explorations/preflight")
def preflight_exploration(config:ExplorationRequest):
    path=dataset_path(config.dataset_id)
    try:
        frame=load_data(path)
        return preflight(frame,config.model_dump())
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc

@app.post("/api/explorations/start",status_code=202)
def start_exploration(config:ExplorationRequest):
    path=dataset_path(config.dataset_id)
    try:
        return JOBS.launch(path,config.model_dump(),load_data,run_advanced)
    except ValueError as exc:
        raise HTTPException(429,str(exc)) from exc

@app.get("/api/explorations/jobs/{job_id}")
def job_status(job_id:str):
    job=JOBS.status(job_id)
    if job is None:
        raise HTTPException(404,"Exploración no encontrada en este proceso de API.")
    return job

@app.get("/api/explorations/jobs/{job_id}/result")
def job_result(job_id:str):
    state=JOBS.status(job_id)
    if state is None:
        raise HTTPException(404,"Exploración no encontrada en este proceso de API.")
    if state["status"]=="failed":
        raise HTTPException(422,state.get("error") or "La exploración falló.")
    if state["status"]!="completed":
        raise HTTPException(409,"La exploración sigue en proceso.")
    return JOBS.result(job_id)
