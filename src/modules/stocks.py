from mcp.server.fastmcp import FastMCP
from src.utils.nse import nse_get
from src.utils.yahoo import get_yf_info, get_yf_history, get_yf_ticker
from src.utils.cache import cached
import pandas as pd

def register(mcp: FastMCP):

    @mcp.tool()
    @cached(ttl=60, prefix="stock:quote")
    async def get_stock_quote(symbol: str) -> dict:
        """Get live stock quote with price, volume, 52-week range, P/E, market cap."""
        try:
            info = await get_yf_info(symbol)
            return {
                "symbol": symbol.upper(),
                "name": info.get("shortName", symbol),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "change": info.get("regularMarketChange"),
                "change_pct": info.get("regularMarketChangePercent"),
                "volume": info.get("volume"),
                "day_high": info.get("dayHigh"),
                "day_low": info.get("dayLow"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "pe_ratio": info.get("trailingPE"),
                "market_cap": info.get("marketCap"),
                "avg_volume": info.get("averageVolume"),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    @cached(ttl=300, prefix="stock:search")
    async def search_stocks(query: str) -> dict:
        """Search for stocks by name or symbol on NSE."""
        data = await nse_get("/api/searchAll")
        if not data:
            return {"error": "NSE search unavailable"}
        results = []
        q = query.upper()
        for item in data:
            if q in item.get("symbol", "").upper() or q in item.get("name", "").upper():
                results.append({"symbol": item.get("symbol"), "name": item.get("name"), "series": item.get("meta", {}).get("series")})
                if len(results) >= 20:
                    break
        return {"results": results, "count": len(results)}

    @mcp.tool()
    @cached(ttl=300, prefix="stock:history")
    async def get_stock_history(symbol: str, period: str = "1y") -> dict:
        """Get historical OHLCV data. Period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,max"""
        try:
            df = await get_yf_history(symbol, period=period)
            if df.empty:
                return {"error": "No data found"}
            df = df.tail(100)
            records = []
            for idx, row in df.iterrows():
                records.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                })
            return {"symbol": symbol.upper(), "data": records, "count": len(records)}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    @cached(ttl=60, prefix="stock:gainers")
    async def get_top_gainers(count: int = 10) -> dict:
        """Get top gaining stocks on NSE."""
        data = await nse_get("/api/topLosers")  # NSE uses topLosers for both
        if not data:
            return {"error": "Data unavailable"}
        stocks = data.get("data", [])[:count]
        return {"gainers": [{"symbol": s.get("symbol"), "name": s.get("meta", {}).get("companyName"), "price": s.get("lastPrice"), "change_pct": s.get("pChange"), "volume": s.get("totalTradedVolume")} for s in stocks]}

    @mcp.tool()
    @cached(ttl=60, prefix="stock:losers")
    async def get_top_losers(count: int = 10) -> dict:
        """Get top losing stocks on NSE."""
        data = await nse_get("/api/topLosers")
        if not data:
            return {"error": "Data unavailable"}
        stocks = data.get("data", [])[:count]
        return {"losers": [{"symbol": s.get("symbol"), "name": s.get("meta", {}).get("companyName"), "price": s.get("lastPrice"), "change_pct": s.get("pChange"), "volume": s.get("totalTradedVolume")} for s in stocks]}

    @mcp.tool()
    @cached(ttl=60, prefix="stock:active")
    async def get_most_active(count: int = 10) -> dict:
        """Get most traded stocks on NSE by volume."""
        data = await nse_get("/api/topLosers")
        if not data:
            return {"error": "Data unavailable"}
        stocks = sorted(data.get("data", []), key=lambda x: x.get("totalTradedVolume", 0), reverse=True)[:count]
        return {"most_active": [{"symbol": s.get("symbol"), "price": s.get("lastPrice"), "volume": s.get("totalTradedVolume"), "value": s.get("totalTradedValue")} for s in stocks]}

    @mcp.tool()
    @cached(ttl=600, prefix="stock:52whigh")
    async def get_52week_high() -> dict:
        """Get stocks at 52-week high on NSE."""
        data = await nse_get("/api/live-analysis-variations?index=NH")
        if not data:
            return {"error": "Data unavailable"}
        return {"stocks_52w_high": data.get("data", [])[:30]}

    @mcp.tool()
    @cached(ttl=600, prefix="stock:52wlow")
    async def get_52week_low() -> dict:
        """Get stocks at 52-week low on NSE."""
        data = await nse_get("/api/live-analysis-variations?index=NL")
        if not data:
            return {"error": "Data unavailable"}
        return {"stocks_52w_low": data.get("data", [])[:30]}

    @mcp.tool()
    @cached(ttl=600, prefix="stock:corporate_actions")
    async def get_corporate_actions(symbol: str) -> dict:
        """Get corporate actions (dividends, splits, bonuses) for a stock."""
        data = await nse_get(f"/api/corporates-corporateActions?index=equities&from_date=01-01-2024&to_date=31-12-2026")
        if not data:
            return {"error": "Data unavailable"}
        actions = [a for a in data if a.get("symbol", "").upper() == symbol.upper()]
        return {"symbol": symbol.upper(), "actions": actions}

    @mcp.tool()
    @cached(ttl=300, prefix="stock:financials")
    async def get_company_financials(symbol: str) -> dict:
        """Get company financials — income statement, balance sheet, key ratios."""
        try:
            info = await get_yf_info(symbol)
            return {
                "symbol": symbol.upper(),
                "name": info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"),
                "roce": info.get("returnOnCapital"),
                "debt_to_equity": info.get("debtToEquity"),
                "dividend_yield": info.get("dividendYield"),
                "profit_margins": info.get("profitMargins"),
                "operating_margins": info.get("operatingMargins"),
                "revenue": info.get("totalRevenue"),
                "net_income": info.get("netIncomeToCommon"),
                "eps": info.get("trailingEps"),
                "book_value": info.get("bookValue"),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def get_peer_comparison(symbol: str) -> dict:
        """Compare a stock with its industry peers."""
        try:
            info = await get_yf_info(symbol)
            sector = info.get("sector", "")
            industry = info.get("industry", "")
            return {
                "symbol": symbol.upper(),
                "sector": sector,
                "industry": industry,
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"),
                "market_cap": info.get("marketCap"),
                "profit_margin": info.get("profitMargins"),
                "note": "Use search_stocks to find peers in the same sector"
            }
        except Exception as e:
            return {"error": str(e)}
