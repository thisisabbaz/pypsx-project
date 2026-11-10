import streamlit as st
import plotly.graph_objects as go

from modules.psx_data import get_stock_history
from modules.indicators import add_indicators

st.set_page_config(page_title="PSX Watchlist", page_icon="📊", layout="wide")
st.title("📊 PSX Watchlist")

col_a, col_b = st.columns([2, 1])
with col_a:
    symbol = st.text_input("Symbol", value="OGDC").upper().strip()
with col_b:
    period = st.selectbox("Period", ["3mo", "6mo", "1y", "2y"], index=2)

if not symbol:
    st.info("Enter a symbol to load.")
    st.stop()

try:
    df = get_stock_history(symbol, period=period)
    df = add_indicators(df)
except Exception as e:
    st.error(f"Failed to fetch {symbol}: {e}")
    st.stop()

if df is None or df.empty:
    st.warning("No data returned for this symbol/period.")
    st.stop()

latest = df.iloc[-1]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Close", f"{float(latest['CLOSE']):.2f}")
m2.metric("RSI(14)", f"{float(latest['RSI_14']):.1f}")
m3.metric("SMA20",
          f"{float(latest['SMA_20']):.2f}"
          if latest['SMA_20'] == latest['SMA_20'] else "—")
m4.metric("SMA50",
          f"{float(latest['SMA_50']):.2f}"
          if latest['SMA_50'] == latest['SMA_50'] else "—")

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["OPEN"], high=df["HIGH"],
    low=df["LOW"], close=df["CLOSE"],
    name=symbol,
))
fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], name="SMA20", line=dict(width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], name="SMA50", line=dict(width=1)))
fig.update_layout(height=520, xaxis_rangeslider_visible=False,
                  margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig, use_container_width=True)

with st.expander("Raw data (last 50 rows)"):
    st.dataframe(df.tail(50), use_container_width=True)