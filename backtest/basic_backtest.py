import pandas as pd, numpy as np, os, csv
from core.signals import SAMPLE_SYMBOLS, fetch_ohlcv, compute_indicators
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'backtest_trades.csv')

def simulate_signal_trade(symbol, signal_date):
    # Fetch next 60 days of daily data starting from signal_date
    df = fetch_ohlcv(symbol, period='2y', interval='1d')
    if df is None or df.empty:
        return None
    df = df.loc[df.index >= pd.to_datetime(signal_date)]
    if df.shape[0] < 2:
        return None
    # entry at next day's open
    entry_row = df.iloc[1]
    entry = entry_row['Open']
    # naive stoploss and target using ATR from previous day
    df_full = fetch_ohlcv(symbol, period='3mo', interval='1d')
    df_full = compute_indicators(df_full)
    atr = df_full['atr14'].iloc[-1] if 'atr14' in df_full.columns else (df_full['Close'].pct_change().std()*entry)
    stop = entry - 2*atr
    target = entry + 3*atr
    # simulate forward until stop or target or 30 days
    for i in range(1, min(30, df.shape[0])):
        row = df.iloc[i]
        low = row['Low']
        high = row['High']
        if low <= stop:
            return {'symbol':symbol,'entry':entry,'exit':stop,'profit':(stop-entry)/entry,'win':False}
        if high >= target:
            return {'symbol':symbol,'entry':entry,'exit':target,'profit':(target-entry)/entry,'win':True}
    # if neither hit, exit at last close
    last = df.iloc[min(30, df.shape[0]-1)]
    exitp = last['Close']
    return {'symbol':symbol,'entry':entry,'exit':exitp,'profit':(exitp-entry)/entry,'win': (exitp>entry)}

def run_backtest_from_history(history_csv= os.path.join(os.path.dirname(__file__),'..','data','signals_history.csv')):
    if not os.path.exists(history_csv):
        print('History CSV not found at', history_csv)
        return
    trades = []
    df = pd.read_csv(history_csv, parse_dates=['signal_time'])
    for idx, row in df.iterrows():
        res = simulate_signal_trade(row['symbol'], row['signal_time'])
        if res:
            trades.append({**res, 'signal_time': row['signal_time']})
    outdf = pd.DataFrame(trades)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    outdf.to_csv(OUT, index=False)
    print('Backtest complete. Trades saved to', OUT)

if __name__ == '__main__':
    run_backtest_from_history()
