import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="Overnight Futures (6 PM → 4 PM)", layout="wide")

st.title("TUZ5 Futures Yield (6 PM → 4 PM Session, 5-Minute Data)")
st.caption(
    "Each trading day is rebased to 0 at its 6 PM open, then tracks through 4 PM next day. "
    "Dashed black line shows average performance. Every 5-minute data point preserved."
)

# -------------------- Helper --------------------
def load_chart_sheet(path: str):
    """Load Chart1 or Chart 1 sheet and clean data."""
    for sn in ["Chart", "Chart 1"]:
        try:
            return pd.read_excel(path, sheet_name=sn).dropna(how="all")
        except Exception:
            continue
    raise ValueError("No sheet named 'Chart1' or 'Chart 1' found.")

# -------------------- Sidebar --------------------
st.sidebar.header("Inputs")
default_path = "TUZ5 - 5M5D.xlsx"
if not os.path.exists(default_path):
    st.error("Missing default file: TUZ5 - 5M5D.xlsx. Upload or place it in this directory.")
    st.stop()

# -------------------- Load & Process --------------------
try:
    df_chart = load_chart_sheet(default_path)
    if "Time/Day" not in df_chart.columns:
        raise ValueError("Expected a 'Time/Day' column in Chart 1 sheet.")

    # numeric columns (all trading days + Avg)
    numeric_cols = [c for c in df_chart.columns if c != "Time/Day" and pd.api.types.is_numeric_dtype(df_chart[c])]
    if not numeric_cols:
        numeric_cols = [c for c in df_chart.columns if c != "Time/Day"]

    # melt to long format
    melt_df = df_chart.melt(id_vars=["Time/Day"], value_vars=numeric_cols,
                            var_name="Date", value_name="Yield")

    # clean up time column (handle AM/PM)
    melt_df["Time/Day"] = melt_df["Time/Day"].astype(str).str.strip()
    melt_df = melt_df[melt_df["Time/Day"].str.match(r"^\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)?$", na=False)]

    # convert to datetime (dummy base date)
    melt_df["t"] = pd.to_datetime("1970-01-01 " + melt_df["Time/Day"], errors="coerce")
    melt_df = melt_df.dropna(subset=["t"])

    # --- Adjust to represent 6 PM → 4 PM session ---
    # times < 6 PM are “after midnight” (so add +1 day)
    melt_df.loc[melt_df["t"].dt.hour < 18, "t"] += pd.Timedelta(days=1)

    # keep 6 PM → 4 PM next day only
    melt_df = melt_df[
        ((melt_df["t"].dt.hour >= 18) | (melt_df["t"].dt.hour < 16))
    ].sort_values("t")

    # shorten date labels for chart
    melt_df["Date"] = (
        melt_df["Date"].astype(str)
        .str.replace("2025-", "", regex=False)
        .str.replace("-2025", "", regex=False)
        .str.replace("00:00:00", "", regex=False)
        .str.strip()
    )

    # --- Normalize each day to start (6 PM) = 0 ---
    def normalize_day(group):
        # find first 6 PM observation
        first_yield = group.loc[group["t"].dt.hour == 18, "Yield"]
        if not first_yield.empty:
            base = first_yield.iloc[0]
        else:
            base = group["Yield"].iloc[0]
        group["Yield"] = group["Yield"] - base
        return group

    melt_df = melt_df.groupby("Date", group_keys=False).apply(normalize_day)

    # Determine start/end from actual dates (ignore Avg)
    date_list = [str(d).strip() for d in melt_df["Date"].unique()]
    non_avg_dates = [d for d in date_list if d.lower() not in ["avg", "average"]]

    if non_avg_dates:
        try:
            # Try parsing — assume September 2025 if missing year
            parsed_dates = []
            for d in non_avg_dates:
                # if looks like "9/18" or "09/18", add year
                if "/" in d and d.count("/") == 1:
                    d_full = f"{d}/2025"
                else:
                    d_full = d
                parsed = pd.to_datetime(d_full, errors="coerce")
                if pd.notna(parsed):
                    parsed_dates.append(parsed)

            if parsed_dates:
                parsed_dates = sorted(parsed_dates)
                start_day = parsed_dates[0].day
                end_day = parsed_dates[-1].day
                title_range = f"Sept {start_day} – {end_day}, 2025"
            else:
                title_range = "Futures Session Range"
        except Exception:
            title_range = "Futures Session Range"
    else:
        title_range = "Futures Session Range"


    st.markdown(f"## TUZ5 Futures Yield: {title_range}")
    st.caption("Each line = daily session (6 PM → 4 PM), rebased to 0 at open. Dashed = average.")

    # separate Avg
    Avg_df = melt_df[melt_df["Date"].str.lower().str.contains("Avg")]
    non_Avg_df = melt_df[~melt_df["Date"].str.lower().str.contains("Avg")]

    # solid lines for each day
    base = (
        alt.Chart(non_Avg_df)
        .mark_line(interpolate="linear", strokeWidth=2)
        .encode(
            x=alt.X("t:T", title="Time (6 PM → 4 PM)", axis=alt.Axis(format="%I:%M %p")),
            y=alt.Y("Yield:Q", title="Δ Yield (from 6 PM Open)"),
            color=alt.Color("Date:N", legend=alt.Legend(title="Date")),
            tooltip=[
                "Date:N",
                alt.Tooltip("t:T", title="Time", format="%I:%M %p"),
                alt.Tooltip("Yield:Q", title="Δ Yield"),
            ],
        )
    )

    # dashed Avg line
    Avg_line = (
        alt.Chart(Avg_df)
        .mark_line(interpolate="linear", strokeDash=[5, 5], color="black", strokeWidth=2)
        .encode(
            x="t:T",
            y="Yield:Q",
            tooltip=["Date:N", alt.Tooltip("t:T", title="Time", format="%I:%M %p"), "Yield:Q"],
        )
    )

    chart = (base + Avg_line).properties(height=500, width="container")
    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "Each day begins at 6 PM = 0 and ends at 4 PM with its total Δ Yield. "
        "All 5-minute data points preserved. Dashed black line shows average session performance."
    )

except Exception as e:
    st.error(f"Couldn't load or plot Chart 1: {e}")
