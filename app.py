import streamlit as st
import pandas as pd
import json, os, time
from core.signals import load_latest_signals, generate_signals_sample, compute_and_store_signals
from alerts.telegram_alerts import send_test_alert

st.set_page_config(page_title='NSE500 Breakout Scanner', layout='wide')
st.title('NSE-500 Breakout Scanner (Expanded)')

col1, col2 = st.columns([3,1])
with col2:
    st.markdown('**Admin**')
    if st.button('Generate sample signals (debug)'):
        generate_signals_sample()
        st.success('Sample signals generated. Refresh page.')
    if st.button('Force compute signals now'):
        compute_and_store_signals()
        st.success('Signals computed. Refresh page.')
    if st.button('Send test Telegram Alert'):
        resp = send_test_alert('This is a test alert from NSE500 Scanner demo.')
        st.write(resp)

with col1:
    st.markdown('### Latest Signals')
    signals = load_latest_signals()
    if signals is None:
        st.info('No signals yet. Scheduler will populate signals periodically.')
    else:
        df = pd.DataFrame(signals)
        display_cols = ['symbol','timeframe','signal_time','action','buy_price','stoploss','target','holding_duration','holding_reason','confidence','reasons']
        df = df[[c for c in display_cols if c in df.columns]]
        st.dataframe(df)
        if not df.empty:
            sym = st.selectbox('Open chart for', df['symbol'].unique())
            st.write('Chart placeholder for', sym)

st.markdown('---')
st.markdown('**Notes**: This expanded demo adds MACD, ATR, Bollinger Bands, VWAP and multi-timeframe checks. Holding duration is estimated from rules.')
st.markdown('Last updated: ' + time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()))
