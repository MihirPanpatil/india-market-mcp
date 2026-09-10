import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional
import asyncio
import httpx

_YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def _yahoo_symbol(symbol: str) -> str:
    value = symbol.upper().strip()
    return value if value.endswith((".NS", ".BO")) else f"{value}.NS"


async def get_yahoo_chart_quote(symbol: str) -> dict:
    """Read quote fields from Yahoo's chart endpoint (no crumb required)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{_yahoo_symbol(symbol)}"
    params = {"range": "1d", "interval": "1d", "events": "div,splits"}
    try:
        async with httpx.AsyncClient(headers=_YAHOO_HEADERS, timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = (response.json().get("chart", {}).get("result") or [None])[0]
            if not result:
                return {}
            meta = result.get("meta", {})
            quote = ((result.get("indicators", {}).get("quote") or [{}])[0])
            close = next((x for x in reversed(quote.get("close", [])) if x is not None), None)
            return {
                "symbol": meta.get("symbol", _yahoo_symbol(symbol)),
                "shortName": meta.get("longName") or meta.get("shortName") or symbol.upper(),
                "currency": meta.get("currency"),
                "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
                "currentPrice": meta.get("regularMarketPrice") or close,
                "regularMarketPrice": meta.get("regularMarketPrice") or close,
                "regularMarketChange": meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0) if meta.get("regularMarketPrice") is not None and meta.get("previousClose") is not None else None,
                "regularMarketChangePercent": meta.get("regularMarketChangePercent"),
                "volume": next((x for x in reversed(quote.get("volume", [])) if x is not None), None),
                "dayHigh": meta.get("regularMarketDayHigh"), "dayLow": meta.get("regularMarketDayLow"),
                "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"), "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
            }
    except Exception:
        return {}


def get_yf_ticker(symbol: str) -> yf.Ticker:
    if symbol.upper().endswith((".NS", ".BO")):
        return yf.Ticker(symbol)
    return yf.Ticker(f"{symbol}.NS")


async def get_yf_info(symbol: str) -> dict:
    ticker = get_yf_ticker(symbol)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(lambda: ticker.info or {}),
            timeout=20.0,
        )
    except (asyncio.TimeoutError, Exception):
        return {}


async def get_yf_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    ticker = get_yf_ticker(symbol)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(lambda: ticker.history(period=period, interval=interval)),
            timeout=20.0,
        )
    except (asyncio.TimeoutError, Exception):
        return pd.DataFrame()

def compute_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def compute_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def compute_bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
    sma = compute_sma(series, period)
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower
