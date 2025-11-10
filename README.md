US Treasury Futures Yield Model (6 PM → 4 PM Sessions)

This Streamlit web application visualizes intraday yield movements for U.S. Treasury futures contracts — 2-Year (TUZ5), 5-Year (FVZ5), and 10-Year (TYZ5) — rebased to their 6 PM session open and tracked through 4 PM the following day.

Each day’s trading session is plotted as a separate line, with a dashed black line representing the average session performance.
The model preserves every 5-minute data point for accurate visualization of intraday price trends.

🚀 Features

Handles multiple contract types (2Y, 5Y, 10Y) with separate tabs

Automatically cleans and parses futures price data (e.g., 104-08¼, 109-05+)

Converts raw CME futures prices into decimal yield changes

Normalizes each session (6 PM open = 0) for consistent cross-day comparison

Plots high-resolution 5-minute yield deltas with Altair interactive charts

Displays average performance (dashed black line) for each futures contract

🧠 How It Works

Each CSV file (tuz5.csv, fvz5.csv, tyz5.csv) contains intraday futures data with timestamps and last-trade prices.

The app converts CME-style prices (e.g., 109-05+ = 109 + 5.125 / 32) into decimal form.

Data is grouped into sessions, where:

Each session starts at 6 PM (previous evening)

Each session ends at 4 PM (next day)

For each session, the yield is rebased so the 6 PM value = 0, showing relative yield movement throughout the session.

The average session line (black dashed) is computed across all available days.