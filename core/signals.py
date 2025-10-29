# core/signals.py
# NSE-first data fetcher (public endpoints) with yfinance fallback.
# Produces signals.json and appends history to signals_history.csv

import os, json, math, time
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'signals_history.csv')

# Small sample of NSE tickers; expand later to NSE-500 symbols.
SAMPLE_SYMBOLS = ['RELIANCE.NS','TCS.NS','INFY.NS','HDFCBANK.NS','ICICIBANK.NS']

# Browser-like headers for NSE site
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
}

def fetch_ohlcv_nse(symbol, days=365):
    """
    Try NSE public historical endpoint. If it fails, fall back to yfinance.
    Returns DataFrame with columns Open,High,Low,Close,Volume indexed by Date.
    """
    nse_sym = symbol.split('.')[0]  # 'RELIANCE.NS' -> 'RELIANCE'
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        # Hit homepage to obtain cookies
        session.get('https://www.nseindia.com', timeout=10)
        to_date = datetime.utcnow().date()
        from_date = to_date - timedelta(days=days)
        url = (
            'https://www.nseindia.com/api/historical/cm/equity'
            f'?symbol={nse_sym}&series=[%22EQ%22]&from={from_date.strftime("%d-%m-%Y")}&to={to_date.strftime("%d-%m-%Y")}'
        )
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            # fallback
            return fetch_ohlcv_yf(symbol, days)
        data = r.json()
        if 'data' not in data or not data['data']:
            return fetch_ohlcv_yf(symbol, days)
        rows = data['data']
        df = pd.DataFrame(rows)
        # Normalize NSE fields -> Date, Open, High, Low, Close, Volume
        # NSE date format like '30-Sep-2025'
        df = df.rename(columns={
            'CH_TIMESTAMP':'Date','OPEN':'Open','HIGH':'High','LOW':'Low','CLOSE':'Close','TOTTRDQTY':'Volume'
        })
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y', errors='coerce')
        df = df.dropna(subset=['Date']).set_index('Date').sort_index()
        df = df[['Open','High','Low','Close','Volume']].astype(float)
        return df
    except Exception as e:
        # Fallback to Yahoo
        print('NSE fetch failed, falling back to yfinance:', e)
        return fetch_ohlcv_yf(symbol, days)

def fetch_ohlcv_yf(symbol, days=365):
    try:
        period = '1y' if days <= 365 else f'{math.ceil(days/365)}y'
        df = yf.download(symbol, period=period, interval='1d', progress=False, threads=False)
        if df is None or df.empty:
            return None
        df = df.dropna()
        return df[['Open','High','Low','Close','Volume']]
    except Exception as e:
        print('yfinance fetch failed', e)
        return None

