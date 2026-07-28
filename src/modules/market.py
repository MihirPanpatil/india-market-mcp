from mcp.server.fastmcp import FastMCP
from src.utils.nse import nse_get
from src.utils.cache import cached

def register(mcp: FastMCP):

    @mcp.tool()
    @cached(ttl=30, prefix="market:status")
    async def get_market_status() -> dict:
        """Check if NSE market is currently open, closed, or pre-market."""
        data = await nse_get("/api/marketStatus")
        if not data:
            return {"error": "Data unavailable"}
        return {"market_status": data.get("marketState", [])}

    @mcp.tool()
    @cached(ttl=60, prefix="market:fii_dii")
    async def get_fii_dii_data() -> dict:
        """Get FII (Foreign Institutional Investors) and DII (Domestic Institutional Investors) buy/sell data."""
        data = await nse_get("/api/fiidiiTradeReact")
        if not data:
            return {"error": "Data unavailable"}
        return {"fii_dii": data}

    @mcp.tool()
    @cached(ttl=60, prefix="market:breadth")
    async def get_advances_declines() -> dict:
        """Get market breadth — advances vs declines."""
        data = await nse_get("/api/equity-stockIndices?index=NIFTY%2050")
        if not data:
            return {"error": "Data unavailable"}
        advances = sum(1 for s in data.get("data", []) if s.get("pChange", 0) > 0)
        declines = sum(1 for s in data.get("data", []) if s.get("pChange", 0) < 0)
        unchanged = sum(1 for s in data.get("data", []) if s.get("pChange", 0) == 0)
        return {"advances": advances, "declines": declines, "unchanged": unchanged, "total": advances + declines + unchanged}

    @mcp.tool()
    @cached(ttl=300, prefix="market:ipo_current")
    async def get_upcoming_ipos() -> dict:
        """Get upcoming and ongoing IPOs on NSE."""
        data = await nse_get("/api/ipo-current-ipos")
        if not data:
            return {"error": "Data unavailable"}
        return {"ipos": data.get("data", [])}

    @mcp.tool()
    @cached(ttl=3600, prefix="market:ipo_past")
    async def get_past_ipos() -> dict:
        """Get recently listed IPOs and their performance."""
        data = await nse_get("/api/ipo-past-ipos")
        if not data:
            return {"error": "Data unavailable"}
        return {"ipos": data.get("data", [])[:20]}

    @mcp.tool()
    @cached(ttl=300, prefix="market:announcements")
    async def get_nse_announcements() -> dict:
        """Get latest corporate announcements from NSE."""
        data = await nse_get("/api/home-corporate-announcements?index=equities")
        if not data:
            return {"error": "Data unavailable"}
        return {"announcements": data.get("data", [])[:30]}

    @mcp.tool()
    @cached(ttl=600, prefix="market:board_meetings")
    async def get_board_meetings() -> dict:
        """Get upcoming board meeting dates for corporate actions."""
        data = await nse_get("/api/corporates-board-meetings?index=equities")
        if not data:
            return {"error": "Data unavailable"}
        return {"board_meetings": data.get("data", [])[:30]}

    @mcp.tool()
    @cached(ttl=300, prefix="market:news")
    async def get_market_news(count: int = 10) -> dict:
        """Get latest Indian market news from Google News."""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://news.google.com/rss/search?q=indian+stock+market+NSE&hl=en-IN&gl=IN&ceid=IN:en", timeout=10)
                if resp.status_code == 200:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(resp.text)
                    items = root.findall(".//item")[:count]
                    news = [{"title": item.find("title").text, "link": item.find("link").text, "pubDate": item.find("pubDate").text} for item in items if item.find("title") is not None]
                    return {"news": news}
        except Exception:
            pass
        return {"error": "News unavailable"}

    @mcp.tool()
    @cached(ttl=600, prefix="market:bulk_deals")
    async def get_bulk_deals() -> dict:
        """Get recent bulk deals on NSE."""
        data = await nse_get("/api/snapshot-capital-market-largedeal")
        if not data:
            return {"error": "Data unavailable"}
        return {"bulk_deals": data.get("data", [])[:20]}

    @mcp.tool()
    @cached(ttl=600, prefix="market:block_deals")
    async def get_block_deals() -> dict:
        """Get recent block deals on NSE (trades >= 10 crore)."""
        data = await nse_get("/api/snapshot-capital-market-largedeal")
        if not data:
            return {"error": "Data unavailable"}
        return {"block_deals": data.get("data", [])[:20]}

    @mcp.tool()
    @cached(ttl=86400, prefix="market:holidays")
    async def get_market_holidays() -> dict:
        """Get NSE market holidays for the current year."""
        data = await nse_get("/api/holiday-master?type=trading")
        if not data:
            return {"error": "Data unavailable"}
        return {"holidays": data}
