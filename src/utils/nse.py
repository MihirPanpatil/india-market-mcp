import httpx
import time
import asyncio

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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        await _init_nse_session(_nse_client)
    return _nse_client


async def _init_nse_session(client: httpx.AsyncClient):
    """Establish NSE session by visiting homepage first (gets cookies)."""
    try:
        await client.get("https://www.nseindia.com", timeout=10.0)
        await asyncio.sleep(0.3)
        await client.get("https://www.nseindia.com/api/marketStatus", timeout=10.0)
    except Exception:
        pass


async def nse_get(path: str) -> dict | list | None:
    global _last_nse_call

    # Rate limit
    elapsed = time.time() - _last_nse_call
    if elapsed < NSE_MIN_INTERVAL:
        await asyncio.sleep(NSE_MIN_INTERVAL - elapsed)
    _last_nse_call = time.time()

    client = await get_nse_client()
    url = f"https://www.nseindia.com{path}"

    for attempt in range(3):
        try:
            resp = await client.get(url, timeout=12.0)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (401, 403, 429):
                # Re-init session and back off
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
