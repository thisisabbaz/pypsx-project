"""Enrich dividend history with fiscal-period labels like PSX displays."""
import pandas as pd


def _period_label(dt) -> str:
    """Pakistani FY (Jul–Jun):
       Sep 30 → IQ
       Dec 31 → HYR
       Mar 31 → IIIQ
       Jun 30 → YR"""
    if pd.isna(dt):
        return ""
    m, d = dt.month, dt.day
    if m == 9 and d >= 25:  return "IQ"
    if m == 12 and d >= 25: return "HYR"
    if m == 3 and d >= 25:  return "IIIQ"
    if m == 6 and d >= 25:  return "YR"
    return ""


def _guess_period_end(ex_date):
    """Map ex-date month → most likely fiscal period end."""
    if pd.isna(ex_date):
        return pd.NaT
    m = ex_date.month
    y = ex_date.year
    if m in (10, 11):
        return pd.Timestamp(y, 9, 30)       # Q1 ended Sep 30 same year
    if m in (2, 3):
        return pd.Timestamp(y - 1, 12, 31)  # Half-year ended Dec 31 PREVIOUS year
    if m in (4, 5):
        return pd.Timestamp(y, 3, 31)       # Q3 ended Mar 31 same year
    if m in (8, 9):
        return pd.Timestamp(y, 6, 30)       # Year ended Jun 30 same year
    return pd.NaT


def enrich_dividends(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]

    date_col = None
    for c in ("EX-DIVIDEND DATE", "EX-DIVIDEND", "RECORD DATE"):
        if c in df.columns:
            date_col = c
            break
    if date_col is None:
        df["FINANCIAL RESULT"] = ""
        return df

    parsed = pd.to_datetime(df[date_col], errors="coerce")

    def fmt(dt):
        end = _guess_period_end(dt)
        if pd.isna(end):
            return ""
        label = _period_label(end)
        return f"{end:%d/%m/%Y}" + (f" ({label})" if label else "")

    df["FINANCIAL RESULT"] = parsed.apply(fmt)

    cols = list(df.columns)
    if "FINANCIAL RESULT" in cols:
        cols.remove("FINANCIAL RESULT")
        cols.insert(cols.index(date_col) + 1, "FINANCIAL RESULT")
        df = df[cols]
    return df