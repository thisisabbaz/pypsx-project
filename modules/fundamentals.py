"""Parse pipe-separated fundamental values into FY columns with trends."""
import re
from datetime import date

import pandas as pd

from modules.fy_detect import get_fy_end

PIPE_ORDER = "newest_first"   # PSX normally displays newest-first
TREND_DEADBAND_PCT = 5.0      # ±5% considered flat


def _to_float(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s or s.lower() in ("nan", "none", "-", "n/a"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    clean = re.sub(r"[^\d.\-]", "", s.replace(",", ""))
    if not clean or clean == "-":
        return None
    try:
        v = float(clean)
        return -v if neg else v
    except ValueError:
        return None


def _split_pipe(v):
    if v is None:
        return []
    s = str(v).strip()
    if "|" not in s:
        return []
    return [p.strip() for p in s.split("|")]


def _fmt_number(x):
    if x is None:
        return "—"
    if abs(x) >= 1_000_000:
        return f"{x/1_000_000:,.2f}M"
    if abs(x) >= 1_000:
        return f"{x:,.2f}"
    return f"{x:,.2f}"


def _trend_arrow(vals):
    """vals newest-first. Compare vals[0] vs vals[1]."""
    if len(vals) < 2 or vals[0] is None or vals[1] is None or vals[1] == 0:
        return ""
    pct = (vals[0] / abs(vals[1]) - 1) * 100
    if pct >= TREND_DEADBAND_PCT:
        return f"▲ +{pct:.1f}%"
    if pct <= -TREND_DEADBAND_PCT:
        return f"▼ {pct:.1f}%"
    return f" {pct:+.1f}%"


def _year_labels(fy_end: tuple[int, int], n: int) -> list[str]:
    month, day = fy_end
    today = date.today()
    if (today.month, today.day) >= (month, day):
        latest = today.year
    else:
        latest = today.year - 1
    labels = [f"FY{latest - i}" for i in range(n)]
    return labels if PIPE_ORDER == "newest_first" else list(reversed(labels))


def clean_fundamentals(df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
    """Forward-fill CATEGORY, drop blank rows. Returns long-form CATEGORY|METRIC|VALUE."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["CATEGORY", "METRIC", "VALUE"])
    df = df.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]

    if "METRIC" not in df.columns and "VALUE" in df.columns:
        df = df.reset_index().rename(columns={"index": "METRIC"})

    if "CATEGORY" in df.columns:
        df["CATEGORY"] = df["CATEGORY"].ffill().fillna("General")

    df["VALUE"] = df["VALUE"].astype(str).str.strip()
    df["METRIC"] = df["METRIC"].astype(str).str.strip()
    mask = ~(
        df["METRIC"].str.lower().isin(["", "nan", "none"]) &
        df["VALUE"].str.lower().isin(["", "nan", "none"])
    )
    return df[mask].reset_index(drop=True)


def _expand_row(metric: str, raw_value: str, fy_end: tuple[int, int]):
    parts = _split_pipe(raw_value)
    if not parts:
        num = _to_float(raw_value)
        return {"Metric": metric,
                "Value": raw_value if num is None else _fmt_number(num)}

    nums = [_to_float(p) for p in parts]
    labels = _year_labels(fy_end, len(nums))
    row = {"Metric": metric}
    for label, n in zip(labels, nums):
        row[label] = _fmt_number(n)
    row["Trend"] = _trend_arrow(nums)
    return row


def grouped_display(df: pd.DataFrame, symbol: str = "", fy_end=None) -> dict:
    """Return {category: wide DataFrame with FY columns + Trend}."""
    if df is None or df.empty:
        return {}
    if fy_end is None:
        fy_end = get_fy_end(symbol)

    result = {}
    for cat, sub in df.groupby("CATEGORY", sort=False):
        rows = [_expand_row(r["METRIC"], r["VALUE"], fy_end) for _, r in sub.iterrows()]
        cols = []
        for r in rows:
            for k in r.keys():
                if k not in cols:
                    cols.append(k)
        if "Trend" in cols:
            cols.remove("Trend")
            cols.append("Trend")
        out = pd.DataFrame(rows)
        for c in cols:
            if c not in out.columns:
                out[c] = ""
        result[cat] = out[cols].reset_index(drop=True)
    return result