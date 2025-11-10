import streamlit as st
import pandas as pd
import altair as alt
import os
import re

st.set_page_config(page_title="US Treasury Futures Yield Model", layout="wide")

st.title("US Treasury Futures Yield Model (6 PM → 4 PM Sessions)")
st.caption(
    "Each trading day is rebased to 0 at its 6 PM open, then tracks through 4 PM next day. "
    "Dashed black line shows average performance. Every 5-minute data point preserved."
)

# ---------- Helper: Load CSV safely ----------
def load_csv(path):
    try:
        df = pd.read_csv(path, encoding="utf-8", skip_blank_lines=True)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin1", skip_blank_lines=True)
    # Strip quotes from all string cells
    df = df.applymap(lambda x: str(x).strip('"').strip("'") if isinstance(x, str) else x)
    return df

# ---------- Helper: Convert futures prices like 104-08¼ ----------
def convert_price(x):
    if isinstance(x, str):
        x = x.strip().replace("–", "-").replace("+", "4")  # '+' means extra 4/32
        match = re.match(r"(\d+)-(\d+)", x)
        if match:
            try:
                whole = float(match.group(1))
                frac = int(match.group(2))
                price = whole + (frac / 32.0) / 100.0
                return price
            except Exception:
                return None
    try:
        return float(x)
    except Exception:
        return None

# ---------- Process one contract ----------
def process_contract(df: pd.DataFrame, contract: str):
    # Identify columns
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    price_col = next((c for c in df.columns if "lst" in c.lower()), None)
    if not date_col or not price_col:
        raise ValueError(f"{contract}: missing required columns (found {df.columns.tolist()})")

    # Clean and parse datetime
    df[date_col] = df[date_col].astype(str).str.replace('"', '').str.strip()
    df["t"] = pd.to_datetime(df[date_col], errors="coerce", infer_datetime_format=True)
    df = df.dropna(subset=["t"]).sort_values("t")

    # Convert price
    df["Price"] = df[price_col].apply(convert_price)
    df = df.dropna(subset=["Price"])

    # Define session date (anything before 6 PM belongs to previous day)
    df["SessionDate"] = df["t"].dt.date
    df.loc[df["t"].dt.hour < 18, "SessionDate"] = df["t"].dt.date - pd.Timedelta(days=1)

    # Keep only 6 PM → 4 PM window
    df = df[(df["t"].dt.hour >= 18) | (df["t"].dt.hour < 16)]

    # Compute minutes since 6 PM open
    session_start = pd.to_datetime(df["SessionDate"].astype(str) + " 18:00")
    df["MinutesSinceOpen"] = (df["t"] - session_start).dt.total_seconds() / 60
    df.loc[df["MinutesSinceOpen"] < 0, "MinutesSinceOpen"] += 24 * 60  # after midnight shift

    # Normalize yield
    def normalize_session(g):
        base = g.loc[g["MinutesSinceOpen"] == 0, "Price"]
        base_val = base.iloc[0] if not base.empty else g["Price"].iloc[0]
        g["Yield"] = g["Price"] - base_val
        return g

    df = df.groupby("SessionDate", group_keys=False).apply(normalize_session)

    # Average line
    avg_df = (
        df.groupby("MinutesSinceOpen", as_index=False)["Yield"]
        .mean()
        .sort_values("MinutesSinceOpen")
    )

    df["DayStr"] = pd.to_datetime(df["SessionDate"]).dt.strftime("%b %d")
    return df, avg_df

# ---------- Chart ----------
def make_chart(df, avg_df, title):
    base = (
        alt.Chart(df)
        .mark_line(interpolate="linear", strokeWidth=1.5)
        .encode(
            x=alt.X("MinutesSinceOpen:Q", title="Minutes Since 6 PM (6 PM → 4 PM)"),
            y=alt.Y("Yield:Q", title="Δ Yield (from 6 PM Open)"),
            color=alt.Color("DayStr:N", legend=alt.Legend(title="Date")),
            tooltip=[
                "DayStr:N",
                alt.Tooltip("MinutesSinceOpen:Q", title="Minutes Since 6 PM"),
                alt.Tooltip("Yield:Q", title="Δ Yield"),
            ],
        )
    )

    avg = (
        alt.Chart(avg_df)
        .mark_line(strokeDash=[5, 5], color="black", strokeWidth=2)
        .encode(x="MinutesSinceOpen:Q", y="Yield:Q")
    )

    return (base + avg).properties(title=title, height=500, width="container")

# ---------- App Layout ----------
tabs = st.tabs(["2Y – TUZ5", "5Y – FVZ5", "10Y – TYZ5"])
contracts = {
    "TUZ5": ("tuz5.csv", tabs[0]),
    "FVZ5": ("fvz5.csv", tabs[1]),
    "TYZ5": ("tyz5.csv", tabs[2]),
}

for name, (filename, tab) in contracts.items():
    with tab:
        if not os.path.exists(filename):
            st.warning(f"Missing `{filename}` in the folder.")
            continue
        try:
            raw = load_csv(filename)
            df_proc, avg_proc = process_contract(raw, name)

            start_day = pd.to_datetime(df_proc["SessionDate"]).min()
            end_day = pd.to_datetime(df_proc["SessionDate"]).max()
            title_range = f"{start_day:%b %d} – {end_day:%b %d, %Y}"

            st.markdown(f"### {name} Futures Yield: {title_range}")
            st.caption("Each line = daily session (6 PM → 4 PM), rebased to 0 at open. Dashed = average.")
            st.altair_chart(make_chart(df_proc, avg_proc, f"{name} Session (6 PM → 4 PM)"), use_container_width=True)

            st.caption(
                "Each day begins at 6 PM = 0 and ends at 4 PM with its total Δ Yield. "
                "All 5-minute data points preserved. Dashed black line shows average session performance."
            )

        except Exception as e:
            st.error(f"Couldn't process {name}: {e}")
