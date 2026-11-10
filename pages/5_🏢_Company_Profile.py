import streamlit as st
import pandas as pd

from modules.fundamentals import clean_fundamentals, grouped_display
from modules.fy_detect import get_fy_end
from modules.dividends import enrich_dividends

st.set_page_config(page_title="Company Profile", page_icon="🏢", layout="wide")
st.title("🏢 Company Profile")

col_a, col_b = st.columns([3, 1])
with col_a:
    symbol = st.text_input("Enter PSX Symbol", value="OGDC").upper().strip()
with col_b:
    st.write("")
    st.write("")
    if st.button("Reload data"):
        st.cache_data.clear()
        st.rerun()

if not symbol:
    st.info("Enter a symbol to load its profile.")
    st.stop()


# ---------- Cached fetchers ----------
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fundamentals(sym):
    import pypsx_toolkit as pt
    try:
        return pt.get_company_fundamentals(sym), None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_dividends(sym):
    import pypsx_toolkit as pt
    try:
        return pt.get_dividend_history(sym), None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_announcements(sym):
    import pypsx_toolkit as pt
    try:
        return pt.get_announcements(sym), None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_history(sym, period):
    from modules.psx_data import get_stock_history
    try:
        return get_stock_history(sym, period=period), None
    except Exception as e:
        return None, str(e)


# ---------- Price snapshot ----------
with st.spinner(f"Loading {symbol}..."):
    hist_5y, hist_err = fetch_history(symbol, "5y")

if not hist_err and hist_5y is not None and not hist_5y.empty:
    last = hist_5y.iloc[-1]
    first = hist_5y.iloc[0]
    chg = (float(last["CLOSE"]) / float(first["CLOSE"]) - 1) * 100
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Close", f"{float(last['CLOSE']):.2f}")
    c2.metric("Period Start", f"{float(first['CLOSE']):.2f}")
    c3.metric("5y Change", f"{chg:+.1f}%")
    c4.metric("Rows", len(hist_5y))
    st.divider()


tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Fundamentals", "💰 Dividend History", "📢 Announcements", "📈 Price History"]
)


# ---------- Tab 1: Fundamentals ----------
with tab1:
    with st.spinner("Loading fundamentals..."):
        raw_f, f_err = fetch_fundamentals(symbol)
        raw_a_for_fy, _ = fetch_announcements(symbol)

    if f_err:
        st.warning(f"Could not load fundamentals: {f_err}")
    elif raw_f is None or raw_f.empty:
        st.info("No fundamental data found.")
    else:
        # Auto-detect and cache fiscal-year-end from announcements
        fy_end = get_fy_end(symbol, ann_df=raw_a_for_fy)
        st.caption(
            f"Fiscal year end (auto-detected): **{fy_end[1]:02d}/{fy_end[0]:02d}**  ·  "
            f"value columns are newest-first"
        )

        cleaned = clean_fundamentals(raw_f, symbol)
        groups = grouped_display(cleaned, symbol, fy_end=fy_end)

        if not groups:
            st.info("No structured fundamentals returned.")
        else:
            for cat, sub in groups.items():
                with st.expander(
                    cat,
                    expanded=(cat.lower() in ("profile", "ratios")),
                ):
                    st.dataframe(sub, use_container_width=True, hide_index=True)


# ---------- Tab 2: Dividends ----------
with tab2:
    with st.spinner("Loading dividend history..."):
        raw_d, d_err = fetch_dividends(symbol)

    if d_err:
        st.warning(f"Could not load dividends: {d_err}")
    elif raw_d is None or raw_d.empty:
        st.info("No dividend history found.")
    else:
        enriched = enrich_dividends(raw_d)

        try:
            cash_col = next(
                (c for c in enriched.columns if "CASH" in c.upper()), None
            )
            if cash_col:
                cash = (
                    enriched[cash_col]
                    .astype(str)
                    .str.replace(r"[^\d.]", "", regex=True)
                    .replace("", pd.NA)
                    .astype(float)
                )
                c1, c2, c3 = st.columns(3)
                c1.metric("Total payouts", len(enriched))
                c2.metric("Sum cash per share (PKR)", f"{cash.sum():.2f}")
                c3.metric(
                    "Latest payout (PKR)",
                    f"{cash.iloc[0]:.2f}" if len(cash) else "—",
                )
        except Exception:
            pass

        preferred = [
            "FINANCIAL RESULT",
            "EX-DIVIDEND DATE", "EX-DIVIDEND",
            "CASH AMOUNT",
            "RECORD DATE",
            "PAY DATE",
            "BOOK CLOSURE",
            "DETAILS",
        ]
        cols = [c for c in preferred if c in enriched.columns]
        cols += [c for c in enriched.columns if c not in cols]
        st.dataframe(enriched[cols], use_container_width=True, hide_index=True, height=560)
        csv = enriched.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, f"{symbol}_dividends.csv", "text/csv")


# ---------- Tab 3: Announcements ----------
with tab3:
    with st.spinner("Loading announcements..."):
        raw_a, a_err = fetch_announcements(symbol)

    if a_err:
        st.warning(f"Could not load announcements: {a_err}")
    elif raw_a is None or raw_a.empty:
        st.info("No announcements found.")
    else:
        ann = raw_a.copy()
        ann.columns = [str(c).upper().strip() for c in ann.columns]
        ann = ann.drop(columns=[c for c in ann.columns if "IMAGE" in c], errors="ignore")

        pdf_col = next((c for c in ann.columns if "PDF" in c), None)
        title_col = next((c for c in ann.columns if "TITLE" in c), None)
        section_col = next((c for c in ann.columns if "SECTION" in c), None)

        st.caption(f"{len(ann)} announcements")
        for _, row in ann.iterrows():
            with st.container(border=True):
                left, right = st.columns([5, 1])
                with left:
                    title = row.get(title_col, "") if title_col else "—"
                    section = row.get(section_col, "") if section_col else ""
                    st.markdown(f"**{title}**")
                    if section:
                        st.caption(section)
                with right:
                    if pdf_col and isinstance(row.get(pdf_col), str):
                        st.link_button(
                            "📄 Open PDF",
                            row[pdf_col],
                            use_container_width=True,
                        )


# ---------- Tab 4: Price History ----------
with tab4:
    period = st.selectbox(
        "Lookback",
        ["1y", "2y", "3y", "5y", "10y", "max"],
        index=3,
        key="profile_period",
    )
    hist, err = fetch_history(symbol, period)
    if err:
        st.error(err)
    elif hist is None or hist.empty:
        st.info("No history returned.")
    else:
        st.caption(f"{len(hist)} rows")
        st.dataframe(hist.tail(500), use_container_width=True, height=520)
        csv = hist.to_csv().encode("utf-8")
        st.download_button("Download CSV", csv, f"{symbol}_{period}.csv", "text/csv")