"""Resumable, bounded MT5 CSV chunk uploads with streaming background validation.

Every operation is protected by the application's existing Bearer middleware.
Accepted bytes are never parsed into an in-memory DataFrame during HTTP upload.
Unfinished uploads and validation states are process-local / ephemeral on Free.
"""
from __future__ import annotations

import csv
import hashlib
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field


CHUNK_BYTES = 2 * 1024 * 1024
MAX_UPLOAD = min(max(int(os.getenv("TRADINGQUANT_MAX_UPLOAD_MB", "150")), 1), 4096) * 1024 * 1024
MAX_ROWS = 5_000_000
MAX_JOBS = 2


class UploadInit(BaseModel):
    filename: str = Field(min_length=5, max_length=200)
    size_bytes: int = Field(ge=1, le=MAX_UPLOAD)


def _norm_header(header: str) -> str:
    return header.lstrip("\ufeff").strip().strip("<>").lower().replace(" ", "_")


def _timestamp(value: str):
    return datetime.fromisoformat(value.strip().replace(".", "/").replace("/", "-").replace("T", " "))


def inspect_mt5_stream(path: Path) -> dict[str, Any]:
    """Validate native 9-column MT5 data in constant memory (no dataframes)."""
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
            first = f.readline()
            if not first:
                raise ValueError("El archivo CSV está vacío.")
            delim = "\t" if first.count("\t") > first.count(",") else ";" if first.count(";") > first.count(",") else ","
            f.seek(0)
            reader = csv.reader(f, delimiter=delim)
            columns = [_norm_header(x) for x in next(reader)]
            if len(columns)!=len(set(columns)):
                raise ValueError("Encabezados duplicados en el CSV.")
            required = ("open","high","low","close")
            if any(x not in columns for x in required):
                raise ValueError("Faltan columnas OHLC: "+", ".join(x for x in required if x not in columns))
            has_date_time = "date" in columns and "time" in columns
            time_field = "timestamp" if "timestamp" in columns else "datetime" if "datetime" in columns else None
            if not has_date_time and time_field is None:
                raise ValueError("El CSV necesita <DATE> y <TIME> o timestamp/datetime.")
            idx = {key:columns.index(key) for key in required}
            date_idx = columns.index("date") if has_date_time else None
            time_idx = columns.index("time") if has_date_time else columns.index(time_field)
            valid = 0
            ignored = 0
            start = None
            end = None
            previous = None
            for line,row in enumerate(reader,2):
                if not row or not any(row):
                    continue
                if len(row)!=len(columns):
                    ignored += 1
                    continue
                try:
                    ts = _timestamp((row[date_idx]+" "+row[time_idx]) if has_date_time else row[time_idx])
                    o,h,l,c = (float(row[idx[k]]) for k in required)
                    if not (o>0 and l>0 and h>=max(o,c) and l<=min(o,c) and h>=l):
                        ignored += 1
                        continue
                    if not all(__import__("math").isfinite(v) for v in (o,h,l,c)):
                        ignored += 1
                        continue
                except (ValueError,IndexError,OverflowError):
                    ignored += 1
                    continue
                if previous is not None and ts<previous:
                    raise ValueError(f"El CSV no está ordenado cronológicamente en la línea {line}. Exporta velas ascendentes.")
                if previous is not None and ts==previous:
                    ignored += 1
                    continue
                previous=ts
                if start is None:
                    start=ts
                end=ts
                valid+=1
                if valid>MAX_ROWS:
                    raise ValueError("Más de cinco millones de velas válidas. Divide el histórico.")
            if valid<300:
                raise ValueError(f"Solo hay {valid} velas OHLC válidas; se requieren por lo menos 300.")
            return {"rows":valid,"start":str(start),"end":str(end),"ignored_rows":ignored,
                    "validated_by":"streaming_OHLC_headers_dates"}
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("Archivo CSV no válido o encabezado corrupto: "+str(exc)) from exc


