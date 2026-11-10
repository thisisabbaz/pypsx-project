import streamlit as st

from modules.mutual_funds import (
    LOCAL_XLSX,
    load_mufap_excel,
    save_uploaded_mufap,
)

st.set_page_config(page_title="Mutual Funds", page_icon="💰", layout="wide")
st.title("💰 Mutual Funds — MUFAP NAVs")

st.markdown(
    "**How to update:** Download the daily Excel from "
    "[mufap.com.pk](https://www.mufap.com.pk/Industry/IndustryStatDaily?tab=3) "
    "(button: *Export to Excel*), then upload it below."
)

uploaded = st.file_uploader(
    "Upload MUFAP 'Nav And Sales Load' Excel (.xlsx)",
    type=["xlsx", "xls"],
)

if uploaded is not None:
    save_uploaded_mufap(uploaded.getvalue())
    st.success(f"Saved to `{LOCAL_XLSX}`")
    st.cache_data.clear()

if not LOCAL_XLSX.exists():
    st.info(
        f"No local MUFAP file yet at `{LOCAL_XLSX}`. "
        "Upload one above to get started."
    )
    st.stop()

try:
    df = load_mufap_excel(LOCAL_XLSX)
except Exception as e:
    st.error(f"Failed to parse Excel: {e}")
    st.stop()

st.caption(f"Loaded {len(df)} rows from `{LOCAL_XLSX}`")

c1, c2, c3 = st.columns(3)

sector = c1.selectbox(
    "Sector",
    ["All"] + sorted(df["Sector"].dropna().unique().tolist())
    if "Sector" in df.columns else ["All"],
)
amc = c2.selectbox(
    "AMC",
    ["All"] + sorted(df["AMC"].dropna().unique().tolist())
    if "AMC" in df.columns else ["All"],
)
cat = c3.selectbox(
    "Category",
    ["All"] + sorted(df["Category"].dropna().unique().tolist())
    if "Category" in df.columns else ["All"],
)

search = st.text_input("Search fund name").strip().lower()

view = df.copy()
if sector != "All":
    view = view[view["Sector"] == sector]
if amc != "All":
    view = view[view["AMC"] == amc]
if cat != "All":
    view = view[view["Category"] == cat]
if search and "Fund" in view.columns:
    view = view[view["Fund"].str.lower().str.contains(search, na=False)]

show_cols = [c for c in
             ["AMC", "Fund", "Category", "NAV", "Offer", "Repurchase",
              "Validity Date", "Front-end", "Back-end"]
             if c in view.columns]

st.dataframe(view[show_cols] if show_cols else view,
             use_container_width=True, height=620, hide_index=True)

csv = view.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered CSV", csv, "mufap_filtered.csv", "text/csv")