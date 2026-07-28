from mcp.server.fastmcp import FastMCP
from src.utils.nse import nse_get
from src.utils.yahoo import get_yf_info, get_yf_history
from src.utils.cache import cached
import asyncio

def register(mcp: FastMCP):

    @mcp.tool()
    @cached(ttl=300, prefix="etf:all")
    async def get_all_etfs() -> dict:
        """Get all NSE ETFs with current prices."""
        data = await nse_get("/api/equity-stockIndices?index=NIFTY%20ETF")
        if not data:
            return {"error": "Data unavailable"}
        etfs = [{"symbol": e.get("symbol"), "price": e.get("last"), "change_pct": e.get("pChange"), "volume": e.get("totalTradedVolume")} for e in data.get("data", [])]
        return {"etfs": etfs, "count": len(etfs)}

    @mcp.tool()
    @cached(ttl=60, prefix="etf:quote")
    async def get_etf_quote(symbol: str) -> dict:
        """Get detailed ETF quote."""
        try:
            info = await get_yf_info(symbol)
            return {"symbol": symbol.upper(), "price": info.get("currentPrice"), "change_pct": info.get("regularMarketChangePercent"), "volume": info.get("volume"), "aum": info.get("totalAssets")}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    @cached(ttl=600, prefix="comm:price")
    async def get_commodity_price(commodity: str = "GC=F") -> dict:
        """Get commodity price (Gold: GC=F, Silver: SI=F, Crude: CL=F)."""
        try:
            info = await get_yf_info(commodity)
            return {"symbol": commodity, "price": info.get("currentPrice"), "change": info.get("regularMarketChange"), "change_pct": info.get("regularMarketChangePercent"), "name": info.get("shortName")}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def get_all_commodity_prices() -> dict:
        """Get prices for major commodities — Gold, Silver, Crude Oil, Natural Gas."""
        commodities = {"Gold": "GC=F", "Silver": "SI=F", "Crude Oil": "CL=F", "Natural Gas": "NG=F"}
        results = {}
        for name, symbol in commodities.items():
            try:
                info = await get_yf_info(symbol)
                results[name] = {"symbol": symbol, "price": info.get("currentPrice"), "change_pct": info.get("regularMarketChangePercent")}
            except Exception:
                results[name] = {"error": "unavailable"}
        return {"commodities": results}

    @mcp.tool()
    @cached(ttl=300, prefix="curr:rate")
    async def get_currency_rate(pair: str = "USDINR=X") -> dict:
        """Get currency exchange rate (USDINR=X, EURINR=X, GBPINR=X)."""
        try:
            info = await get_yf_info(pair)
            return {"pair": pair, "rate": info.get("regularMarketPrice"), "change": info.get("regularMarketChange"), "change_pct": info.get("regularMarketChangePercent")}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def get_all_currency_rates() -> dict:
        """Get all major INR exchange rates."""
        pairs = {"USD/INR": "USDINR=X", "EUR/INR": "EURINR=X", "GBP/INR": "GBPINR=X", "JPY/INR": "JPYINR=X"}
        results = {}
        for name, symbol in pairs.items():
            try:
                info = await get_yf_info(symbol)
                results[name] = {"rate": info.get("regularMarketPrice"), "change_pct": info.get("regularMarketChangePercent")}
            except Exception:
                results[name] = {"error": "unavailable"}
        return {"rates": results}

    @mcp.tool()
    @cached(ttl=86400, prefix="sgb:all")
    async def get_sovereign_gold_bonds() -> dict:
        """Get all Sovereign Gold Bonds listed on NSE."""
        data = await nse_get("/api/merged-daily-reports?key=favSgb")
        if not data:
            return {"error": "Data unavailable"}
        return {"sgbs": data.get("data", [])[:20]}

    @mcp.tool()
    @cached(ttl=300, prefix="screener:basic")
    async def screen_stocks(min_price: float = 0, max_price: float = 999999, min_volume: float = 0, sector: str = "") -> dict:
        """Screen stocks by price, volume, and sector filters."""
        data = await nse_get("/api/equity-stockIndices?index=NIFTY%2050")
        if not data:
            return {"error": "Data unavailable"}
        results = []
        for s in data.get("data", []):
            price = s.get("last", 0) or 0
            volume = s.get("totalTradedVolume", 0) or 0
            if min_price <= price <= max_price and volume >= min_volume:
                results.append({"symbol": s.get("symbol"), "price": price, "change_pct": s.get("pChange"), "volume": volume})
        return {"results": results[:30], "count": len(results)}

    @mcp.tool()
    @cached(ttl=300, prefix="screener:fundamental")
    async def screen_by_fundamentals(min_pe: float = 0, max_pe: float = 100, min_roe: float = 0) -> dict:
        """Screen stocks by fundamental ratios — P/E, ROE, market cap."""
        try:
            import yfinance as yf
            nifty50 = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "MARUTI", "TITAN", "SUNPHARMA", "ASIANPAINT", "HCLTECH", "WIPRO", "TATAMOTORS"]
            results = []
            for symbol in nifty50:
                try:
                    info = await asyncio.to_thread(lambda s=symbol: yf.Ticker(f"{s}.NS").info or {})
                    pe = info.get("trailingPE", 0) or 0
                    roe = (info.get("returnOnEquity", 0) or 0) * 100
                    if min_pe <= pe <= max_pe and roe >= min_roe:
                        results.append({"symbol": symbol, "pe": round(pe, 2), "roe": round(roe, 2), "market_cap": info.get("marketCap"), "price": info.get("currentPrice")})
                except Exception:
                    continue
            return {"results": results[:20], "count": len(results)}
        except Exception as e:
            return {"error": str(e)}
