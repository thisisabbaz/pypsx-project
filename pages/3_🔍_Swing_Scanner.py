import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from modules.psx_data import get_stock_history
from modules.indicators import add_indicators

st.set_page_config(page_title="Swing Scanner", page_icon="🔍", layout="wide")
st.title("🔍 Swing Trade Scanner")
st.caption("Filter → rank → inspect each candidate. Trade plans are computed from "
           "recent price action, not recommendations.")


# ---------- Sidebar: scan parameters ----------
with st.sidebar:
    st.header("Scan settings")
    default_watch = "OGDC,PPL,KEL,HBL,MLCF,MUGHAL,LUCK,ENGRO,MCB,UBL,PSO,FCCL"
    watch_input = st.text_area(
        "Watchlist (comma-separated)",
        value=default_watch,
        height=100,
    )
    period = st.selectbox("Lookback", ["3mo", "6mo", "1y", "2y"], index=1)

    st.divider()
    st.subheader("Oversold")
    rsi_thresh = st.slider("RSI threshold", 20, 60, 40)
    use_rsi = st.checkbox("Require RSI below threshold", value=True)

    st.subheader("Trend")
    require_above_sma50 = st.checkbox("Require close > SMA50", value=True)
    near_sma20_band = st.slider("Near SMA20 (band %)", 0.0, 5.0, 2.0)

    st.subheader("Momentum")
    use_macd = st.checkbox("Require MACD bullish cross", value=False)

    st.subheader("Volume")
    min_vol_ratio = st.slider(
        "Min volume / 20d avg",
        0.0, 3.0, 0.0, step=0.1,
        help="Filter to symbols with elevated volume. 0 disables.",
    )


symbols = [s.strip().upper() for s in watch_input.split(",") if s.strip()]

if not symbols:
    st.info("Add symbols to the watchlist to scan.")
    st.stop()

if st.button("Run Scan", type="primary"):

    rows = []
    progress = st.progress(0.0, text="Scanning...")
    errors = []

    for i, sym in enumerate(symbols):
        try:
            df = add_indicators(get_stock_history(sym, period=period))
            if df is None or len(df) < 50:
                errors.append(f"{sym}: not enough data")
                progress.progress((i + 1) / len(symbols))
                continue

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            close = float(latest["CLOSE"])
            sma20 = float(latest["SMA_20"]) if latest["SMA_20"] == latest["SMA_20"] else None
            sma50 = float(latest["SMA_50"]) if latest["SMA_50"] == latest["SMA_50"] else None
            rsi = float(latest["RSI_14"])
            macd_now = float(latest["MACD_Hist"])
            macd_prev = float(prev["MACD_Hist"])
            macd_cross = macd_now > 0 and macd_prev <= 0

            # volume ratio
            vol = df["VOLUME"] if "VOLUME" in df.columns else None
            if vol is not None and len(vol) >= 20:
                avg_vol = float(vol.tail(20).mean())
                vol_ratio = float(vol.iloc[-1]) / avg_vol if avg_vol > 0 else 0.0
            else:
                vol_ratio = None

            # --- Filters ---
            if use_rsi and rsi >= rsi_thresh:
                progress.progress((i + 1) / len(symbols))
                continue
            if require_above_sma50 and (sma50 is None or close <= sma50):
                progress.progress((i + 1) / len(symbols))
                continue
            if use_macd and not macd_cross:
                progress.progress((i + 1) / len(symbols))
                continue
            if min_vol_ratio > 0 and (vol_ratio is None or vol_ratio < min_vol_ratio):
                progress.progress((i + 1) / len(symbols))
                continue

            # --- Signals ---
            signals = []
            if rsi < rsi_thresh:
                signals.append(f"RSI<{rsi_thresh}")
            if sma20 is not None and close <= sma20 * (1 + near_sma20_band / 100):
                signals.append("Near SMA20")
            if macd_cross:
                signals.append("MACD cross↑")
            if vol_ratio is not None and vol_ratio >= 1.5:
                signals.append(f"Vol×{vol_ratio:.1f}")

            if not signals:
                progress.progress((i + 1) / len(symbols))
                continue

            # --- Trade plan ---
            recent_low = float(df["LOW"].tail(20).min())
            recent_high = float(df["HIGH"].tail(20).max())

            entry_low = round(close * 0.995, 2)
            entry_high = round(close * 1.005, 2)
            stop_loss = round(recent_low * 0.99, 2)

            risk = entry_high - stop_loss
            target_1 = round(max(recent_high, entry_high * 1.03), 2)
            target_2 = round(max(target_1 * 1.05, entry_high + 2 * risk), 2)

            reward_t1 = target_1 - entry_high
            reward_t2 = target_2 - entry_high
            rr_t1 = reward_t1 / risk if risk > 0 else 0
            rr_t2 = reward_t2 / risk if risk > 0 else 0

            # Simple strength score
            score = 0
            score += 25 if rsi < rsi_thresh else 0
            score += 20 if sma50 is not None and close > sma50 else 0
            score += 15 if macd_cross else 0
            score += 15 if (vol_ratio or 0) >= 1.5 else 0
            score += 25 if rr_t1 >= 2 else (15 if rr_t1 >= 1.5 else 0)
            score = min(score, 100)

            rows.append({
                "Symbol": sym,
                "Close": round(close, 2),
                "RSI": round(rsi, 1),
                "SMA20": round(sma20, 2) if sma20 is not None else None,
                "SMA50": round(sma50, 2) if sma50 is not None else None,
                "Vol×": round(vol_ratio, 2) if vol_ratio is not None else None,
                "Entry Low": entry_low,
                "Entry High": entry_high,
                "Stop": stop_loss,
                "T1": target_1,
                "T2": target_2,
                "R:R T1": round(rr_t1, 2),
                "R:R T2": round(rr_t2, 2),
                "Score": score,
                "Signals": ", ".join(signals),
            })
        except Exception as e:
            errors.append(f"{sym}: {e}")
        progress.progress((i + 1) / len(symbols), text=f"Scanned {sym}")

    progress.empty()
    st.session_state["scan_rows"] = rows
    st.session_state["scan_errors"] = errors


