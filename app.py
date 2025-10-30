# app.py
import streamlit as st
st.set_page_config(page_title="NSE500 Breakout Scanner", layout="wide")

import time
import pandas as pd

# safe imports with clear error shown on screen
try:
    from core.signals import load_latest_signals, compute_and_store_signals, generate_signals_sample
    from core.signals import SAMPLE_SYMBOLS
    from alerts.telegram_alerts import send_test_alert
except Exception as e:
    st.title("🚨 Startup error")
    st.error("A required module failed to import. See details below.")
    st.exception(e)
    st.stop()

st.title("📊 NSE-500 Breakout Scanner (Stable)")

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
            "or **Generate sample signals** for demo output."
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
st.caption(
    "This app uses Alpha Vantage (if configured) → NSE public endpoints → Yahoo fallback. "
    "Click Force compute to refresh data. No Zerodha credentials used."
)
st.caption("Last updated: " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