def compute_indicators(df):
    df = df.copy()
    df['sma20'] = SMAIndicator(df['Close'], window=20).sma_indicator()
    df['sma50'] = SMAIndicator(df['Close'], window=50).sma_indicator()
    df['ema20'] = EMAIndicator(df['Close'], window=20).ema_indicator()
    df['ema50'] = EMAIndicator(df['Close'], window=50).ema_indicator()
    macd = MACD(df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['rsi14'] = RSIIndicator(df['Close'], window=14).rsi()
    df['atr14'] = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
    bb = BollingerBands(df['Close'], window=20, window_dev=2)
    df['bb_h'] = bb.bollinger_hband()
    df['bb_l'] = bb.bollinger_lband()
    tp = (df['High'] + df['Low'] + df['Close'])/3
    df['vwap_20'] = (tp * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum()
    return df

def analyze_symbol(symbol):
    # Fetch daily (1y) and weekly (3y) using NSE first
    daily = fetch_ohlcv_nse(symbol, days=365)
    weekly = fetch_ohlcv_nse(symbol, days=3*365)
    if daily is None or daily.empty:
        return None
    try:
        daily = compute_indicators(daily)
        # If weekly fetch returned daily-level data, resample weekly
        if weekly is not None and not weekly.empty:
            weekly = compute_indicators(weekly)
        else:
            weekly = compute_indicators(daily.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}))

        d_latest = daily.iloc[-1]
        d_prev = daily.iloc[-2]
        w_latest = weekly.iloc[-1]
        w_prev = weekly.iloc[-2]

        reasons = []
        confidence = 0.0

        # Breakout/momentum checks
        daily_break = d_latest['Close'] > d_prev['High']
        weekly_break = w_latest['Close'] > w_prev['High']
        rsi_ok = d_latest['rsi14'] > 55
        macd_ok = d_latest['macd'] > d_latest['macd_signal']
        ema_trend = d_latest['ema20'] > d_latest['ema50']
        vwap_ok = (not pd.isna(d_latest['vwap_20'])) and (d_latest['Close'] > d_latest['vwap_20'])
        vol20 = daily['Volume'].rolling(20).mean().iloc[-1] if 'Volume' in daily.columns else 0
        vol_ok = False
        if vol20 > 0 and d_latest['Volume'] > 1.2*vol20:
            vol_ok = True

        if daily_break:
            reasons.append('Daily breakout')
            confidence += 0.2
        if weekly_break:
            reasons.append('Weekly breakout')
            confidence += 0.35
        if rsi_ok:
            reasons.append('RSI>55')
            confidence += 0.15
        if macd_ok:
            reasons.append('MACD positive')
            confidence += 0.1
        if ema_trend:
            reasons.append('EMA trend up')
            confidence += 0.1
        if vwap_ok:
            reasons.append('Above VWAP')
            confidence += 0.05
        if vol_ok:
            reasons.append('Volume surge')
            confidence += 0.15
        else:
            reasons.append('Volume low - watch fakeout')
            confidence -= 0.1

        if confidence < 0.5:
            return None

        # Price levels
        buy_price = round(d_latest['Close'] * 1.001, 2)
        atr = d_latest['atr14'] if not pd.isna(d_latest['atr14']) else (daily['Close'].pct_change().std() * d_latest['Close'])
        stoploss = round(d_latest['Close'] - 2*atr, 2)
        target = round(d_latest['Close'] + 3*atr, 2)

        # Holding duration rules
        if weekly_break and confidence > 0.7:
            holding = 'Long (1-6 months)'
            holding_reason = 'Weekly breakout with strong momentum'
        elif confidence > 0.8 and ema_trend and macd_ok:
            holding = 'Medium (1-4 weeks)'
            holding_reason = 'High confidence and trend alignment'
        else:
            holding = 'Short (2-7 days)'
            holding_reason = 'Moderate confidence - prefer quick review'

        signal = {
            'symbol': symbol,
            'timeframe': 'Daily/Weekly',
            'signal_time': datetime.utcnow().isoformat(),
            'action': 'BUY',
            'buy_price': buy_price,
            'stoploss': stoploss,
            'target': target,
            'holding_duration': holding,
            'holding_reason': holding_reason,
            'confidence': round(float(confidence), 2),
            'reasons': '; '.join(reasons)
        }
        _append_history(signal)
        return signal
    except Exception as e:
        print('analyze_symbol exception', e)
        return None

def compute_and_store_signals():
    signals = []
    for sym in SAMPLE_SYMBOLS:
        try:
            r = analyze_symbol(sym)
            if r:
                signals.append(r)
        except Exception as e:
            print('Error analyzing', sym, e)
    with open(SIGNALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(signals, f, indent=2, default=str)
    return signals

def load_latest_signals():
    if not os.path.exists(SIGNALS_FILE):
        return None
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def _append_history(signal):
    import csv
    fields = ['symbol','timeframe','signal_time','action','buy_price','stoploss','target','holding_duration','holding_reason','confidence','reasons']
    write_header = not os.path.exists(HISTORY_FILE)
    with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        w.writerow({k:signal.get(k,'') for k in fields})