# ---------- Results ----------
rows = st.session_state.get("scan_rows")
errors = st.session_state.get("scan_errors", [])

if rows is None:
    st.info("Configure settings in the sidebar and click **Run Scan**.")
    if errors:
        with st.expander("Symbols skipped"):
            for e in errors:
                st.write(e)
    st.stop()

if not rows:
    st.warning("No candidates matched the current filters.")
    with st.expander("Try loosening"):
        st.markdown(
            "- Raise **RSI threshold** (e.g. 45)\n"
            "- Uncheck **Require close > SMA50**\n"
            "- Reduce **Min volume / 20d avg**\n"
            "- Widen the **Near SMA20 band**"
        )
    if errors:
        with st.expander("Symbols skipped"):
            for e in errors:
                st.write(e)
    st.stop()

df_out = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)

# Summary metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Candidates", len(df_out))
c2.metric("High conviction (Score≥70)", int((df_out["Score"] >= 70).sum()))
c3.metric("R:R ≥ 2 to T1", int((df_out["R:R T1"] >= 2).sum()))
c4.metric("Avg RSI", f"{df_out['RSI'].mean():.1f}")

st.divider()

# ---------- Table view ----------
st.subheader("Ranked Candidates")
display_cols = [
    "Symbol", "Score", "Close", "RSI",
    "Entry Low", "Entry High", "Stop", "T1", "T2",
    "R:R T1", "R:R T2", "Vol×", "SMA20", "SMA50", "Signals",
]
display_cols = [c for c in display_cols if c in df_out.columns]

st.dataframe(
    df_out[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Score": st.column_config.ProgressColumn(
            "Score", min_value=0, max_value=100, format="%d"
        ),
        "R:R T1": st.column_config.NumberColumn("R:R T1", format="%.2f"),
        "R:R T2": st.column_config.NumberColumn("R:R T2", format="%.2f"),
    },
)

csv = df_out.to_csv(index=False).encode("utf-8")
st.download_button("Download scan (CSV)", csv, "swing_scan.csv", "text/csv")

st.divider()

# ---------- Detail cards ----------
st.subheader("Candidate detail")

for _, row in df_out.iterrows():
    badge = "🟢" if row["Score"] >= 70 else ("🟡" if row["Score"] >= 50 else "⚪")
    header = f"{badge} {row['Symbol']} — Score {row['Score']} · Entry {row['Entry Low']}–{row['Entry High']}"

    with st.expander(header, expanded=(row["Score"] >= 70)):
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Stop", f"{row['Stop']}")
        m2.metric("Target 1", f"{row['T1']}", f"{row['R:R T1']}R")
        m3.metric("Target 2", f"{row['T2']}", f"{row['R:R T2']}R")
        m4.metric("RSI", f"{row['RSI']}")
        m5.metric("Volume ×", f"{row['Vol×']}" if row["Vol×"] is not None else "—")

        try:
            df_chart = add_indicators(get_stock_history(row["Symbol"], period=period))
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_chart.index,
                open=df_chart["OPEN"], high=df_chart["HIGH"],
                low=df_chart["LOW"], close=df_chart["CLOSE"],
                name=row["Symbol"],
            ))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["SMA_20"],
                                     name="SMA20", line=dict(width=1)))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["SMA_50"],
                                     name="SMA50", line=dict(width=1)))

            # Horizontal levels
            for label, price, color in [
                ("Entry", row["Entry High"], "#3498db"),
                ("Stop", row["Stop"], "#e74c3c"),
                ("T1", row["T1"], "#27ae60"),
                ("T2", row["T2"], "#16a085"),
            ]:
                fig.add_hline(
                    y=price, line_dash="dot", line_color=color,
                    annotation_text=f"{label} {price}",
                    annotation_position="right",
                )

            fig.update_layout(
                height=340,
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{row['Symbol']}")
        except Exception as e:
            st.warning(f"Could not draw chart: {e}")

        st.caption(f"Signals: {row['Signals']}")

if errors:
    with st.expander(f"Symbols skipped ({len(errors)})"):
        for e in errors:
            st.write(e)