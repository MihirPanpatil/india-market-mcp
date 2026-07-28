from mcp.server.fastmcp import FastMCP
from src.utils.yahoo import get_yf_history, compute_sma, compute_ema, compute_rsi, compute_macd, compute_bollinger_bands
from src.utils.cache import cached
import asyncio

def register(mcp: FastMCP):

    @mcp.tool()
    @cached(ttl=300, prefix="tech:indicators")
    async def get_technical_indicators(symbol: str) -> dict:
        """Get technical indicators — SMA, EMA, RSI, MACD, Bollinger Bands for a stock."""
        try:
            df = await asyncio.to_thread(lambda: get_yf_history.__wrapped__(symbol, period="6mo") if hasattr(get_yf_history, '__wrapped__') else None)
            if df is None or df.empty:
                ticker_obj = __import__("yfinance").Ticker(f"{symbol}.NS")
                df = await asyncio.to_thread(lambda: ticker_obj.history(period="6mo"))
            if df.empty:
                return {"error": "No data found"}
            
            close = df["Close"]
            sma_20 = compute_sma(close, 20).iloc[-1] if len(close) >= 20 else None
            sma_50 = compute_sma(close, 50).iloc[-1] if len(close) >= 50 else None
            ema_12 = compute_ema(close, 12).iloc[-1] if len(close) >= 12 else None
            ema_26 = compute_ema(close, 26).iloc[-1] if len(close) >= 26 else None
            rsi = compute_rsi(close, 14).iloc[-1] if len(close) >= 14 else None
            macd_line, signal_line, histogram = compute_macd(close)
            bb_upper, bb_middle, bb_lower = compute_bollinger_bands(close)
            
            return {
                "symbol": symbol.upper(),
                "current_price": round(close.iloc[-1], 2),
                "sma_20": round(sma_20, 2) if sma_20 else None,
                "sma_50": round(sma_50, 2) if sma_50 else None,
                "ema_12": round(ema_12, 2) if ema_12 else None,
                "ema_26": round(ema_26, 2) if ema_26 else None,
                "rsi_14": round(rsi, 2) if rsi else None,
                "macd": round(macd_line.iloc[-1], 2) if len(macd_line) > 0 else None,
                "macd_signal": round(signal_line.iloc[-1], 2) if len(signal_line) > 0 else None,
                "macd_histogram": round(histogram.iloc[-1], 2) if len(histogram) > 0 else None,
                "bb_upper": round(bb_upper.iloc[-1], 2) if len(bb_upper) > 0 else None,
                "bb_middle": round(bb_middle.iloc[-1], 2) if len(bb_middle) > 0 else None,
                "bb_lower": round(bb_lower.iloc[-1], 2) if len(bb_lower) > 0 else None,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def get_support_resistance(symbol: str) -> dict:
        """Get support and resistance levels using pivot points."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}.NS")
            df = await asyncio.to_thread(lambda: ticker.history(period="3mo"))
            if df.empty:
                return {"error": "No data found"}
            recent = df.tail(20)
            high = recent["High"].max()
            low = recent["Low"].min()
            close = recent["Close"].iloc[-1]
            
            pivot = (high + low + close) / 3
            r1 = 2 * pivot - low
            r2 = pivot + (high - low)
            r3 = high + 2 * (pivot - low)
            s1 = 2 * pivot - high
            s2 = pivot - (high - low)
            s3 = low - 2 * (high - pivot)
            
            return {
                "symbol": symbol.upper(),
                "pivot": round(pivot, 2),
                "resistance": {"r1": round(r1, 2), "r2": round(r2, 2), "r3": round(r3, 2)},
                "support": {"s1": round(s1, 2), "s2": round(s2, 2), "s3": round(s3, 2)},
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def detect_candlestick_patterns(symbol: str) -> dict:
        """Detect candlestick patterns — Doji, Hammer, Engulfing, etc."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}.NS")
            df = await asyncio.to_thread(lambda: ticker.history(period="3mo"))
            if df.empty or len(df) < 5:
                return {"error": "Insufficient data"}
            
            patterns = []
            recent = df.tail(30)
            for i in range(1, len(recent)):
                o, h, l, c = recent.iloc[i][["Open", "High", "Low", "Close"]]
                body = abs(c - o)
                upper_shadow = h - max(o, c)
                lower_shadow = min(o, c) - l
                total_range = h - l
                
                if total_range == 0:
                    continue
                body_ratio = body / total_range
                
                if body_ratio < 0.1:
                    patterns.append({"date": recent.index[i].strftime("%Y-%m-%d"), "pattern": "Doji", "signal": "Indecision"})
                elif lower_shadow > 2 * body and upper_shadow < body:
                    patterns.append({"date": recent.index[i].strftime("%Y-%m-%d"), "pattern": "Hammer", "signal": "Bullish reversal"})
                elif upper_shadow > 2 * body and lower_shadow < body:
                    patterns.append({"date": recent.index[i].strftime("%Y-%m-%d"), "pattern": "Shooting Star", "signal": "Bearish reversal"})
                
                if i >= 1:
                    prev_o, prev_c = recent.iloc[i-1][["Open", "Close"]]
                    if prev_c < prev_o and c > o and c > prev_o and o < prev_c:
                        patterns.append({"date": recent.index[i].strftime("%Y-%m-%d"), "pattern": "Bullish Engulfing", "signal": "Bullish reversal"})
                    elif prev_c > prev_o and c < o and c < prev_o and o > prev_c:
                        patterns.append({"date": recent.index[i].strftime("%Y-%m-%d"), "pattern": "Bearish Engulfing", "signal": "Bearish reversal"})
            
            return {"symbol": symbol.upper(), "patterns": patterns[-15:]}
        except Exception as e:
            return {"error": str(e)}
