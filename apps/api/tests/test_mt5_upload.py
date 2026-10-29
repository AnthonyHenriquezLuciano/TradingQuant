"""MT5 9-column tab CSV upload and secure CORS regressions."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timedelta
import pytest
from fastapi.testclient import TestClient
import main

CSV_HEADER="<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"

def mt5_content(n=400):
    rows=[CSV_HEADER]
    for i in range(n):
        dt=datetime(2020,1,1)+timedelta(minutes=i)
        # All OHLC equal is valid for very low-volume FX minutes.
        p=108.658+i*.0001
        rows.append(f"{dt:%Y.%m.%d}\t{dt:%H:%M:%S}\t{p:.3f}\t{p:.3f}\t{p:.3f}\t{p:.3f}\t1\t0\t14\n")
    return "".join(rows).encode("utf-8")

def test_mt5_nine_tab_columns_import(tmp_path:Path):
    from engine import load_data
    file=tmp_path/"mt5.csv"
    file.write_bytes(mt5_content())
    df=load_data(file)
    assert df.shape==(400,5)
    assert df.columns==["timestamp","open","high","low","close"]
    assert df[0,"open"]==pytest.approx(108.658)
    assert str(df[0,"timestamp"]).startswith("2020-01-01 00:00:00")

def test_mt5_upload_uses_bearer_token_and_returns_cors_headers(tmp_path:Path,monkeypatch):
    monkeypatch.setenv("TRADINGQUANT_REQUIRE_AUTH","1")
    monkeypatch.setenv("TRADINGQUANT_ACCESS_TOKEN","test-only-private-token")
    monkeypatch.setattr(main,"DATA_DIR",tmp_path)
    client=TestClient(main.app)
    origin="https://tradingquant-beta.vercel.app"
    preflight=client.options("/api/datasets/upload",headers={
        "Origin":origin,
        "Access-Control-Request-Method":"POST",
        "Access-Control-Request-Headers":"authorization",
    })
    assert preflight.status_code==200, preflight.text
    assert preflight.headers.get("access-control-allow-origin")==origin
    files={"file":("USDJPY_M1_MT5.csv",mt5_content(),"text/csv")}
    denied=client.post("/api/datasets/upload",files=files,headers={"Origin":origin})
    assert denied.status_code==401
    assert denied.headers.get("access-control-allow-origin")==origin
    allowed=client.post("/api/datasets/upload",files=files,headers={
        "Origin":origin,
        "Authorization":"Bearer test-only-private-token",
    })
    assert allowed.status_code==200,allowed.text
    body=allowed.json()
    assert body["rows"]==400
    assert body["filename"]=="USDJPY_M1_MT5.csv"
    assert body["start"].startswith("2020-01-01")
    assert (tmp_path/(body["id"]+".csv")).is_file()
