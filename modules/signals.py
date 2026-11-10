"""Signal logic: swing candidates + holding decisions."""
import pandas as pd

from modules.psx_data import get_stock_history
from modules.indicators import add_indicators


def _pct_change_over(df, days):
    if len(df) < days + 1:
        return None
    old = df["CLOSE"].iloc[-(days + 1)]
    new = df["CLOSE"].iloc[-1]
    if pd.isna(old) or old == 0:
        return None
    return (new / old - 1) * 100


def scan_swing(symbols, rsi_thresh=35, sma_band=2.0, period="6mo"):
    results = []
    for sym in symbols:
        try:
            df = get_stock_history(sym, period=period)
            if df is None or df.empty or len(df) < 50:
                continue
            df = add_indicators(df)

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            close = float(latest["CLOSE"])
            sma20 = float(latest["SMA_20"])
            sma50 = float(latest["SMA_50"])
            rsi = float(latest["RSI_14"])
            macd_now = float(latest["MACD_Hist"])
            macd_prev = float(prev["MACD_Hist"])

            above_sma50 = close > sma50
            signals = []

            if rsi < rsi_thresh:
                signals.append(f"RSI<{rsi_thresh}")
            if sma20 == sma20 and close <= sma20 * (1 + sma_band / 100):
                signals.append("Near SMA20")
            if macd_now > 0 and macd_prev <= 0:
                signals.append("MACD cross↑")

            if not signals:
                continue

            if rsi < rsi_thresh and above_sma50:
                verdict = "SWING CANDIDATE"
            elif rsi < rsi_thresh and not above_sma50:
                verdict = "AVOID (below SMA50)"
            else:
                verdict = "WATCH"

            recent_low = float(df["LOW"].tail(20).min())
            recent_high = float(df["HIGH"].tail(20).max())
            entry_low = round(close * 0.995, 2)
            entry_high = round(close * 1.005, 2)
            stop = round(recent_low * 0.99, 2)
            risk = entry_high - stop
            target_1 = round(max(recent_high, entry_high * 1.03), 2)
            target_2 = round(max(target_1 * 1.05, entry_high + 2 * risk), 2)

            results.append({
                "Symbol": sym,
                "Close": round(close, 2),
                "RSI": round(rsi, 1),
                "SMA20": round(sma20, 2) if sma20 == sma20 else None,
                "SMA50": round(sma50, 2) if sma50 == sma50 else None,
                "Above SMA50": above_sma50,
                "Signals": ", ".join(signals),
                "Verdict": verdict,
                "Entry Low": entry_low,
                "Entry High": entry_high,
                "Stop Loss": stop,
                "Target 1": target_1,
                "Target 2": target_2,
            })
        except Exception:
            continue
    return sorted(results, key=lambda r: r["RSI"])


def evaluate_holdings(portfolio):
    """Apply the Decision Cheat Sheet to each holding."""
    results = []
    for sym, info in portfolio.items():
        try:
            df = get_stock_history(sym, period="3mo")
            if df is None or df.empty or len(df) < 22:
                results.append({
                    "Symbol": sym,
                    "Action": "NO DATA",
                    "Reason": "insufficient history",
                })
                continue
            df = add_indicators(df)

            latest = df.iloc[-1]
            close = float(latest["CLOSE"])
            sma50 = float(latest["SMA_50"])
            rsi = float(latest["RSI_14"])
            buy = float(info["buy_price"])

            pnl_pct = (close / buy - 1) * 100
            pnl_1mo = _pct_change_over(df, 21)
            above_sma50 = close > sma50
            thesis = str(info.get("thesis", "intact")).lower()

            action, reasons = "HOLD", []

            if pnl_pct >= 15 and rsi > 70:
                action = "TRIM 1/3"
                reasons.append("up 15%+, RSI>70 → trim 1/3, let rest run")

            if pnl_pct <= -8 and not above_sma50:
                if thesis == "broken":
                    action = "CUT"
                    reasons.append("down 8%+, below SMA50, thesis broken → cut")
                else:
                    action = "REVIEW"
                    reasons.append("down 8%+, below SMA50 → thesis check needed")

            if pnl_pct <= -8 and above_sma50:
                if action == "HOLD":
                    action = "HOLD (WAIT)"
                reasons.append("down 8%+ but above SMA50 → wait for SMA20 reclaim")

            if not reasons:
                reasons.append("no rule triggered")

            results.append({
                "Symbol": sym,
                "Buy": round(buy, 2),
                "Close": round(close, 2),
                "P&L %": round(pnl_pct, 2),
                "1mo %": round(pnl_1mo, 2) if pnl_1mo is not None else None,
                "RSI": round(rsi, 1),
                "Above SMA50": above_sma50,
                "Action": action,
                "Reason": "; ".join(reasons),
            })
        except Exception as e:
            results.append({
                "Symbol": sym,
                "Action": "ERROR",
                "Reason": str(e),
            })
    return results