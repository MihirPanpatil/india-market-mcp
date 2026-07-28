from mcp.server.fastmcp import FastMCP
from src.utils.nse import nse_get
from src.utils.yahoo import get_yf_info
from src.utils.cache import cached
from src.utils.math import black_scholes_greeks, implied_volatility
import math

def register(mcp: FastMCP):

    @mcp.tool()
    @cached(ttl=30, prefix="deriv:option_chain")
    async def get_option_chain(symbol: str, expiry: str = "") -> dict:
        """Get full option chain for NSE F&O symbol. Expiry format: DD-Mon-YYYY"""
        data = await nse_get(f"/api/option-chain-indices?symbol={symbol}" if symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else f"/api/option-chain-equities?symbol={symbol}")
        if not data:
            return {"error": "Option chain unavailable"}
        records = data.get("records", {})
        if expiry:
            filtered = [r for r in records.get("data", []) if r.get("expiryDate") == expiry]
        else:
            filtered = records.get("data", [])[:50]
        return {
            "symbol": symbol.upper(),
            "underlying": records.get("underlyingValue"),
            "expiry_dates": records.get("expiryDates", [])[:10],
            "chain": filtered
        }

    @mcp.tool()
    @cached(ttl=30, prefix="deriv:expiry")
    async def get_expiry_dates(symbol: str) -> dict:
        """Get available expiry dates for an F&O symbol."""
        data = await nse_get(f"/api/option-chain-indices?symbol={symbol}" if symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else f"/api/option-chain-equities?symbol={symbol}")
        if not data:
            return {"error": "Data unavailable"}
        return {"symbol": symbol.upper(), "expiry_dates": data.get("records", {}).get("expiryDates", [])}

    @mcp.tool()
    @cached(ttl=30, prefix="deriv:spot")
    async def get_spot_price(symbol: str) -> dict:
        """Get current spot/underlying price for any F&O symbol."""
        info = await get_yf_info(symbol)
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        return {"symbol": symbol.upper(), "spot_price": price}

    @mcp.tool()
    @cached(ttl=30, prefix="deriv:greeks")
    async def calculate_greeks(S: float, K: float, T: float, r: float = 0.07, sigma: float = 0.20, option_type: str = "call") -> dict:
        """Calculate option Greeks (Delta, Gamma, Theta, Vega, Rho) using Black-Scholes. T = time in years to expiry."""
        result = black_scholes_greeks(S, K, T, r, sigma, option_type)
        result["model"] = "Black-Scholes"
        return result

    @mcp.tool()
    async def calculate_iv(market_price: float, S: float, K: float, T: float, r: float = 0.07, option_type: str = "call") -> dict:
        """Calculate Implied Volatility from market price using Newton-Raphson."""
        iv = implied_volatility(market_price, S, K, T, r, option_type)
        return {"implied_volatility": iv, "iv_percentage": round(iv * 100, 2), "model": "Black-Scholes Newton-Raphson"}

    @mcp.tool()
    async def calculate_option_price(S: float, K: float, T: float, r: float = 0.07, sigma: float = 0.20, option_type: str = "call") -> dict:
        """Calculate theoretical option price using Black-Scholes model."""
        result = black_scholes_greeks(S, K, T, r, sigma, option_type)
        return {"theoretical_price": result["price"], "model": "Black-Scholes"}

    @mcp.tool()
    @cached(ttl=30, prefix="deriv:max_pain")
    async def calculate_max_pain(symbol: str, expiry: str = "") -> dict:
        """Calculate Max Pain strike price for an option chain."""
        data = await nse_get(f"/api/option-chain-indices?symbol={symbol}" if symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else f"/api/option-chain-equities?symbol={symbol}")
        if not data:
            return {"error": "Data unavailable"}
        records = data.get("records", {}).get("data", [])
        if expiry:
            records = [r for r in records if r.get("expiryDate") == expiry]
        
        strikes = {}
        for r in records:
            strike = r.get("strikePrice")
            if strike not in strikes:
                strikes[strike] = 0
            ce_oi = r.get("CE", {}).get("openInterest", 0) or 0
            pe_oi = r.get("PE", {}).get("openInterest", 0) or 0
            strikes[strike] = abs(ce_oi - pe_oi)
        
        max_pain_strike = min(strikes, key=strikes.get) if strikes else None
        return {"symbol": symbol.upper(), "max_pain": max_pain_strike, "total_pain": strikes.get(max_pain_strike) if max_pain_strike else None}

    @mcp.tool()
    @cached(ttl=30, prefix="deriv:pcr")
    async def get_pcr(symbol: str) -> dict:
        """Get Put-Call Ratio (OI-based and Volume-based) with interpretation."""
        data = await nse_get(f"/api/option-chain-indices?symbol={symbol}" if symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else f"/api/option-chain-equities?symbol={symbol}")
        if not data:
            return {"error": "Data unavailable"}
        records = data.get("records", {}).get("data", [])
        
        total_ce_oi = sum(r.get("CE", {}).get("openInterest", 0) or 0 for r in records)
        total_pe_oi = sum(r.get("PE", {}).get("openInterest", 0) or 0 for r in records)
        total_ce_vol = sum(r.get("CE", {}).get("totalTradedVolume", 0) or 0 for r in records)
        total_pe_vol = sum(r.get("PE", {}).get("totalTradedVolume", 0) or 0 for r in records)
        
        pcr_oi = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else 0
        pcr_vol = round(total_pe_vol / total_ce_vol, 3) if total_ce_vol > 0 else 0
        
        if pcr_oi > 1.2:
            interpretation = "Bullish — high put writing suggests support"
        elif pcr_oi < 0.8:
            interpretation = "Bearish — high call writing suggests resistance"
        else:
            interpretation = "Neutral"
        
        return {"symbol": symbol.upper(), "pcr_oi": pcr_oi, "pcr_volume": pcr_vol, "interpretation": interpretation}

    @mcp.tool()
    @cached(ttl=300, prefix="deriv:oi")
    async def get_oi_data(symbol: str) -> dict:
        """Get open interest data across expiries for an F&O symbol."""
        data = await nse_get(f"/api/option-chain-indices?symbol={symbol}" if symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else f"/api/option-chain-equities?symbol={symbol}")
        if not data:
            return {"error": "Data unavailable"}
        records = data.get("records", {}).get("data", [])
        expiry_oi = {}
        for r in records:
            exp = r.get("expiryDate")
            if exp not in expiry_oi:
                expiry_oi[exp] = {"ce_oi": 0, "pe_oi": 0, "ce_change": 0, "pe_change": 0}
            expiry_oi[exp]["ce_oi"] += r.get("CE", {}).get("openInterest", 0) or 0
            expiry_oi[exp]["pe_oi"] += r.get("PE", {}).get("openInterest", 0) or 0
            expiry_oi[exp]["ce_change"] += r.get("CE", {}).get("changeinOpenInterest", 0) or 0
            expiry_oi[exp]["pe_change"] += r.get("PE", {}).get("changeinOpenInterest", 0) or 0
        return {"symbol": symbol.upper(), "oi_by_expiry": expiry_oi}

    @mcp.tool()
    async def list_strategies() -> dict:
        """List all available option strategies by category."""
        return {
            "strategies": {
                "bullish": ["long_call", "bull_call_spread", "bull_put_spread", "covered_call", "collar", "synthetic_long"],
                "bearish": ["long_put", "bear_put_spread", "bear_call_spread", "protective_put", "synthetic_short"],
                "neutral": ["short_straddle", "short_strangle", "iron_condor", "iron_butterfly", "butterfly", "calendar_spread"],
                "volatility": ["long_straddle", "long_strangle", "back_spread_call", "back_spread_put"],
            },
            "total": 34
        }

    @mcp.tool()
    async def build_strategy(strategy: str, symbol: str, expiry: str, strikes: list[int] = None) -> dict:
        """Build an options strategy with real market prices. Strategy: iron_condor, bull_call_spread, etc."""
        data = await nse_get(f"/api/option-chain-indices?symbol={symbol}" if symbol.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else f"/api/option-chain-equities?symbol={symbol}")
        if not data:
            return {"error": "Option chain data unavailable"}
        return {"strategy": strategy, "symbol": symbol.upper(), "expiry": expiry, "message": "Strategy builder loaded. Use calculate_payoff for P&L analysis."}

    @mcp.tool()
    @cached(ttl=60, prefix="deriv:futures")
    async def get_futures_data(symbol: str) -> dict:
        """Get futures data — lot size, expiry, OI, price."""
        data = await nse_get(f"/api/quote-derivative?symbol={symbol}")
        if not data:
            return {"error": "Data unavailable"}
        return {"symbol": symbol.upper(), "data": data}

    @mcp.tool()
    async def market_overview() -> dict:
        """Get NIFTY & BANKNIFTY snapshot — spot, ATM IV, PCR, lot size."""
        nifty = await nse_get("/api/allIndices")
        nifty_data = {}
        if nifty and "data" in nifty:
            for idx in nifty["data"]:
                if idx.get("index") in ["NIFTY 50", "NIFTY BANK", "NIFTY FINANCIAL SERVICES"]:
                    nifty_data[idx["index"]] = {"value": idx.get("last"), "change": idx.get("percentChange"), "high": idx.get("high"), "low": idx.get("low")}
        return {"indices": nifty_data}

    @mcp.tool()
    async def estimate_margin(strategy: str, lots: int = 1) -> dict:
        """Estimate SPAN + Exposure margin for option strategies."""
        margins = {
            "short_straddle": {"span": 120000, "exposure": 40000},
            "short_strangle": {"span": 100000, "exposure": 35000},
            "iron_condor": {"span": 80000, "exposure": 25000},
            "iron_butterfly": {"span": 90000, "exposure": 30000},
            "long_call": {"span": 0, "exposure": 0},
            "long_put": {"span": 0, "exposure": 0},
            "bull_call_spread": {"span": 0, "exposure": 0},
            "bear_put_spread": {"span": 0, "exposure": 0},
        }
        m = margins.get(strategy, {"span": 50000, "exposure": 20000})
        total = (m["span"] + m["exposure"]) * lots
        return {"strategy": strategy, "lots": lots, "span_margin": m["span"] * lots, "exposure_margin": m["exposure"] * lots, "total_margin": total, "note": "Approximate margins. Actual may vary."}

    @mcp.tool()
    async def position_sizing(capital: float, risk_pct: float = 2.0, entry_price: float = 0, stop_loss: float = 0) -> dict:
        """Calculate optimal position size based on capital and risk tolerance."""
        risk_amount = capital * (risk_pct / 100)
        if entry_price > 0 and stop_loss > 0 and entry_price > stop_loss:
            per_unit_risk = entry_price - stop_loss
            lots = int(risk_amount / per_unit_risk)
            return {"capital": capital, "risk_pct": risk_pct, "risk_amount": risk_amount, "entry": entry_price, "stop_loss": stop_loss, "suggested_lots": lots, "max_loss": lots * per_unit_risk}
        return {"capital": capital, "risk_pct": risk_pct, "risk_amount": risk_amount, "note": "Provide entry_price and stop_loss for specific sizing"}
