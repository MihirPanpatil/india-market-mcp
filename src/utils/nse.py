import httpx
import time
import asyncio
import csv
import io

_nse_client: httpx.AsyncClient | None = None
_last_nse_call: float = 0
NSE_MIN_INTERVAL = 0.5

async def get_nse_client() -> httpx.AsyncClient:
    global _nse_client
    if _nse_client is None or _nse_client.is_closed:
        _nse_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=10.0),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )
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
    _last_nse_call = time.time()
    client = await get_nse_client()
    for attempt in range(3):
        try:
            resp = await client.get(f"https://www.nseindia.com{path}", timeout=12.0)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (401, 403, 429):
                await _init_nse_session(client)
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            return None
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError):
            if attempt < 2:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < 2:
                await asyncio.sleep(1.0)
                continue
            return None
    return None

async def get_security_master() -> list[dict]:
    """Fetch NSE's public security master CSV for symbol search."""
    client = await get_nse_client()
    try:
        response = await client.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", timeout=20.0)
        response.raise_for_status()
        return list(csv.DictReader(io.StringIO(response.text)))
    except Exception:
        return []

async def get_index_constituents_csv(index: str) -> list[dict]:
    """Fetch current constituents from NSE Indices' public CSV files."""
    names = {"NIFTY 50": "ind_nifty50list.csv", "NIFTY NEXT 50": "ind_niftynext50list.csv", "NIFTY 100": "ind_nifty100list.csv", "NIFTY 200": "ind_nifty200list.csv"}
    filename = names.get(index.strip().upper())
    if not filename:
        return []
    client = await get_nse_client()
    try:
        response = await client.get(f"https://www.niftyindices.com/IndexConstituent/{filename}", timeout=20.0)
        response.raise_for_status()
        return list(csv.DictReader(io.StringIO(response.text)))
    except Exception:
        return []
