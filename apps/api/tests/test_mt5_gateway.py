"""MT5 read-only attach, broker symbol metadata, real OHLC rates and account lock."""
import sys
import types
from datetime import datetime,timezone,timedelta

import numpy as np
from fastapi.testclient import TestClient

import main
import mt5_gateway
from mt5_gateway import MT5Bridge,ConnectRequest,HistoryRequest

class Named:
    def __init__(self,**kwargs):self.__dict__.update(kwargs)
    def _asdict(self):return dict(self.__dict__)
class FakeMT5:
    TIMEFRAME_M1=1
    TIMEFRAME_M5=5
    def __init__(self):
        self.shutdown_count=0
        self.trades_sent=0
    def initialize(self,**kwargs):return True
    def shutdown(self):self.shutdown_count+=1
    def last_error(self):return (0,"ok")
    def account_info(self):
        return Named(login=12345,server="Broker-Demo",company="TestBroker",
            currency="USD",leverage=100,balance=5025.0,equity=5001.0)
    def terminal_info(self):return Named(path="C:\\MT5\\Data")
    def symbols_get(self):return [self.symbol_info("USDJPY"),self.symbol_info("XAUUSD.a")]
    def symbol_info(self,sym):
        if sym not in ("USDJPY","XAUUSD.a"):return None
        return Named(name=sym,description="Test instrument",visible=True,select=True,
            digits=3,point=.001,spread=15,spread_float=True,trade_tick_size=.001,
            trade_tick_value=.90,trade_tick_value_profit=.90,trade_tick_value_loss=.91,
            trade_contract_size=100000,volume_min=.01,volume_step=.01,volume_max=100.0,
            currency_profit="JPY",swap_long=-2.0,swap_short=1.0,swap_mode=1,
            trade_mode=4,trade_stops_level=10,trade_freeze_level=0,trade_calc_mode=0,
            path="Forex/JPY",currency_base="USD",currency_margin="USD")
    def symbol_select(self,sym,enabled):return True
    def copy_rates_range(self,sym,tf,start,end):
        dt=np.dtype([("time","i8"),("open","f8"),("high","f8"),("low","f8"),
                 ("close","f8"),("tick_volume","i8"),("spread","i4"),("real_volume","f8")])
        base=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp())
        out=np.zeros(400,dtype=dt)
        out["time"]=base+np.arange(400)*60
        out["open"]=140.+np.arange(400)*.001
        out["high"]=out["open"]+.002
        out["low"]=out["open"]-.002
        out["close"]=out["open"]+.001
        out["tick_volume"]=3
        out["spread"]=15
        return out


def test_readonly_mt5_accounts_symbols_history_and_no_password(tmp_path,monkeypatch):
    fake=FakeMT5()
    monkeypatch.setenv("TRADINGQUANT_LOCAL_MODE","1")
    monkeypatch.setattr(mt5_gateway.platform,"system",lambda:"Windows")
    monkeypatch.setitem(sys.modules,"MetaTrader5",fake)
    gateway=MT5Bridge(tmp_path/"data")
    account=gateway.connect(ConnectRequest(label="FundingPips Fase 1",
        account_type="propfirm",phase="phase1",prop_firm="FundingPips"))
    id=account["account"]["id"]
    assert id=="12345@Broker-Demo"
    assert account["account"]["status"]=="connected"
    assert gateway.list()["active_id"]==id
    assert "password" not in (tmp_path/"data"/"mt5_accounts.json").read_text().lower()
    symbols=gateway.symbols(id)
    assert [s["name"] for s in symbols["symbols"]]==["USDJPY","XAUUSD.a"]
    assert gateway.all_symbols()["symbols"][1]["accounts"]==[id]
    spec=gateway.specification(id,"USDJPY")
    assert spec["symbol"]["spread"]==15
    assert spec["symbol"]["commission_roundtrip_account_currency"] is None
    imported=gateway.import_history(HistoryRequest(account_id=id,symbol="USDJPY",
        timeframe="1m",start=datetime(2026,1,1,tzinfo=timezone.utc),
        end=datetime(2026,1,2,tzinfo=timezone.utc)),tmp_path/"uploads")
    assert imported["rows"]==400
    assert imported["source"]=="MT5_TERMINAL"
    csv=(tmp_path/"uploads"/(imported["id"]+".csv")).read_text()
    assert "<DATE>\t<TIME>" in csv
    assert "2026.01.01" in csv
    assert fake.trades_sent==0


def test_account_gate_blocks_research_until_connected(tmp_path,monkeypatch):
    monkeypatch.setenv("TRADINGQUANT_REQUIRE_AUTH","0")
    monkeypatch.setenv("TRADINGQUANT_REQUIRE_ACCOUNT","1")
    monkeypatch.setattr(main,"MT5",MT5Bridge(tmp_path/"data"))
    c=TestClient(main.app)
    assert c.get("/health").status_code==200
    assert c.get("/api/accounts/status").status_code==200
    locked=c.get("/api/local/inbox")
    assert locked.status_code==403
    assert "MT5" in locked.json()["detail"]
    main.MT5.active_id="123@Broker"
    assert c.get("/api/local/inbox",headers={"X-TradingQuant-Account":"other"}).status_code==403
    monkeypatch.setenv("TRADINGQUANT_LOCAL_MODE","1")
    assert c.get("/api/local/inbox",headers={"X-TradingQuant-Account":"123@Broker"}).status_code==200
