"""PSX data wrapper. Flattens MultiIndex columns from pypsx_toolkit."""
import pandas as pd
import pypsx_toolkit as pt


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            str(col[1]).upper() if len(col) > 1 and col[1] else str(col[0]).upper()
            for col in df.columns
        ]
    else:
        df.columns = [str(c).upper() for c in df.columns]
    return df


def get_stock_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Return OHLCV; empty DataFrame on any error."""
    try:
        df = pt.download(symbol.upper().strip(), period=period, interval="1d")
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    return _flatten_columns(df)


def get_batch_quotes(symbols):
    try:
        return pt.get_quote_batch([s.upper().strip() for s in symbols])
    except Exception:
        return {}


def get_top_performers():
    return pt.top_performers()