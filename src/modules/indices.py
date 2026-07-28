from mcp.server.fastmcp import FastMCP
from src.utils.nse import nse_get
from src.utils.yahoo import get_yf_info, get_yf_history
from src.utils.cache import cached
from src.utils.math import calculate_sip, calculate_xirr
import yfinance as yf

def register(mcp: FastMCP):

    @mcp.tool()
    @cached(ttl=60, prefix="idx:all")
    async def get_all_indices() -> dict:
        """Get all NSE indices with current values."""
        data = await nse_get("/api/allIndices")
        if not data:
            return {"error": "Data unavailable"}
        indices = []
        for idx in data.get("data", []):
            indices.append({
                "name": idx.get("index"),
                "value": idx.get("last"),
                "change": idx.get("percentChange"),
                "high": idx.get("high"),
                "low": idx.get("low"),
                "prev_close": idx.get("previousClose"),
            })
        return {"indices": indices, "count": len(indices)}

    @mcp.tool()
    @cached(ttl=60, prefix="idx:constituents")
    async def get_index_constituents(index: str = "NIFTY 50") -> dict:
        """Get all stocks in an index with live prices."""
        data = await nse_get(f"/api/equity-stockIndices?index={index.upper()}")
        if not data:
            return {"error": "Data unavailable"}
        stocks = []
        for s in data.get("data", []):
            stocks.append({"symbol": s.get("symbol"), "price": s.get("last"), "change_pct": s.get("pChange"), "volume": s.get("totalTradedVolume"), "52w_high": s.get("meta", {}).get("weekHighLow", {}).get("max"), "52w_low": s.get("meta", {}).get("weekHighLow", {}).get("min")})
        return {"index": index, "stocks": stocks, "count": len(stocks)}

    @mcp.tool()
    @cached(ttl=600, prefix="idx:sector")
    async def get_sector_performance() -> dict:
        """Get sectoral indices ranked by performance."""
        data = await nse_get("/api/allIndices")
        if not data:
            return {"error": "Data unavailable"}
        sectors = [idx for idx in data.get("data", []) if "SECTORAL" in idx.get("index", "").upper() or any(s in idx.get("index", "") for s in ["NIFTY AUTO", "NIFTY BANK", "NIFTY ENERGY", "NIFTY FMCG", "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA", "NIFTY PVT BANK", "NIFTY PSU BANK", "NIFTY REALTY"])]
        sectors.sort(key=lambda x: x.get("percentChange", 0), reverse=True)
        return {"sectors": [{"name": s.get("index"), "change_pct": s.get("percentChange"), "value": s.get("last")} for s in sectors[:20]]}
