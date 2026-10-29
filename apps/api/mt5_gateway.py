"""Windows-only, read-only MetaTrader 5 local terminal gateway.

MT5 Python talks to an installed desktop terminal, not to an MT5 cloud API.
Passwords are never requested or persisted. Attach only to an already signed-in
terminal, optionally at an explicit executable path; never call order_send.
All MT5 calls are serialized: the Python integration has one active terminal
connection per Python process. Multiple accounts can be registered and
revisited via their own terminal installations, not queried simultaneously.
"""
from __future__ import annotations
import csv
import json
import os
import platform
import re
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

TF_KEYS = {
    "1m": "TIMEFRAME_M1", "5m": "TIMEFRAME_M5", "15m": "TIMEFRAME_M15",
    "30m": "TIMEFRAME_M30", "1h": "TIMEFRAME_H1", "4h": "TIMEFRAME_H4",
    "1d": "TIMEFRAME_D1",
}
LOCAL_MODE = "TRADINGQUANT_LOCAL_MODE"
TERMINAL_ALLOWED = "TRADINGQUANT_MT5_READ_ONLY"


class ConnectRequest(BaseModel):
    terminal_path: str | None = Field(default=None, max_length=1024)
    label: str | None = Field(default=None, max_length=90)


class HistoryRequest(BaseModel):
    account_id: str = Field(min_length=6, max_length=180)
    symbol: str = Field(min_length=1, max_length=90)
    timeframe: str = "1m"
    start: datetime
    end: datetime


