"""Bounded background research jobs for a persistent FastAPI worker process.

This manager intentionally does NOT claim cross-process durability, distributed
scheduling, cancellation, or Cloud Function compatibility. Restart loses status.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from threading import Lock
from time import monotonic
from uuid import uuid4

class ResearchJobs:
    def __init__(self,max_queued:int=2):
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix="tq-research")
        self.lock=Lock()
        self.jobs={}
        self.max_queued=max_queued

    def launch(self,dataset_path,config,load_func,engine_func):
        with self.lock:
            active=sum(1 for j in self.jobs.values() if j["status"] in ("queued","running"))
            if active>=self.max_queued:
                raise ValueError("Hay exploraciones activas. Espera a que termine alguna antes de iniciar otra.")
            job_id=str(uuid4())
            now=datetime.now(timezone.utc).isoformat()
            self.jobs[job_id]={"id":job_id,"status":"queued","phase":"en cola",
                               "created_at":now,"updated_at":now,
                               "checked":0,"total":config.get("candidates",0),
                               "percent":0,"result":None,"error":None,
                               "started":None,"last_progress":None,
                               "seconds_since_progress":0,"elapsed_seconds":0}
        def worker():
            with self.lock:
                self.jobs[job_id].update(status="running",phase="cargando histórico",
                                         started=monotonic(),last_progress=monotonic())
            def progress(checked,total,phase):
                with self.lock:
                    job=self.jobs[job_id]
                    if phase.startswith("explorando"):
                        fraction=.08+.74*checked/max(1,total)
                    elif phase.startswith("validando"):
                        fraction=.83+.16*checked/max(1,total)
                    elif phase.startswith("reconstruyendo"):
                        fraction=.82
                    else:
                        fraction=.02+.05*checked/max(1,total)
                    now=monotonic()
                    job.update(checked=int(checked),total=int(total),phase=phase,
                               percent=min(99,max(job["percent"],int(fraction*100))),
                               last_progress=now,seconds_since_progress=0,
                               elapsed_seconds=int(now-job["started"]))
            try:
                frame=load_func(dataset_path)
                progress(0,config.get("candidates",0),"filtrando histórico")
                result=engine_func(frame,config,on_progress=progress)
                output={"id":job_id,"created_at":now,
                        "dataset_id":config["dataset_id"],"config":config,**result}
                with self.lock:
                    output["elapsed_seconds"]=int(monotonic()-self.jobs[job_id]["started"])
                    job=self.jobs[job_id]
                    job.update(status="completed",phase="completado",result=output,
                               checked=int(result["tested"]),total=int(result["tested"]),
                               percent=100,elapsed_seconds=int(monotonic()-job["started"]),
                               updated_at=datetime.now(timezone.utc).isoformat())
            except Exception as exc:
                with self.lock:
                    job=self.jobs[job_id]
                    job.update(status="failed",phase="error",error=str(exc)[:500],
                               elapsed_seconds=int(monotonic()-job["started"]),
                               updated_at=datetime.now(timezone.utc).isoformat())
        self.executor.submit(worker)
        return self.status(job_id)

    def status(self,job_id):
        with self.lock:
            if job_id not in self.jobs:
                return None
            j=self.jobs[job_id]
            view={k:v for k,v in j.items() if k not in ("result","started","last_progress")}
            if j["status"]=="running" and j["started"] is not None:
                now=monotonic()
                view["elapsed_seconds"]=int(now-j["started"])
                view["seconds_since_progress"]=int(now-(j["last_progress"] or j["started"]))
            return view

    def result(self,job_id):
        with self.lock:
            if job_id not in self.jobs:
                return None
            return self.jobs[job_id].get("result")

JOBS=ResearchJobs()
