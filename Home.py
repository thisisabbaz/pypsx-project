import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PSX Portfolio", page_icon="📈", layout="wide")


def load_json(path: Path):
    """Return (data, error). Never raises."""
    if not path.exists():
        return None, f"{path.name} not found"
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None, f"{path.name} is empty"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"{path.name} invalid JSON: {e}"


def render_movers(section):
    if section is None:
        st.caption("—")
        return
    if isinstance(section, list):
        st.dataframe(pd.DataFrame(section), use_container_width=True, hide_index=True)
        return
    if isinstance(section, dict):
        rows = []
        for k, v in section.items():
            if isinstance(v, dict):
                rows.append({"Symbol": k, **v})
            else:
                rows.append({"Symbol": k, "Value": v})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            return
    st.write(section)


@st.cache_data(ttl=300)
def load_movers():
    try:
        from modules.psx_data import get_top_performers
        return get_top_performers(), None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=3600)
def load_navs():
    try:
        from modules.mutual_funds import fetch_mufap_navs
        return fetch_mufap_navs(), None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=300)
def load_portfolio_summary(portfolio):
    """Fetch quotes and compute portfolio summary."""
    if not portfolio:
        return None
    from modules.psx_data import get_batch_quotes
    from modules.portfolio import compute_portfolio
    
    symbols = list(portfolio.keys())
    try:
        quotes = get_batch_quotes(symbols)
        df = compute_portfolio(portfolio, quotes)
        
        total_cost = df['Cost'].sum()
        total_value = df['Market Value'].sum()
        total_pnl = df['P&L'].sum()
        total_pnl_pct = (total_value / total_cost - 1) * 100 if total_cost > 0 else 0
        
        return {
            'df': df,
            'total_cost': total_cost,
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
        }
    except Exception as e:
        return {'error': str(e)}


st.title("📈 PSX Investment Dashboard")

with st.sidebar:
    st.header("My Holdings")
    portfolio, err = load_json(Path("data/portfolio.json"))
    if err:
        st.warning(err)
    elif portfolio:
        from modules.portfolio import compute_portfolio, fetch_quotes
        with st.spinner("Fetching prices..."):
            quotes = fetch_quotes(list(portfolio.keys()))
            df_p = compute_portfolio(portfolio, quotes)

        df_valid = df_p.dropna(subset=["Market Value"])
        if not df_valid.empty:
            total_cost = df_valid["Cost"].sum()
            total_value = df_valid["Market Value"].sum()
            total_pnl = df_valid["P&L"].sum()
            total_pnl_pct = (total_value / total_cost - 1) * 100 if total_cost else 0
            st.metric("Total Value", f"PKR {total_value:,.0f}")
            st.metric("Total Cost", f"PKR {total_cost:,.0f}")
            st.metric("Total P&L", f"PKR {total_pnl:,.0f}", f"{total_pnl_pct:+.2f}%")
            st.divider()
            st.dataframe(
                df_valid[["Symbol", "Shares", "Buy", "Price", "Market Value", "P&L %"]],
                use_container_width=True, hide_index=True,
            )

        missing = df_p[df_p["Market Value"].isna()]["Symbol"].tolist()
        if missing:
            st.caption(f"⚠️ No price for: {', '.join(missing)}")

    st.divider()
    if st.button("Refresh All Data"):
        st.cache_data.clear()
        st.rerun()
        
col1, col2 = st.columns(2)

with col1:
    st.subheader("PSX Today's Movers")
    movers, err = load_movers()
    if err:
        st.error(err)
    elif movers:
        for key in ("top_gainers", "top_decliners", "top_actives"):
            section = movers.get(key) if isinstance(movers, dict) else None
            st.markdown(f"**{key.replace('_', ' ').title()}**")
            render_movers(section)
            st.divider()
    else:
        st.info("No movers returned.")

with col2:
    st.subheader("Fund NAV Snapshot")
    navs, err = load_navs()
    if err:
        st.info("No local MUFAP file yet. Go to **Mutual Funds** page to upload one.")
    elif navs is None or navs.empty:
        st.info("Excel loaded but empty.")
    else:
        show = [c for c in ["AMC", "Fund", "Category", "NAV", "Validity Date"]
                if c in navs.columns]
        st.caption(f"{len(navs)} funds")
        st.dataframe(navs[show] if show else navs,
                     use_container_width=True, height=520, hide_index=True)