class MT5Bridge:
    def __init__(self, base: Path):
        self.base = Path(base).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.store = self.base / "mt5_accounts.json"
        self.lock = threading.RLock()
        self.active_id: str | None = None
        self.accounts: dict[str,dict[str,Any]] = {}
        try:
            raw=json.loads(self.store.read_text(encoding="utf-8"))
            if isinstance(raw,dict):
                self.accounts={str(k):v for k,v in raw.items() if isinstance(v,dict)}
        except (ValueError,OSError):
            pass

    def _mt5(self):
        if os.getenv(LOCAL_MODE)!="1":
            raise HTTPException(404,"MetaTrader 5 solo está disponible en el modo local.")
        if platform.system()!="Windows":
            raise HTTPException(503,"La integración MetaTrader5 requiere Windows con el terminal MT5 instalado.")
        try:
            import MetaTrader5 as mt5  # optional on Linux CI; Windows desktop only
        except ImportError:
            raise HTTPException(503,"Instala el paquete MetaTrader5 en Python 3.12 mediante el iniciador local.") from None
        return mt5

    def _save(self):
        # Only account numbers, public server names, terminal paths, and
        # cached public instrument specifications; NEVER account passwords.
        tmp=self.store.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.accounts,ensure_ascii=False,indent=2),encoding="utf-8")
        tmp.replace(self.store)

    def _public(self,key:str,entry:dict):
        return {"id":key,"login":entry["login"],"server":entry["server"],
            "broker":entry.get("broker",""),"currency":entry.get("currency",""),
            "leverage":entry.get("leverage",0),"balance":entry.get("balance",0.0),
            "equity":entry.get("equity",0.0),"name":entry.get("label",""),
            "terminal_path":entry.get("terminal_path",""),
            "status":"connected" if key==self.active_id else "saved",
            "symbols_count":len(entry.get("symbols",[]))}
    def list(self):
        with self.lock:
            return {"active_id":self.active_id,
                "accounts":[self._public(k,v) for k,v in self.accounts.items()],
                "read_only":True,
                "multiple_terminals_note":"Solo un terminal activo por proceso Python; puedes registrar varias instalaciones MT5."}

    def _snapshot_symbol(self,s):
        x=s._asdict() if hasattr(s,"_asdict") else vars(s)
        take=("name","description","path","visible","select","trade_mode",
              "digits","point","spread","spread_float","trade_tick_size",
              "trade_tick_value","trade_tick_value_profit","trade_tick_value_loss",
              "trade_contract_size","volume_min","volume_max","volume_step",
              "currency_base","currency_profit","currency_margin","swap_long",
              "swap_short","swap_mode","trade_stops_level","trade_freeze_level",
              "trade_calc_mode")
        result={k:x.get(k) for k in take}
        result["name"]=str(x.get("name",""))
        # Costs returned by MT5 are a CURRENT symbol snapshot, not historical.
        result["cost_source"]="mt5_current_symbol_snapshot"
        result["commission_roundtrip_account_currency"]=None
        result["commission_available"]=False
        return result

    def _attach(self,mt5,terminal_path:str | None):
        if terminal_path:
            p=Path(terminal_path).expanduser()
            if not p.is_file() or p.name.lower() not in ("terminal64.exe","terminal.exe"):
                raise HTTPException(422,"Selecciona la ruta existente a terminal64.exe de una instalación de MT5.")
            ok=mt5.initialize(path=str(p),timeout=12000)
        else:
            ok=mt5.initialize(timeout=12000)
        if not ok:
            raise HTTPException(503,f"MT5 no está conectado. Abre el terminal e inicia sesión antes de vincularlo. Error: {mt5.last_error()}")
        info=mt5.account_info()
        terminal=mt5.terminal_info()
        if info is None or terminal is None:
            mt5.shutdown()
            raise HTTPException(503,"No hay una cuenta abierta en ese terminal MT5.")
        return info,terminal

    def connect(self,payload:ConnectRequest):
        with self.lock:
            mt5=self._mt5()
            mt5.shutdown()
            acc,terminal=self._attach(mt5,payload.terminal_path)
            info=acc._asdict()
            tid=str(info.get("login",""))+"@"+str(info.get("server",""))
            if not tid or tid=="@":
                mt5.shutdown()
                raise HTTPException(503,"El terminal no devolvió identificador y servidor válidos.")
            original=self.accounts.get(tid,{})
            x=terminal._asdict()
            path=payload.terminal_path or x.get("path","")
            # terminal_info.path is usually the terminal data path, not exe;
            # only retain explicit user-selected executable paths.
            if not payload.terminal_path: path=""
            registered={
                "login":int(info["login"]),"server":str(info["server"]),
                "broker":str(info.get("company","")),"currency":str(info.get("currency","")),
                "leverage":int(info.get("leverage",0)),"balance":float(info.get("balance",0)),
                "equity":float(info.get("equity",0)),
                "label":(payload.label or original.get("label") or f"MT5 {info['login']}")[:90],
                "terminal_path":path,
                "symbols":original.get("symbols",[]),
            }
            self.accounts[tid]=registered
            self.active_id=tid
            self._save()
            return {"account":self._public(tid,registered),"terminal_connected":True,
                    "read_only":True,"warning":"No se transmiten credenciales ni se ejecutan operaciones."}

    def activate(self,account_id:str):
        with self.lock:
            entry=self.accounts.get(account_id)
            if not entry: raise HTTPException(404,"Cuenta no registrada. Conecta MT5 primero.")
            mt5=self._mt5()
            mt5.shutdown()
            acc,term=self._attach(mt5,entry.get("terminal_path") or None)
            actual=str(acc.login)+"@"+str(acc.server)
            if actual!=account_id:
                mt5.shutdown()
                self.active_id=None
                raise HTTPException(409,"Este terminal tiene iniciada otra cuenta. Selecciona su instalación MT5 o cambia de sesión desde MetaTrader 5; no usaremos contraseñas.")
            self.active_id=account_id
            entry["balance"]=float(acc.balance)
            entry["equity"]=float(acc.equity)
            self._save()
            return {"account":self._public(account_id,entry),"terminal_connected":True}

    def ensure_active(self, account_id:str):
        with self.lock:
            if not self.active_id or account_id!=self.active_id:
                raise HTTPException(403,"Selecciona y conecta una cuenta MT5 antes de utilizar el laboratorio.")
            return self.accounts[account_id]

    def _verified(self,mt5,account_id):
        self.ensure_active(account_id)
        a=mt5.account_info()
        if a is None or str(a.login)+"@"+str(a.server)!=account_id:
            self.active_id=None
            raise HTTPException(409,"La cuenta activa del terminal MT5 cambió. Vuelve a conectar la cuenta.")

    def symbols(self,account_id:str,refresh:bool=True):
        with self.lock:
            entry=self.ensure_active(account_id)
            mt5=self._mt5()
            self._verified(mt5,account_id)
            if refresh:
                raw=mt5.symbols_get()
                if raw is None:
                    raise HTTPException(502,f"No se pudieron consultar símbolos MT5: {mt5.last_error()}")
                entry["symbols"]=sorted([self._snapshot_symbol(s) for s in raw],
                                         key=lambda x:x["name"])
                self._save()
            return {"account_id":account_id,"symbols":entry.get("symbols",[]),
                    "total":len(entry.get("symbols",[])),"snapshot":True}

    def all_symbols(self):
        with self.lock:
            groups={}
            for account_id,entry in self.accounts.items():
                for s in entry.get("symbols",[]):
                    groups.setdefault(s["name"],[]).append(account_id)
            return {"symbols":[{"symbol":sym,"accounts":ids} for sym,ids in sorted(groups.items())],
                    "note":"Unión de inventarios almacenados por cuenta; algunas cuentas pueden estar desconectadas."}

    def specification(self,account_id:str,symbol:str):
        with self.lock:
            self.ensure_active(account_id)
            mt5=self._mt5()
            self._verified(mt5,account_id)
            info=mt5.symbol_info(symbol)
            if info is None:
                raise HTTPException(404,"El símbolo no está disponible en la cuenta activa.")
            result=self._snapshot_symbol(info)
            return {"account_id":account_id,"symbol":result,
                    "costs_note":"Spread y swaps actuales, no series históricas; MT5 no ofrece una comisión futura universal por símbolo. Estima comisión y deslizamiento por separado.",
                    "account_currency":self.accounts[account_id]["currency"]}

    def import_history(self,p:HistoryRequest,data_dir:Path):
        with self.lock:
            self.ensure_active(p.account_id)
            mt5=self._mt5()
            self._verified(mt5,p.account_id)
            if p.timeframe not in TF_KEYS:
                raise HTTPException(422,"Temporalidad no compatible.")
            if p.end<=p.start or (p.end-p.start).days>365*15:
                raise HTTPException(422,"Selecciona un rango de fechas válido (máximo 15 años).")
            if not re.fullmatch(r"[\w.+#-]{1,90}",p.symbol):
                raise HTTPException(422,"Nombre de símbolo no admitido.")
            spec=mt5.symbol_info(p.symbol)
            if spec is None:
                raise HTTPException(404,"Este símbolo no está disponible en MT5.")
            if not mt5.symbol_select(p.symbol,True):
                raise HTTPException(502,f"No se pudo seleccionar el símbolo: {mt5.last_error()}")
            period=getattr(mt5,TF_KEYS[p.timeframe])
            start=p.start.replace(tzinfo=timezone.utc) if p.start.tzinfo is None else p.start.astimezone(timezone.utc)
            end=p.end.replace(tzinfo=timezone.utc) if p.end.tzinfo is None else p.end.astimezone(timezone.utc)
            if end>datetime.now(timezone.utc):end=datetime.now(timezone.utc)
            # Data are UTC from MetaTrader 5. The terminal may have fewer
            # bars than requested (Tools > Options > Charts > Max bars).
            rates=mt5.copy_rates_range(p.symbol,period,start,end)
            if rates is None or len(rates)<300:
                raise HTTPException(422,"MT5 no devolvió 300 velas completas. Revisa fechas, Max. bars in chart y carga el histórico del símbolo en MT5.")
            if len(rates)>5_000_000:
                raise HTTPException(413,"Más de cinco millones de velas; divide el período.")
            uid=str(uuid.uuid4())
            data_dir.mkdir(parents=True,exist_ok=True)
            path=data_dir/(uid+".csv")
            try:
                with path.open("w",newline="",encoding="utf-8") as f:
                    wr=csv.writer(f,delimiter="\t")
                    wr.writerow(["<DATE>","<TIME>","<OPEN>","<HIGH>","<LOW>","<CLOSE>","<TICKVOL>","<VOL>","<SPREAD>"])
                    for bar in rates:
                        t=datetime.fromtimestamp(int(bar["time"]),tz=timezone.utc)
                        wr.writerow([t.strftime("%Y.%m.%d"),t.strftime("%H:%M:%S"),
                            float(bar["open"]),float(bar["high"]),float(bar["low"]),
                            float(bar["close"]),int(bar["tick_volume"]),float(bar["real_volume"]),
                            int(bar["spread"])])
            except Exception:
                path.unlink(missing_ok=True)
                raise
            return {"id":uid,"filename":f"{p.symbol}_{p.timeframe}_MT5.csv",
                "rows":len(rates),"start":str(start),"end":str(end),
                "timeframe":p.timeframe,"uploaded_at":datetime.now(timezone.utc).isoformat(),
                "source":"MT5_TERMINAL","account_id":p.account_id,
                "symbol":p.symbol,"market_timezone":"UTC",
                "specification":self._snapshot_symbol(spec),
                "warning":"El histórico disponible depende de Max. bars in chart. Spread y comisión históricos no se obtienen de una especificación actual."}
