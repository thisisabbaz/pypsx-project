"""MUFAP NAV loader — reads local Excel, no scraping."""
from pathlib import Path

import pandas as pd

LOCAL_XLSX = Path("data/mufap_navs.xlsx")


def load_mufap_excel(path: Path) -> pd.DataFrame:
    """Read MUFAP 'Nav And Sales Load' Excel export.
    Finds the header row by looking for 'Sector' + 'AMC'."""
    raw = pd.read_excel(path, sheet_name=0, header=None)

    header_row = None
    for i in range(min(15, len(raw))):
        vals = [str(v).strip().lower() for v in raw.iloc[i].tolist()]
        if "sector" in vals and "amc" in vals:
            header_row = i
            break

    if header_row is None:
        raise ValueError(
            "Could not find MUFAP header row (expected 'Sector' and 'AMC')."
        )

    df = pd.read_excel(path, sheet_name=0, header=header_row)
    df = df.dropna(how="all").reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]

    for col in ("Offer", "Repurchase", "NAV",
                "Front-end", "Back-end", "Contingent", "Market"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def fetch_mufap_navs() -> pd.DataFrame:
    """Return local MUFAP Excel if present, else raise a helpful error."""
    if not LOCAL_XLSX.exists():
        raise FileNotFoundError(
            f"No local MUFAP file at {LOCAL_XLSX}. "
            "Download 'Nav And Sales Load' Excel from mufap.com.pk "
            "and either upload it from the Mutual Funds page or save it there."
        )
    return load_mufap_excel(LOCAL_XLSX)


def save_uploaded_mufap(file_bytes: bytes) -> Path:
    """Persist an uploaded Excel file to data/mufap_navs.xlsx."""
    LOCAL_XLSX.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_XLSX.write_bytes(file_bytes)
    return LOCAL_XLSX