"""Fixed-UTC session scheduling for bar-open entries and forced position exits.

No seasonal hour shift is applied: the UI shows and controls exactly these
fixed UTC windows. Source CSV clock timezone is explicitly configured.
"""
from __future__ import annotations
import numpy as np
import polars as pl

SESSION_WINDOWS={
    "sydney":(21*60,6*60),
    "tokyo":(0,9*60),
    "london":(7*60,16*60),
    "new_york":(12*60,21*60),
    "tokyo_london":(7*60,9*60),
    "london_new_york":(12*60,16*60),
    "asian":(21*60,9*60),
}
DEFAULT_SCHEDULE={
    "sessions":["all_day"],
    "close_before_ny":False,
    "close_before_weekend":False,
    "no_friday_entries":False,
    "avoid_monday_open":False,
    "avoid_rollover":False,
}


def validate_schedule(cfg:dict|None)->dict:
    if cfg is not None and not isinstance(cfg,dict):
        raise ValueError("El horario debe ser un objeto.")
    cfg={**DEFAULT_SCHEDULE,**(cfg or {})}
    sessions=cfg.get("sessions",[])
    if not isinstance(sessions,list) or not sessions or not all(
        isinstance(s,str) and (s=="all_day" or s in SESSION_WINDOWS)
        for s in sessions
    ):
        raise ValueError("Selecciona al menos una sesión válida.")
    if "all_day" in sessions and len(sessions)>1:
        raise ValueError("24 horas no se puede combinar con otras ventanas.")
    for key in DEFAULT_SCHEDULE:
        if key!="sessions" and not isinstance(cfg[key],bool):
            raise ValueError("Restricción de horario inválida: "+key)
    return cfg


def time_arrays(frame:pl.DataFrame,source_timezone:str,schedule:dict|None):
    cfg=validate_schedule(schedule)
    try:
        ts=frame.select(
            pl.col("timestamp").dt.replace_time_zone(
                source_timezone,ambiguous="earliest"
            ).dt.convert_time_zone("UTC").alias("utc")
        )["utc"]
        utc=pl.DataFrame({"ts":ts})
        # Polars hour/minute can be uint8. Cast BEFORE multiplying to avoid 256 overflow.
        minute=(utc["ts"].dt.hour().to_numpy().astype(np.int32)*60+
                utc["ts"].dt.minute().to_numpy().astype(np.int32))
        weekday=utc["ts"].dt.weekday().to_numpy().astype(np.int32)-1
        # ISO week and calendar month identifiers for realized risk limits
        weeks=utc["ts"].dt.strftime("%G%V").cast(pl.Int32).to_numpy()
        months=utc["ts"].dt.strftime("%Y%m").cast(pl.Int32).to_numpy()
        days=utc["ts"].dt.date().cast(pl.Int32).to_numpy()
    except Exception as exc:
        raise ValueError("No se pudo interpretar el horario del CSV. Revisa su zona horaria.") from exc

    allowed=np.zeros(len(frame),dtype=np.bool_)
    forced=np.zeros(len(frame),dtype=np.bool_)
    sessions=cfg["sessions"]
    for i in range(len(frame)):
        wd=int(weekday[i])
        m=int(minute[i])
        if wd>=5:
            continue
        if "all_day" in sessions:
            inside=True
        else:
            inside=False
            for s in sessions:
                start,end=SESSION_WINDOWS[s]
                if (start<=m<end if start<end else m>=start or m<end):
                    inside=True
                    break
        if cfg["no_friday_entries"] and wd==4:
            inside=False
        if cfg["avoid_monday_open"] and wd==0 and m<60:
            inside=False
        # Rollover spans 20:55-21:10 UTC, not 00:00.
        if cfg["avoid_rollover"] and (20*60+55<=m<21*60+10):
            inside=False
        if cfg["close_before_ny"] and m>=20*60:
            inside=False
            forced[i]=True
        if cfg["close_before_weekend"] and wd==4 and m>=19*60:
            inside=False
            forced[i]=True
        allowed[i]=inside
    return allowed,forced,days,weeks,months
