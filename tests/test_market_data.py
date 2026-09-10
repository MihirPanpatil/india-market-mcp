import asyncio
import json
from pathlib import Path

import pytest

from src.utils import nse
from src.utils.yahoo import get_yahoo_chart_quote


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append(url)
        return self.responses[url]


@pytest.mark.asyncio
async def test_nse_get_parses_json_response(monkeypatch):
    client = FakeClient({
        "https://www.nseindia.com/api/marketStatus": FakeResponse({"marketState": []})
    })
    monkeypatch.setattr(nse, "get_nse_client", lambda: asyncio.sleep(0, result=client))
    result = await nse.nse_get("/api/marketStatus")
    assert result == {"marketState": []}


@pytest.mark.asyncio
async def test_security_master_csv_is_parsed(monkeypatch):
    csv_text = "SYMBOL,NAME OF COMPANY, SERIES\nRELIANCE,Reliance Industries Limited, EQ\n"
    client = FakeClient({
        "https://archives.nseindia.com/content/equities/EQUITY_L.csv": FakeResponse({}, text=csv_text)
    })
    monkeypatch.setattr(nse, "get_nse_client", lambda: asyncio.sleep(0, result=client))
    result = await nse.get_security_master()
    assert result == [{"SYMBOL": "RELIANCE", "NAME OF COMPANY": "Reliance Industries Limited", " SERIES": " EQ"}]


@pytest.mark.asyncio
async def test_index_constituent_csv_is_parsed(monkeypatch):
    csv_text = "Company Name,Industry,Symbol,Series,ISIN Code\nReliance Industries Ltd.,Oil Gas & Consumable Fuels,RELIANCE,EQ,INE002A01018\n"
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"
    client = FakeClient({url: FakeResponse({}, text=csv_text)})
    monkeypatch.setattr(nse, "get_nse_client", lambda: asyncio.sleep(0, result=client))
    result = await nse.get_index_constituents_csv("NIFTY 50")
    assert result[0]["Symbol"] == "RELIANCE"


@pytest.mark.asyncio
async def test_unknown_index_does_not_make_network_request(monkeypatch):
    client = FakeClient({})
    monkeypatch.setattr(nse, "get_nse_client", lambda: asyncio.sleep(0, result=client))
    assert await nse.get_index_constituents_csv("UNKNOWN") == []
    assert client.calls == []


@pytest.mark.asyncio
async def test_yahoo_chart_quote_maps_exchange_and_price(monkeypatch):
    class FakeYahooClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            return FakeYahooResponse()

    class FakeYahooResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"chart": {"result": [{
                "meta": {
                    "symbol": "RELIANCE.NS", "shortName": "Reliance Industries",
                    "currency": "INR", "fullExchangeName": "NSE",
                    "regularMarketPrice": 1274.0, "regularMarketChangePercent": -0.39,
                    "fiftyTwoWeekHigh": 1611.8, "fiftyTwoWeekLow": 1249.8,
                },
                "indicators": {"quote": [{"volume": [9290437], "close": [1274.0]}]},
            }]}}

    import src.utils.yahoo as yahoo
    monkeypatch.setattr(yahoo.httpx, "AsyncClient", lambda **kwargs: FakeYahooClient())
    result = await yahoo.get_yahoo_chart_quote("RELIANCE")
    assert result["exchange"] == "NSE"
    assert result["currentPrice"] == 1274.0
    assert result["volume"] == 9290437


def test_mcp_server_declares_stdio_entrypoint():
    source = Path("src/server.py").read_text()
    assert 'mcp.run(transport="stdio")' in source
