# app.py - Diagnostics-enabled version
import streamlit as st
import pandas as pd
import time
import traceback

st.set_page_config(page_title="NSE500 Breakout Scanner (Diagnostics)", layout="wide")

# Safe imports
try:
    from core.signals import (
        load_latest_signals,
        compute_and_store_signals,
        generate_signals_sample,
    )
    from core.signals import SAMPLE_SYMBOLS  # sample list
    from core.signals import fetch_ohlcv, fetch_ohlcv_av, fetch_ohlcv_nse, fetch_ohlcv_yf
    from alerts.telegram_alerts import send_test_alert
except Exception as e:
    st.title("🚨 Import Error — App couldn't start")
    st.error("A required module failed to load. Full exception:")
    st.exception(e)
    st.stop()

st.title("📊 NSE-500 Breakout Scanner (Diagnostics)")

col1, col2 = st.columns([3, 1])

with col2:
    st.markdown("### ⚙️ Admin")
    if st.button("Generate sample signals (debug)"):
        generate_signals_sample()
        st.success("Sample signals generated. Refresh the page to view them.")
    if st.button("Force compute signals now"):
        try:
            compute_and_store_signals()
            st.success("✅ Signals computed. Refresh the page.")
        except Exception as e:
            st.error("Computation failed:")
            st.exception(e)
    if st.button("Send test Telegram Alert"):
        resp = send_test_alert("This is a test alert from your NSE500 Scanner.")
        st.write(resp)

    st.markdown("---")
    st.markdown("### 🔎 Diagnostics")
    st.markdown("Use **Run Diagnostics** to see which data source returns rows for each symbol.")
    if st.button("Run Diagnostics"):
        st.info("Running diagnostics — this may take up to 30 seconds (one request per sample symbol)...")
        diag_results = []
        for sym in SAMPLE_SYMBOLS:
            row = {"symbol": sym, "alpha_rows": None, "nse_rows": None, "yf_rows": None, "alpha_err": None, "nse_err": None, "yf_err": None}
            # Alpha Vantage (if available)
            try:
                av = None
                try:
                    av = fetch_ohlcv_av(sym, days=365)
                except Exception as e_av:
                    row["alpha_err"] = str(e_av)
                if av is not None:
                    row["alpha_rows"] = len(av)
                # NSE
                nse_df = None
                try:
                    nse_df = fetch_ohlcv_nse(sym, days=365)
                except Exception as e_nse:
                    row["nse_err"] = str(e_nse)
                if nse_df is not None:
                    row["nse_rows"] = len(nse_df)
                # Yahoo
                yf_df = None
                try:
                    yf_df = fetch_ohlcv_yf(sym, days=365)
                except Exception as e_yf:
                    row["yf_err"] = str(e_yf)
                if yf_df is not None:
                    row["yf_rows"] = len(yf_df)
            except Exception as e_any:
                row["diag_error"] = traceback.format_exc()
            diag_results.append(row)
        st.success("Diagnostics complete — see table below.")
        st.dataframe(pd.DataFrame(diag_results))
        st.markdown("**Notes:**")
        st.markdown("- `alpha_rows` shows number of daily rows AlphaVantage returned (if key set).")
        st.markdown("- `nse_rows` shows rows from NSE public endpoint.")
        st.markdown("- `yf_rows` shows rows from yfinance fallback.")
        st.markdown("- If all three columns are `None`, the fetcher failed for that symbol — copy the errors and paste them in chat for help.")
        st.stop()

with col1:
    st.markdown("### 📈 Latest Signals")
    try:
        signals = load_latest_signals()
    except Exception as e:
        st.error("Couldn't load signals.json:")
        st.exception(e)
        signals = None

    if not signals:
        st.info(
            "No signals yet. Click **Force compute signals now** to fetch live data "
            "or **Generate sample signals** for demo output. Use Diagnostics to test sources."
        )
    else:
        df = pd.DataFrame(signals)
        display_cols = [
            "symbol",
            "timeframe",
            "signal_time",
            "action",
            "buy_price",
            "stoploss",
            "target",
            "holding_duration",
            "holding_reason",
            "confidence",
            "reasons",
        ]
        df = df[[c for c in display_cols if c in df.columns]]
        st.dataframe(df, use_container_width=True)

st.markdown("---")
st.caption("Diagnostics tool will show which data source returned rows. If AlphaVantage is preferred, set ALPHA_VANTAGE_KEY in Streamlit Secrets.")
st.caption("Last updated: " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
