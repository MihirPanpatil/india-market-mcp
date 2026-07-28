from mcp.server.fastmcp import FastMCP
from src.utils.nse import nse_get
from src.utils.yahoo import get_yf_info, get_yf_history
from src.utils.cache import cached
from src.utils.math import calculate_sip, calculate_xirr
import yfinance as yf

def register(mcp: FastMCP):

    @mcp.tool()
    @cached(ttl=3600, prefix="mf:search")
    async def search_mutual_funds(query: str) -> dict:
        """Search mutual funds by name across 47,000+ AMFI schemes."""
        try:
            from mftool import Mftool
            mf = Mftool()
            import asyncio
            all_schemes = await asyncio.to_thread(mf.get_scheme_codes)
            results = []
            q = query.upper()
            for code, name in all_schemes.items():
                if q in name.upper():
                    results.append({"scheme_code": code, "scheme_name": name})
                    if len(results) >= 20:
                        break
            return {"results": results, "count": len(results)}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    @cached(ttl=900, prefix="mf:nav")
    async def get_mf_nav(scheme_code: str) -> dict:
        """Get latest NAV for a mutual fund scheme."""
        try:
            from mftool import Mftool
            mf = Mftool()
            import asyncio
            quote = await asyncio.to_thread(mf.get_scheme_quote, scheme_code)
            return {"scheme_code": scheme_code, "data": quote}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    @cached(ttl=3600, prefix="mf:history")
    async def get_mf_history(scheme_code: str) -> dict:
        """Get full historical NAV for a mutual fund scheme."""
        try:
            from mftool import Mftool
            mf = Mftool()
            import asyncio
            history = await asyncio.to_thread(mf.get_scheme_historical_nav, scheme_code)
            if isinstance(history, dict) and "data" in history:
                return {"scheme_code": scheme_code, "nav_count": len(history["data"]), "recent": history["data"][:30]}
            return {"scheme_code": scheme_code, "data": history}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def compare_mutual_funds(scheme_codes: list[str]) -> dict:
        """Compare 2-4 mutual funds side by side."""
        try:
            from mftool import Mftool
            mf = Mftool()
            import asyncio
            results = []
            for code in scheme_codes:
                quote = await asyncio.to_thread(mf.get_scheme_quote, code)
                results.append({"scheme_code": code, "data": quote})
            return {"comparison": results}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    @cached(ttl=3600, prefix="mf:performance")
    async def get_equity_scheme_performance() -> dict:
        """Get equity mutual fund performance (1Y, 3Y, 5Y returns)."""
        try:
            from mftool import Mftool
            mf = Mftool()
            import asyncio
            perf = await asyncio.to_thread(mf.get_openended_equity_scheme_performance)
            return {"performance": perf[:50] if isinstance(perf, list) else perf}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def analyze_mutual_fund(scheme_code: str) -> dict:
        """Deep mutual fund analysis — returns, Sharpe ratio, max drawdown."""
        try:
            from mftool import Mftool
            mf = Mftool()
            import asyncio
            import pandas as pd
            history = await asyncio.to_thread(mf.get_scheme_historical_nav, scheme_code)
            if not history or "data" not in history:
                return {"error": "No data found"}
            navs = history["data"]
            if len(navs) < 30:
                return {"error": "Insufficient data for analysis"}
            nav_series = [float(n.get("nav", 0)) for n in navs[:min(len(navs), 1000)]]
            nav_series.reverse()
            
            returns = [(nav_series[i] - nav_series[i-1]) / nav_series[i-1] for i in range(1, len(nav_series))]
            avg_return = sum(returns) / len(returns) if returns else 0
            std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0
            
            annualized_return = avg_return * 252
            annualized_vol = std_dev * (252 ** 0.5)
            sharpe = annualized_return / annualized_vol if annualized_vol > 0 else 0
            
            cumulative = 1
            peak = 1
            max_drawdown = 0
            for r in returns:
                cumulative *= (1 + r)
                peak = max(peak, cumulative)
                dd = (peak - cumulative) / peak
                max_drawdown = max(max_drawdown, dd)
            
            return {
                "scheme_code": scheme_code,
                "total_return_pct": round((nav_series[-1] / nav_series[0] - 1) * 100, 2) if nav_series else 0,
                "annualized_return": round(annualized_return * 100, 2),
                "annualized_volatility": round(annualized_vol * 100, 2),
                "sharpe_ratio": round(sharpe, 3),
                "max_drawdown_pct": round(max_drawdown * 100, 2),
                "latest_nav": nav_series[-1] if nav_series else None,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def calculate_sip_returns(monthly_amount: float, annual_return_pct: float, years: int) -> dict:
        """Calculate SIP maturity value and total investment."""
        monthly_rate = annual_return_pct / 100 / 12
        months = years * 12
        if monthly_rate == 0:
            future_value = monthly_amount * months
        else:
            future_value = monthly_amount * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
        invested = monthly_amount * months
        wealth_gained = future_value - invested
        return {
            "monthly_sip": monthly_amount,
            "years": years,
            "expected_return_pct": annual_return_pct,
            "total_invested": round(invested, 2),
            "maturity_value": round(future_value, 2),
            "wealth_gained": round(wealth_gained, 2),
        }

    @mcp.tool()
    async def calculate_xirr(cashflows: list) -> dict:
        """Calculate XIRR for irregular cash flows. Cashflows: [{"date": "YYYY-MM-DD", "amount": 5000}]"""
        try:
            from datetime import datetime
            dates = [datetime.strptime(cf["date"], "%Y-%m-%d") for cf in cashflows]
            amounts = [cf["amount"] for cf in cashflows]
            d0 = dates[0]
            days = [(d - d0).days / 365.0 for d in dates]
            
            def npv(rate):
                return sum(a / (1 + rate) ** t for a, t in zip(amounts, days))
            
            def npv_deriv(rate):
                return sum(-t * a / (1 + rate) ** (t + 1) for a, t in zip(amounts, days))
            
            rate = 0.1
            for _ in range(200):
                f = npv(rate)
                fp = npv_deriv(rate)
                if abs(fp) < 1e-12:
                    break
                rate -= f / fp
                if abs(f) < 0.001:
                    break
            
            return {"xirr_pct": round(rate * 100, 2), "cashflows_count": len(cashflows)}
        except Exception as e:
            return {"error": str(e)}
