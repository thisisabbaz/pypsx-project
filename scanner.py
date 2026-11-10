"""PSX nightly scanner.
Runs swing + holdings scans. Writes actionable signals to data/alerts.json.
No email, no Windows notifications. View alerts from the Streamlit Alerts page."""
import contextlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 on stdout so stray Unicode never crashes the run.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from modules.alerts import append_alerts
from modules.signals import evaluate_holdings, scan_swing

BASE = Path(__file__).parent
CFG_PATH = BASE / "data" / "alerts_config.json"
PORT_PATH = BASE / "data" / "portfolio.json"
LOG_PATH = BASE / "data" / "scanner.log"


def log(msg):
    """ASCII-safe logging. Log file is UTF-8."""
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        print(line)
    except Exception:
        # Extremely defensive: fall back to ASCII
        print(line.encode("ascii", "replace").decode("ascii"))
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def is_actionable(holdings, candidates, is_weekend_scan):
    for h in holdings:
        if h.get("Action") in {"TRIM 1/3", "CUT", "REVIEW"}:
            return True
    if is_weekend_scan:
        for c in candidates:
            if c.get("Verdict") == "SWING CANDIDATE":
                return True
    return False


def main():
    cfg = load_json(CFG_PATH)
    portfolio = load_json(PORT_PATH)
    watchlist = cfg.get("watchlist", [])

    is_weekend_scan = datetime.now().weekday() >= 4

    log("=== Scan start === weekend_scan={} watchlist={} holdings={}".format(
        is_weekend_scan, len(watchlist), len(portfolio)))

    # Suppress pypsx_toolkit stdout noise ("Downloading symbols...") during scans
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        holdings = evaluate_holdings(portfolio)
        candidates = scan_swing(
            watchlist,
            rsi_thresh=cfg.get("rsi_threshold", 35),
            sma_band=cfg.get("sma_band", 2.0),
            period=cfg.get("lookback", "6mo"),
        )

    log("Holdings evaluated: {} | Candidates: {}".format(len(holdings), len(candidates)))

    if not is_actionable(holdings, candidates, is_weekend_scan):
        log("Nothing actionable. No alerts recorded.")
        return

    new = append_alerts(holdings, candidates, is_weekend_scan)
    log("Recorded {} alert(s) -> data/alerts.json".format(len(new)))


if __name__ == "__main__":
    main()