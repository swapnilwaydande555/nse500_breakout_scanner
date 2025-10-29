import os, json, time
import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'signals_history.csv')

# Expanded sample list (common NSE tickers in Yahoo format)
SAMPLE_SYMBOLS = ['RELIANCE.NS','TCS.NS','INFY.NS','HDFCBANK.NS','ICICIBANK.NS']

def fetch_ohlcv(symbol, period='2y', interval='1d'):
    # Helper wrapper around yfinance
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)
        if df is None or df.empty:
            return None
        df = df.dropna()
        return df
    except Exception as e:
        print('yfinance error', e)
        return None

def compute_indicators(df):
    # requires df with Open High Low Close Volume and datetime index
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
    # Simple VWAP-like: cumulative typical price * vol / cumulative vol for window
    tp = (df['High'] + df['Low'] + df['Close'])/3
    df['vwap_20'] = (tp * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum()
    return df

def multi_timeframe_checks(symbol):
    # fetch daily and weekly, compute indicators and check breakout on both
    daily = fetch_ohlcv(symbol, period='1y', interval='1d')
    weekly = fetch_ohlcv(symbol, period='3y', interval='1wk')
    if daily is None or weekly is None:
        return None
    daily = compute_indicators(daily)
    weekly = compute_indicators(weekly)
    return daily, weekly

def analyze_symbol(symbol):
    try:
        daily, weekly = multi_timeframe_checks(symbol)
        if daily is None or weekly is None:
            return None
        # Last rows
        d_latest = daily.iloc[-1]
        d_prev = daily.iloc[-2]
        w_latest = weekly.iloc[-1]
        w_prev = weekly.iloc[-2]

        reasons = []
        confidence = 0.0
        action = None
        # Breakout rules: daily close > previous daily high AND weekly close > previous weekly high
        daily_break = d_latest['Close'] > d_prev['High']
        weekly_break = w_latest['Close'] > w_prev['High']
        # Momentum checks
        rsi_ok = d_latest['rsi14'] > 55
        macd_ok = d_latest['macd'] > d_latest['macd_signal']
        ema_trend = d_latest['ema20'] > d_latest['ema50']
        vwap_ok = d_latest['Close'] > d_latest['vwap_20'] if not pd.isna(d_latest['vwap_20']) else True
        # Volume confirmation
        vol20 = daily['Volume'].rolling(20).mean().iloc[-1] if 'Volume' in daily.columns else 0
        vol_ok = False
        if vol20>0 and d_latest['Volume'] > 1.2*vol20:
            vol_ok = True

        # Decide action and confidence
        if daily_break:
            reasons.append('Daily breakout: close > prev high')
            confidence += 0.2
        if weekly_break:
            reasons.append('Weekly breakout: weekly close > prev weekly high')
            confidence += 0.35
        if rsi_ok:
            reasons.append('RSI>55')
            confidence += 0.15
        if macd_ok:
            reasons.append('MACD positive')
            confidence += 0.1
        if ema_trend:
            reasons.append('EMA20>EMA50 (uptrend)')
            confidence += 0.1
        if vwap_ok:
            reasons.append('Price above 20-day VWAP')
            confidence += 0.05
        if vol_ok:
            reasons.append('Volume confirmed (20-day avg surge)')
            confidence += 0.15
        else:
            reasons.append('Volume not sufficiently high — check for fakeout')
            confidence -= 0.1

        # Determine action
        if confidence >= 0.5:
            action = 'BUY'
        else:
            return None  # not strong enough

        # Fake breakout detector: if close reversed strongly next bar recently, mark lower confidence
        # (We approximate by checking last 3-day return)
        recent_ret = (daily['Close'].pct_change().iloc[-3:]).sum()
        if recent_ret < -0.05:
            reasons.append('Recent negative momentum; possible reversal')
            confidence -= 0.15

        confidence = max(0.0, min(1.0, confidence))

        # Price levels
        buy_price = round(d_latest['Close'] * 1.001, 2)
        atr = d_latest['atr14'] if not pd.isna(d_latest['atr14']) else (daily['Close'].pct_change().std()*d_latest['Close'])
        stoploss = round(d_latest['Close'] - 2*atr, 2)
        target = round(d_latest['Close'] + 3*atr, 2)

        # Holding duration estimator (rule-based with clear explanation)
        holding = 'Short (minutes-hours)'  # default, though minutes require intraday data; we will provide days when daily signal
        holding_reason = ''
        # If weekly_break and strong momentum -> Long
        if weekly_break and confidence > 0.7:
            holding = 'Long (1-6 months)'
            holding_reason = 'Weekly breakout + strong momentum historically persists'
        elif confidence > 0.8 and ema_trend and macd_ok:
            holding = 'Medium (1-4 weeks)'
            holding_reason = 'High confidence, trend aligned across indicators'
        else:
            holding = 'Short (2-7 days)'
            holding_reason = 'Moderate confidence; prefer short review period'

        result = {
            'symbol': symbol,
            'timeframe': 'Daily/Weekly',
            'signal_time': datetime.utcnow().isoformat(),
            'action': action,
            'buy_price': buy_price,
            'stoploss': stoploss,
            'target': target,
            'holding_duration': holding,
            'holding_reason': holding_reason,
            'confidence': round(float(confidence),2),
            'reasons': '; '.join(reasons)
        }
        # Append to history CSV
        _append_history(result)
        return result
    except Exception as e:
        print('analyze_symbol error', e)
        return None

def _append_history(signal):
    import csv, os
    fields = ['symbol','timeframe','signal_time','action','buy_price','stoploss','target','holding_duration','holding_reason','confidence','reasons']
    write_header = not os.path.exists(HISTORY_FILE)
    with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
        import csv
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        w.writerow({k:signal.get(k,'') for k in fields})

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
        json.dump(signals, f, default=str, indent=2)
    return signals

def load_latest_signals():
    if not os.path.exists(SIGNALS_FILE):
        return None
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_signals_sample():
    # Keep as compatibility helper
    s = []
    now = datetime.utcnow().isoformat()
    for sym in SAMPLE_SYMBOLS:
        s.append({
            'symbol': sym,
            'timeframe': 'Daily/Weekly',
            'signal_time': now,
            'action': 'BUY',
            'buy_price': 100.0,
            'stoploss': 95.0,
            'target': 110.0,
            'holding_duration': 'Medium (1-4 weeks)',
            'holding_reason': 'Demo sample',
            'confidence': 0.78,
            'reasons': 'Sample generated'
        })
    with open(SIGNALS_FILE,'w', encoding='utf-8') as f:
        json.dump(s,f,indent=2)
    return s
