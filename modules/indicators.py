"""Pure pandas indicators — no numba/llvmlite, no native DLLs."""
import numpy as np
import pandas as pd


def sma(s: pd.Series, period: int) -> pd.Series:
    return s.rolling(period).mean()


def ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def rsi(s: pd.Series, period: int = 14) -> pd.Series:
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(s, fast) - ema(s, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _close_col(df: pd.DataFrame) -> pd.Series:
    for c in df.columns:
        if str(c).upper() == "CLOSE":
            return df[c]
    raise KeyError(f"No CLOSE column found. Columns: {list(df.columns)}")


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = _close_col(df)
    df["SMA_20"] = sma(close, 20)
    df["SMA_50"] = sma(close, 50)
    df["RSI_14"] = rsi(close, 14)
    m, s, h = macd(close)
    df["MACD"] = m
    df["MACD_Signal"] = s
    df["MACD_Hist"] = h
    return df