"""Portfolio math: cost basis, market value, P&L."""
import pandas as pd


def _extract_price(q) -> float | None:
    if q is None:
        return None
    if isinstance(q, (int, float)):
        return float(q)
    if isinstance(q, dict):
        for k in ("price", "close", "Close", "CLOSE", "last", "Last", "current"):
            v = q.get(k)
            if v is None:
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _price_from_history(symbol: str) -> float | None:
    """Latest CLOSE from 5d history — most reliable source."""
    try:
        from modules.psx_data import get_stock_history
        df = get_stock_history(symbol, period="5d")
        if df is None or df.empty:
            return None
        return float(df.iloc[-1]["CLOSE"])
    except Exception:
        return None


def fetch_quotes(symbols):
    """
    Returns {symbol: price_float}. Uses history as the primary source
    since it's proven reliable; batch quotes are only a fallback.
    """
    quotes = {}
    for s in symbols:
        p = _price_from_history(s)
        if p is not None:
            quotes[s] = p
    return quotes


def compute_portfolio(portfolio: dict, quotes: dict) -> pd.DataFrame:
    rows = []
    for sym, info in portfolio.items():
        shares = float(info["shares"])
        buy = float(info["buy_price"])
        cost = shares * buy
        price = quotes.get(sym)
        if not isinstance(price, (int, float)):
            price = _extract_price(price)

        mv = shares * price if price is not None else None
        pnl = (mv - cost) if mv is not None else None
        pnl_pct = (pnl / cost * 100) if (pnl is not None and cost) else None

        rows.append({
            "Symbol": sym,
            "Shares": shares,
            "Buy": buy,
            "Cost": round(cost, 2),
            "Price": round(price, 2) if price is not None else None,
            "Market Value": round(mv, 2) if mv is not None else None,
            "P&L": round(pnl, 2) if pnl is not None else None,
            "P&L %": round(pnl_pct, 2) if pnl_pct is not None else None,
        })
    return pd.DataFrame(rows)