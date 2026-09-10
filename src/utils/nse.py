import asyncio
import csv
import io
import time
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

import httpx

_nse_client: httpx.AsyncClient | None = None
_last_nse_call: float = 0
NSE_MIN_INTERVAL = 0.5
_security_master_cache: list[dict] = []
_security_master_diagnostics: dict = {"stale": False}
IST = ZoneInfo("Asia/Kolkata")


def classify_market_session(at: datetime | None = None, holidays: set | None = None) -> str:
    """Classify NSE hours in IST; holidays may contain date objects or ISO dates."""
    value = (at or datetime.now(IST)).replace(tzinfo=IST) if (at or datetime.now(IST)).tzinfo is None else (at or datetime.now(IST)).astimezone(IST)
    if value.weekday() >= 5 or value.date() in (holidays or set()) or value.date().isoformat() in (holidays or set()):
        return "closed"
    if value.time() < dt_time(9, 15):
        return "pre_market"
    if value.time() <= dt_time(15, 30):
        return "open"
    return "closed"


async def get_nse_client() -> httpx.AsyncClient:
    global _nse_client
    if _nse_client is None or _nse_client.is_closed:
        _nse_client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=10.0), follow_redirects=True, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate", "Connection": "keep-alive"})
        await _init_nse_session(_nse_client)
    return _nse_client


async def _init_nse_session(client: httpx.AsyncClient):
    try:
        await client.get("https://www.nseindia.com", timeout=10.0)
        await asyncio.sleep(0.3)
        await client.get("https://www.nseindia.com/api/marketStatus", timeout=10.0)
    except Exception:
        pass


async def nse_get(path: str) -> dict | list | None:
    global _last_nse_call
    elapsed = time.time() - _last_nse_call
    if elapsed < NSE_MIN_INTERVAL:
        await asyncio.sleep(NSE_MIN_INTERVAL - elapsed)
    client = await get_nse_client()
    last_status = None
    for attempt in range(3):
        _last_nse_call = time.time()
        try:
            resp = await client.get(f"https://www.nseindia.com{path}", timeout=12.0)
            if resp.status_code == 200:
                return resp.json()
            last_status = resp.status_code
            if resp.status_code in (401, 403, 429):
                await _init_nse_session(client)
                if attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
            return {"error": "nse_request_failed", "diagnostics": {"path": path, "status_code": resp.status_code, "attempts": attempt + 1, "session_refreshed": resp.status_code in (401, 403, 429)}}
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as exc:
            if attempt < 2:
                await asyncio.sleep(1.0 * (attempt + 1)); continue
            return {"error": "nse_request_failed", "diagnostics": {"path": path, "exception": type(exc).__name__, "status_code": last_status, "attempts": attempt + 1}}
        except Exception as exc:
            if attempt < 2:
                await asyncio.sleep(1.0); continue
            return {"error": "nse_request_failed", "diagnostics": {"path": path, "exception": type(exc).__name__, "status_code": last_status, "attempts": attempt + 1}}
    return None


async def get_security_master() -> list[dict]:
    global _security_master_cache, _security_master_diagnostics
    client = await get_nse_client()
    try:
        response = await client.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", timeout=20.0)
        response.raise_for_status()
        data = list(csv.DictReader(io.StringIO(response.text)))
        _security_master_cache = data
        _security_master_diagnostics = {"stale": False, "count": len(data)}
        return data
    except Exception as exc:
        _security_master_diagnostics = {"stale": bool(_security_master_cache), "error": type(exc).__name__, "count": len(_security_master_cache)}
        return _security_master_cache


def get_security_master_diagnostics() -> dict:
    return dict(_security_master_diagnostics)


async def get_index_constituents_csv(index: str) -> list[dict]:
    names = {"NIFTY 50": "ind_nifty50list.csv", "NIFTY NEXT 50": "ind_niftynext50list.csv", "NIFTY 100": "ind_nifty100list.csv", "NIFTY 200": "ind_nifty200list.csv"}
    filename = names.get(index.upper())
    if not filename:
        return []
    client = await get_nse_client()
    try:
        response = await client.get(f"https://www.niftyindices.com/IndexConstituent/{filename}", timeout=20.0)
        response.raise_for_status()
        return list(csv.DictReader(io.StringIO(response.text)))
    except Exception:
        return []
