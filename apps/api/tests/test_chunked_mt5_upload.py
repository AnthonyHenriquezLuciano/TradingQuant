"""Secure MT5 chunk upload: end-to-end browser API equivalent regressions."""
from __future__ import annotations
import hashlib
import time
from pathlib import Path

from fastapi.testclient import TestClient
import main
from dataset_uploads import UploadManager,CHUNK_BYTES,inspect_mt5_stream
from test_mt5_upload import mt5_content

TOKEN="test-only-chunk-token"
ORIGIN="https://tradingquant-beta.vercel.app"
AUTH={"Origin":ORIGIN,"Authorization":f"Bearer {TOKEN}"}

def _headers(blob:bytes):
    return {"X-Chunk-SHA256":hashlib.sha256(blob).hexdigest(),
            "Content-Type":"application/octet-stream",**AUTH}

def test_chunked_mt5_upload_and_sha256_retry_and_streaming_validation(tmp_path:Path,monkeypatch):
    manager=UploadManager(tmp_path)
    monkeypatch.setattr(main,"UPLOADS",manager)
    monkeypatch.setenv("TRADINGQUANT_REQUIRE_AUTH","1")
    monkeypatch.setenv("TRADINGQUANT_ACCESS_TOKEN",TOKEN)
    c=TestClient(main.app)
    options=c.options("/api/datasets/uploads/anything/chunks/0",headers={
        "Origin":ORIGIN,"Access-Control-Request-Method":"PUT",
        "Access-Control-Request-Headers":"authorization,x-chunk-sha256,content-type"})
    assert options.status_code==200,options.text
    assert options.headers["access-control-allow-origin"]==ORIGIN
    content=mt5_content(38000)
    assert len(content)>CHUNK_BYTES
    started=c.post("/api/datasets/uploads",json={"filename":"USDJPY_M1.csv","size_bytes":len(content)},headers=AUTH)
    assert started.status_code==201,started.text
    uid=started.json()["id"]
    assert started.json()["chunk_bytes"]==CHUNK_BYTES
    first=content[:CHUNK_BYTES]
    second=content[CHUNK_BYTES:]
    denied=c.put(f"/api/datasets/uploads/{uid}/chunks/0",content=first,
                 headers={"X-Chunk-SHA256":hashlib.sha256(first).hexdigest(),"Origin":ORIGIN})
    assert denied.status_code==401
    invalid=c.put(f"/api/datasets/uploads/{uid}/chunks/0",content=first,
                  headers={"X-Chunk-SHA256":"0"*64,**AUTH})
    assert invalid.status_code==422
    ok=c.put(f"/api/datasets/uploads/{uid}/chunks/0",content=first,headers=_headers(first))
    assert ok.status_code==200,ok.text
    assert ok.json()["received_bytes"]==len(first)
    # A repeated first chunk, e.g. after interrupted fetch, is safely idempotent.
    retry=c.put(f"/api/datasets/uploads/{uid}/chunks/0",content=first,headers=_headers(first))
    assert retry.status_code==200
    assert retry.json()["received_bytes"]==len(first)
    ok2=c.put(f"/api/datasets/uploads/{uid}/chunks/1",content=second,headers=_headers(second))
    assert ok2.status_code==200,ok2.text
    assert ok2.json()["received_bytes"]==len(content)
    done=c.post(f"/api/datasets/uploads/{uid}/complete",headers=AUTH)
    assert done.status_code==202
    for _ in range(300):
        status=c.get(f"/api/datasets/uploads/{uid}",headers=AUTH)
        assert status.status_code==200,status.text
        if status.json()["status"] in ("ready","failed"):
            break
        time.sleep(.015)
    assert status.json()["status"]=="ready",status.text
    dataset=status.json()["dataset"]
    assert dataset["rows"]==38000
    assert dataset["start"].startswith("2020-01-01")
    assert dataset["filename"]=="USDJPY_M1.csv"
    assert (tmp_path/(uid+".csv")).read_bytes()==content

def test_invalid_mt5_file_never_becomes_registered_dataset(tmp_path:Path,monkeypatch):
    manager=UploadManager(tmp_path)
    monkeypatch.setattr(main,"UPLOADS",manager)
    monkeypatch.setenv("TRADINGQUANT_REQUIRE_AUTH","1")
    monkeypatch.setenv("TRADINGQUANT_ACCESS_TOKEN",TOKEN)
    client=TestClient(main.app)
    content=b"<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\n2020.01.01\t00:00:00\t100\t102\t98\t101\n"
    initial=client.post("/api/datasets/uploads",json={"filename":"broken.csv","size_bytes":len(content)},headers=AUTH)
    uid=initial.json()["id"]
    chunk=client.put(f"/api/datasets/uploads/{uid}/chunks/0",content=content,headers=_headers(content))
    assert chunk.status_code==200
    client.post(f"/api/datasets/uploads/{uid}/complete",headers=AUTH)
    for _ in range(200):
        status=client.get(f"/api/datasets/uploads/{uid}",headers=AUTH).json()
        if status["status"] in ("ready","failed"):break
        time.sleep(.01)
    assert status["status"]=="failed"
    assert "300" in status["error"]
    assert not (tmp_path/(uid+".csv")).exists()

def test_stream_import_preserves_mt5_tick_volume_spread_files_unmodified(tmp_path:Path):
    content=mt5_content(400)
    f=tmp_path/"mt5.csv"
    f.write_bytes(content)
    report=inspect_mt5_stream(f)
    assert report["rows"]==400
    assert report["ignored_rows"]==0
    assert "<SPREAD>" in f.read_text()
    assert f.read_bytes()==content