class UploadManager:
    def __init__(self,folder:Path):
        self.folder=Path(folder)
        self.folder.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.jobs:dict[str,dict[str,Any]]={}
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="tq-csv")
    def _job(self,uid:str):
        try:
            uid=str(uuid.UUID(uid))
        except (ValueError,TypeError):
            raise HTTPException(400,"Identificador de subida inválido.") from None
        if uid not in self.jobs:
            raise HTTPException(404,"Carga no encontrada. Si Render reinició la instancia, vuelve a subir el archivo.")
        return self.jobs[uid]
    def begin(self,params:UploadInit):
        if not params.filename.lower().endswith(".csv"):
            raise HTTPException(400,"Solo se aceptan archivos .csv.")
        with self.lock:
            active=sum(1 for j in self.jobs.values() if j["status"] in ("uploading","validating"))
            if active>=MAX_JOBS:
                raise HTTPException(429,"Ya hay dos archivos en proceso. Espera que termine alguno.")
            uid=str(uuid.uuid4())
            filename=Path(params.filename).name[:150]
            part=self.folder/(uid+".part")
            part.touch(exist_ok=False)
            now=datetime.now(timezone.utc).isoformat()
            self.jobs[uid]={"id":uid,"filename":filename,"expected_bytes":params.size_bytes,
                "received_bytes":0,"status":"uploading","error":None,
                "created_at":now,"updated_at":now,"result":None}
            return self.status(uid)
    def import_local(self, filename:str, inbox:Path):
        """Register an inbox CSV without browser upload, safely inside local storage."""
        if not filename or filename!=Path(filename).name or any(x in filename for x in ("/","\\","\\x00")):
            raise HTTPException(400,"Nombre de archivo inválido.")
        if not filename.lower().endswith(".csv"):
            raise HTTPException(400,"Solo se aceptan CSV.")
        path=inbox/filename
        if path.is_symlink() or not path.is_file():
            raise HTTPException(404,"CSV no encontrado en la carpeta local de entrada.")
        size=path.stat().st_size
        if size<1 or size>MAX_UPLOAD:
            raise HTTPException(413,"El CSV está vacío o supera el límite de subida local.")
        with self.lock:
            active=sum(1 for j in self.jobs.values() if j["status"] in ("uploading","validating"))
            if active>=MAX_JOBS:
                raise HTTPException(429,"Ya hay dos archivos en proceso.")
            uid=str(uuid.uuid4())
            dest=self.folder/(uid+".csv")
            try:
                os.link(path,dest)
            except OSError:
                import shutil
                shutil.copyfile(path,dest)
            now=datetime.now(timezone.utc).isoformat()
            self.jobs[uid]={"id":uid,"filename":filename,"expected_bytes":size,
                "received_bytes":size,"status":"validating","error":None,
                "created_at":now,"updated_at":now,"result":None}
            self.pool.submit(self._validate,uid,dest)
            return self.status(uid)
    def status(self,uid:str):
        with self.lock:
            j=self._job(uid)
            return {k:v for k,v in j.items() if k!="result"} | ({"dataset":j["result"]} if j["status"]=="ready" else {})
    def write(self,uid:str,index:int,body:bytes,sha256:str):
        if len(body)>CHUNK_BYTES or not body:
            raise HTTPException(413,"Bloque inválido: el máximo es 2 MiB.")
        if len(sha256)!=64 or not __import__("hmac").compare_digest(hashlib.sha256(body).hexdigest(),sha256.lower()):
            raise HTTPException(422,"Error de integridad del bloque. Se debe reintentar.")
        with self.lock:
            j=self._job(uid)
            if j["status"]!="uploading":
                raise HTTPException(409,"Esta carga ya pasó a validación o finalizó.")
            expected=j["expected_bytes"]
            offset=index*CHUNK_BYTES
            if index<0 or offset+len(body)>expected:
                raise HTTPException(400,"Rango de bloque inválido.")
            path=self.folder/(uid+".part")
            current=path.stat().st_size if path.is_file() else 0
            if offset<current and offset+len(body)==current:
                with path.open("rb") as f:
                    f.seek(offset)
                    if __import__("hmac").compare_digest(hashlib.sha256(f.read(len(body))).hexdigest(),sha256.lower()):
                        return self.status(uid)  # safely retry completed block
            if offset!=current:
                raise HTTPException(409,f"Bloque fuera de orden: se esperan bytes desde {current}.")
            if offset+len(body)<expected and len(body)!=CHUNK_BYTES:
                raise HTTPException(400,"Los bloques intermedios deben tener exactamente 2 MiB.")
            with path.open("ab") as f:
                f.write(body)
                f.flush()
            j["received_bytes"]=offset+len(body)
            j["updated_at"]=datetime.now(timezone.utc).isoformat()
            return self.status(uid)
    def finish(self,uid:str):
        with self.lock:
            j=self._job(uid)
            if j["status"]!="uploading":
                return self.status(uid)
            if j["received_bytes"]!=j["expected_bytes"]:
                raise HTTPException(409,f"Subida incompleta: {j['received_bytes']} de {j['expected_bytes']} bytes.")
            src=self.folder/(uid+".part")
            dest=self.folder/(uid+".csv")
            src.replace(dest)
            j["status"]="validating"
            j["updated_at"]=datetime.now(timezone.utc).isoformat()
            self.pool.submit(self._validate,uid,dest)
            return self.status(uid)
    def _validate(self,uid:str,path:Path):
        try:
            metrics=inspect_mt5_stream(path)
            with self.lock:
                j=self.jobs[uid]
                j["result"]={"id":uid,"filename":j["filename"],"rows":metrics["rows"],
                    "start":metrics["start"],"end":metrics["end"],"timeframe":"source",
                    "uploaded_at":datetime.now(timezone.utc).isoformat(),
                    "ignored_rows":metrics["ignored_rows"]}
                j["status"]="ready"
                j["updated_at"]=datetime.now(timezone.utc).isoformat()
        except (ValueError,OSError) as exc:
            path.unlink(missing_ok=True)
            with self.lock:
                if uid in self.jobs:
                    self.jobs[uid].update(status="failed",error=str(exc)[:350],
                        updated_at=datetime.now(timezone.utc).isoformat())

