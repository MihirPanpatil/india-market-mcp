import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional
import asyncio


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
