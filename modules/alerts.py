"""Alert persistence — write actionable signals to data/alerts.json."""
import json
from datetime import datetime
from pathlib import Path

ALERTS_PATH = Path("data/alerts.json")
MAX_KEEP = 500


def _load():
    if not ALERTS_PATH.exists():
        return []
    try:
        return json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(alerts):
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    alerts = alerts[-MAX_KEEP:]
    ALERTS_PATH.write_text(
        json.dumps(alerts, indent=2, default=str),
        encoding="utf-8",
    )


def append_alerts(holdings, candidates, is_weekend_scan):
    """Append actionable rows to data/alerts.json. Returns the new entries."""
    now = datetime.now().isoformat(timespec="seconds")
    new = []

    for h in holdings:
        if h.get("Action") in {"TRIM 1/3", "CUT", "REVIEW"}:
            new.append({
                "ts": now,
                "type": "holding",
                "symbol": h["Symbol"],
                "action": h["Action"],
                "reason": h.get("Reason", ""),
                "pnl_pct": h.get("P&L %"),
                "rsi": h.get("RSI"),
            })

    if is_weekend_scan:
        for c in candidates:
            if c.get("Verdict") == "SWING CANDIDATE":
                new.append({
                    "ts": now,
                    "type": "swing",
                    "symbol": c["Symbol"],
                    "action": "SWING CANDIDATE",
                    "reason": c.get("Signals", ""),
                    "rsi": c.get("RSI"),
                    "close": c.get("Close"),
                })

    if new:
        _save(_load() + new)

    return new