import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Alerts", page_icon="🔔", layout="wide")
st.title("🔔 Alerts")

ALERTS_PATH = Path("data/alerts.json")
SEEN_PATH = Path("data/alerts_seen.json")


def load_alerts():
    if not ALERTS_PATH.exists():
        return []
    try:
        return json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def load_seen():
    if not SEEN_PATH.exists():
        return []
    try:
        return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_seen(seen):
    SEEN_PATH.write_text(json.dumps(seen, indent=2), encoding="utf-8")


top_left, top_right = st.columns([1, 4])
with top_left:
    if st.button("Run scanner now"):
        with st.spinner("Scanning..."):
            result = subprocess.run(
                [sys.executable, "scanner.py"],
                capture_output=True, text=True, cwd=Path.cwd(),
            )
        if result.returncode == 0:
            st.success("Scan complete.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"Scanner failed (exit {result.returncode})")
            st.code(result.stderr or result.stdout or "no output")


alerts = load_alerts()
seen = set(load_seen())

if not alerts:
    st.info(
        "No alerts yet. The scanner writes to `data/alerts.json` only when "
        "rules fire. Click **Run scanner now**, or wait for the scheduled task."
    )
    st.stop()

df = pd.DataFrame(alerts)
df["_ts"] = pd.to_datetime(df["ts"], errors="coerce")
df = df.sort_values("_ts", ascending=False)
df["new"] = df["ts"].apply(lambda t: t not in seen)

c1, c2, c3 = st.columns(3)
c1.metric("Total alerts", len(df))
c2.metric("Unread", int(df["new"].sum()))
c3.metric("Last alert",
          df["_ts"].iloc[0].strftime("%d %b %H:%M") if len(df) else "—")

with st.expander("Filters", expanded=False):
    show_only_new = st.checkbox("Only unread", value=True)
    types = st.multiselect(
        "Type",
        sorted(df["type"].dropna().unique().tolist()),
        default=sorted(df["type"].dropna().unique().tolist()),
    )
    actions = st.multiselect(
        "Action",
        sorted(df["action"].dropna().unique().tolist()),
        default=sorted(df["action"].dropna().unique().tolist()),
    )

view = df[df["type"].isin(types) & df["action"].isin(actions)]
if show_only_new:
    view = view[view["new"]]

display_cols = [c for c in
                ["ts", "symbol", "type", "action", "rsi", "pnl_pct", "close", "reason", "new"]
                if c in view.columns]

st.dataframe(view[display_cols], use_container_width=True,
             hide_index=True, height=520)

col_a, col_b = st.columns(2)
with col_a:
    if st.button("Mark all as read"):
        new_seen = sorted(set(seen) | set(df["ts"].tolist()))
        save_seen(new_seen)
        st.success("Marked all as read.")
        st.rerun()
with col_b:
    if st.button("Clear alert history"):
        ALERTS_PATH.write_text("[]", encoding="utf-8")
        SEEN_PATH.write_text("[]", encoding="utf-8")
        st.success("Cleared.")
        st.rerun()

csv = view.to_csv(index=False).encode("utf-8")
st.download_button("Download visible alerts (CSV)", csv,
                   "psx_alerts.csv", "text/csv")