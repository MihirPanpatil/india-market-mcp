# Hermes Agent Guide

This file records the repository-specific conventions and integration details used by Hermes Agent.

## Repository

- Remote: `https://github.com/icharshal/india-market-mcp.git`
- Local working copy used by Hermes: `/tmp/india-market-mcp`
- Transport: local MCP stdio
- Entry point: `src.server:main`
- Hermes command configuration:

```yaml
mcp_servers:
  india_market:
    command: /tmp/india-market-mcp/.venv/bin/python
    args: ["-m", "src.server"]
    cwd: /tmp/india-market-mcp
    enabled: true
    timeout: 120
```

Do not replace this with a network endpoint unless the transport and authentication are deliberately designed and tested.

## Environment

- Use the repository virtual environment: `.venv/bin/python`.
- The code currently uses the MCP v1 API (`mcp.server.fastmcp.FastMCP`), so keep `mcp<2` installed.
- Install or update dependencies with `uv`, not system `pip`:

```bash
uv pip install --python .venv/bin/python -e .
```

## Data-source map

- NSE JSON endpoints: `src/utils/nse.py`.
- NSE security search: public security master CSV at `https://archives.nseindia.com/content/equities/EQUITY_L.csv`.
- Index constituents: public CSV files from `https://www.niftyindices.com/IndexConstituent/`.
- Yahoo quotes: direct Chart API in `src/utils/yahoo.py`; it avoids crumb-dependent `ticker.info` for quote fields.
- Yahoo history: `yfinance.history()`.
- Mutual funds, derivatives, and other modules may use their own upstream providers; verify those paths independently.

## Reliability behavior and tests

- NSE request failures return structured `error: nse_request_failed` diagnostics; 401/403/429 responses refresh the session before retrying.
- `classify_market_session()` uses Asia/Kolkata, weekends, optional holiday dates, and NSE hours (09:15–15:30 IST).
- Transient error payloads are not written to the disk cache. Security-master fetches retain the last successful result and expose stale diagnostics.
- Technical indicator NaN and infinity values are normalized to JSON `null`; quote fields use Yahoo Chart API and do not fall back to fundamentals.

Run the full suite with:

```bash
.venv/bin/pytest -q
```

Run reliability tests with:

```bash
.venv/bin/pytest -q tests/test_reliability.py
```

## Important known constraints

1. Keep NSE `Accept-Encoding` restricted to `gzip, deflate`. Requesting Brotli (`br`) causes compressed responses that this environment does not decode correctly.
2. Do not restore `/api/searchAll`; it returns HTTP 404. Use the security-master CSV.
3. Do not restore `/api/equity-stockIndices`; it returns HTTP 404 in the current NSE API. Use supported NSE Indices CSV files and Yahoo Chart enrichment.
4. Yahoo `ticker.info` can fail with certificate, crumb, or HTTP 401 errors. The Chart API is the primary quote path; `ticker.info` is only a fallback for fields unavailable from Chart.
5. Filter history rows with incomplete OHLC values. Current-day Yahoo candles may contain volume but `NaN` OHLC fields.
6. These are unofficial/public endpoints. They may be delayed, rate-limited, changed, or unavailable. Do not represent the output as an exchange execution feed or use it as the sole source for high-stakes decisions.

## Change workflow

1. Read this file and inspect the relevant module before changing an endpoint.
2. Reproduce the issue with a focused test or diagnostic command before editing.
3. Keep MCP stdout JSON-RPC-clean. Logs and diagnostics must remain on stderr.
4. Run unit tests:

```bash
.venv/bin/pytest -q
```

5. Run live integration tests when network access is available:

```bash
.venv/bin/pytest -q -m integration
```

6. Verify the direct server and Hermes gateway layers:

```bash
hermes mcp test india_market
```

Expected result: connection succeeds and 60 tools are discovered unless the tool count intentionally changed.

## Test layout

- `tests/test_market_data.py`: deterministic unit tests with mocked clients.
- `tests/test_mcp_smoke.py`: live MCP and external-data smoke tests marked `integration`.
- Tests should cover both the response schema and the upstream failure mode. Avoid tests that only assert the subprocess starts.

## Current supported index CSVs

- `NIFTY 50` → `ind_nifty50list.csv`
- `NIFTY NEXT 50` → `ind_niftynext50list.csv`
- `NIFTY 100` → `ind_nifty100list.csv`
- `NIFTY 200` → `ind_nifty200list.csv`

When adding an index, update the mapping in `src/utils/nse.py`, add a deterministic parser test, and add or extend a live integration assertion.

## Hermes-specific completion checklist

Before reporting a change as complete:

- [ ] Focused regression test exists.
- [ ] `.venv/bin/pytest -q` passes.
- [ ] Direct JSON-RPC/MCP smoke test passes.
- [ ] `hermes mcp test india_market` passes.
- [ ] External endpoint limitations are documented rather than hidden.
- [ ] No secrets, credentials, or local cache files are committed.
