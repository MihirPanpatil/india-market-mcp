import asyncio
from datetime import datetime
import numpy as np
import pandas as pd
import pytest

from src.utils import cache, nse
from src.modules.technicals import _clean_number


def test_market_session_uses_ist_and_weekends():
    assert nse.classify_market_session(datetime(2026, 9, 12, 12, 0)) == "closed"  # Saturday
    assert nse.classify_market_session(datetime(2026, 9, 10, 12, 0)) == "open"
    assert nse.classify_market_session(datetime(2026, 9, 10, 8, 0)) == "pre_market"
    assert nse.classify_market_session(datetime(2026, 9, 10, 16, 0)) == "closed"


def test_nan_normalization():
    assert _clean_number(np.nan) is None
    assert _clean_number(float("inf")) is None
    assert _clean_number(12.345) == 12.35

@pytest.mark.asyncio
async def test_cache_does_not_store_error_payloads(monkeypatch):
    cache._cache.clear()
    calls = 0
    @cache.cached(ttl=100)
    async def flaky():
        nonlocal calls
        calls += 1
        return {"error": "temporary"}
    await flaky(); await flaky()
    assert calls == 2

@pytest.mark.asyncio
async def test_nse_auth_failure_refreshes_and_returns_diagnostics(monkeypatch):
    class Response:
        status_code = 401
        def json(self): return {}
    class Client:
        async def get(self, *args, **kwargs): return Response()
    client = Client()
    refreshed = []
    async def get_client(): return client
    async def refresh(c): refreshed.append(1)
    async def no_sleep(*args): return None
    monkeypatch.setattr(nse, "get_nse_client", get_client)
    monkeypatch.setattr(nse, "_init_nse_session", refresh)
    monkeypatch.setattr(nse.asyncio, "sleep", no_sleep)
    result = await nse.nse_get("/api/test")
    assert result["error"] == "nse_request_failed"
    assert result["diagnostics"]["status_code"] == 401
    assert refreshed

@pytest.mark.asyncio
async def test_security_master_uses_stale_fallback(monkeypatch):
    nse._security_master_cache = [{"SYMBOL": "OLD"}]
    class Client:
        async def get(self, *args, **kwargs): raise RuntimeError("offline")
    monkeypatch.setattr(nse, "get_nse_client", lambda: asyncio.sleep(0, result=Client()))
    result = await nse.get_security_master()
    assert result == [{"SYMBOL": "OLD"}]
    assert nse.get_security_master_diagnostics()["stale"] is True
