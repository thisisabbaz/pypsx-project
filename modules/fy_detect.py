"""Auto-detect fiscal year end from announcements; cache in data/fy_ends.json."""
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

CACHE_PATH = Path("data/fy_ends.json")
DEFAULT_FY_END = (6, 30)  # Pakistan's most common

MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Last-resort overrides for symbols where announcements may be missing
FY_END_OVERRIDES = {
    "HBL": (12, 31), "MCB": (12, 31), "UBL": (12, 31),
    "BAHL": (12, 31), "BAFL": (12, 31), "MEBL": (12, 31),
    "NBP": (12, 31), "AKBL": (12, 31), "FABL": (12, 31),
    "BOP": (12, 31), "SNBL": (12, 31), "JSBL": (12, 31),
}


def _load_cache():
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def _detect_from_announcements(ann_df) -> tuple[int, int] | None:
    """Scan titles for 'YEAR ENDED <Month> <Day>, <Year>'."""
    if ann_df is None or ann_df.empty:
        return None
    df = ann_df.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]
    title_col = next((c for c in df.columns if "TITLE" in c), None)
    if not title_col:
        return None

    month_alt = "|".join(sorted(MONTH_MAP.keys(), key=len, reverse=True))
    pattern = re.compile(
        rf"year\s+ended\s+({month_alt})\s+(\d{{1,2}})",
        re.IGNORECASE,
    )

    hits = []
    for title in df[title_col].astype(str):
        m = pattern.search(title)
        if not m:
            continue
        mon = MONTH_MAP.get(m.group(1).lower())
        try:
            day = int(m.group(2))
        except ValueError:
            continue
        if mon and 1 <= day <= 31:
            hits.append((mon, day))

    if not hits:
        return None
    return Counter(hits).most_common(1)[0][0]


def get_fy_end(symbol: str, ann_df=None, force_refresh: bool = False) -> tuple[int, int]:
    """
    Return (month, day) of the fiscal year end for `symbol`.
    Lookup order: cache → detect from announcements → overrides → default.
    """
    symbol = symbol.upper().strip()

    cache = _load_cache()
    if not force_refresh and symbol in cache:
        e = cache[symbol]
        return int(e["month"]), int(e["day"])

    detected = _detect_from_announcements(ann_df) if ann_df is not None else None

    if detected is None:
        detected = FY_END_OVERRIDES.get(symbol, DEFAULT_FY_END)

    cache[symbol] = {"month": detected[0], "day": detected[1]}
    _save_cache(cache)
    return detected