# app.py  —  Full working Streamlit front-end for NSE-500 Breakout Scanner

import streamlit as st
import pandas as pd
import time

st.set_page_config(page_title="NSE500 Breakout Scanner", layout="wide")

# ───────────────────────────────────────────────────────────────────────────────
# Safe imports: wrap to show readable error instead of red screen
try:
    from core.signals import load_latest_signals, compute_and_store_signals, generate_signals_sample
    from alerts.telegram_alerts import send_test_alert
except Exception as e:
    st.title("🚨 Import Error — App couldn't start")
    st.error(
        "A required module failed to load. "
        "See details below and check your GitHub requirements.txt "
        "(remove python-telegram-bot if present)."
    )
    st.exception(e)
    st.stop()

# ───────────────────────────────────────────────────────────────────────────────
st.title("📊 NSE-500 Breakout Scanner (Expanded)")

col1, col2 = st.columns([3, 1])

# ───────────────  ADMIN PANEL  ───────────────
with col2:
    st.markdown("### ⚙️ Admin")
    if st.button("Generate sample signals (debug)"):
        generate_signals_sample()
        st.success("✅ Sample signals generated. Refresh the page to view them.")

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

# ───────────────  MAIN TABLE  ───────────────
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

        if not df.empty:
            sym = st.selectbox("Open chart for:", df["symbol"].unique())
            st.markdown(f"Chart placeholder for **{sym}** *(to be integrated later)*")

# ───────────────  FOOTER  ───────────────
st.markdown("---")
st.caption(
    "This version uses NSE public endpoints (with fallback to Yahoo Finance). "
    "Indicators: MACD, ATR, Bollinger Bands, VWAP, multi-timeframe checks. "
    "Holding duration is rule-based. No Zerodha keys or paid APIs required."
)
st.caption("Last updated: " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
