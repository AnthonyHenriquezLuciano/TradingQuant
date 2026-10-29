"""Local-only CSV inbox must be usable without Render and reject unsafe names."""
import time

from fastapi.testclient import TestClient

import main
from dataset_uploads import UploadManager
from test_mt5_upload import mt5_content


def test_local_inbox_and_direct_import(tmp_path, monkeypatch):
    data=tmp_path/"uploads"
    inbox=tmp_path/"inbox"
    data.mkdir()
    inbox.mkdir()
    monkeypatch.setenv("TRADINGQUANT_REQUIRE_AUTH","0")
    monkeypatch.setenv("TRADINGQUANT_LOCAL_MODE","1")
    monkeypatch.setattr(main,"DATA_DIR",data)
    manager=UploadManager(data)
    monkeypatch.setattr(main,"UPLOADS",manager)
    csv=inbox/"USDJPY_M1.csv"
    csv.write_bytes(mt5_content(400))
    c=TestClient(main.app)
    listed=c.get("/api/local/inbox")
    assert listed.status_code==200
    assert [x["filename"] for x in listed.json()["files"]]==["USDJPY_M1.csv"]
    unsafe=c.post("/api/local/import",json={"filename":"../private.csv"})
    assert unsafe.status_code==400
    started=c.post("/api/local/import",json={"filename":"USDJPY_M1.csv"})
    assert started.status_code==202,started.text
    uid=started.json()["id"]
    for _ in range(250):
        status=c.get("/api/datasets/uploads/"+uid)
        assert status.status_code==200
        if status.json()["status"] in ("ready","failed"):
            break
        time.sleep(.01)
    assert status.json()["status"]=="ready",status.text
    assert status.json()["dataset"]["rows"]==400
    assert (data/(uid+".csv")).read_bytes()==csv.read_bytes()


def test_local_import_is_disabled_for_cloud(monkeypatch):
    monkeypatch.delenv("TRADINGQUANT_LOCAL_MODE",raising=False)
    monkeypatch.setenv("TRADINGQUANT_REQUIRE_AUTH","0")
    c=TestClient(main.app)
    assert c.get("/api/local/inbox").status_code==404
    assert c.post("/api/local/import",json={"filename":"MT5.csv"}).status_code==404
