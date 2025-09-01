import pandas as pd
import numpy as np
import time
from binance.client import Client
from datetime import datetime
from logger_config import logger

def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def smoothed_heikin_ashi(df, len1, len2):
    o = ema(df['Open'], len1)
    h = ema(df['High'], len1)
    l = ema(df['Low'], len1)
    c = ema(df['Close'], len1)

    haclose = (o + h + l + c) / 4
    haopen = [(o.iloc[0] + c.iloc[0]) / 2]
    for i in range(1, len(df)):
        haopen.append((haopen[i - 1] + haclose.iloc[i - 1]) / 2)
    haopen = pd.Series(haopen, index=df.index)

    hahigh = pd.concat([h, haopen, haclose], axis=1).max(axis=1)
    halow = pd.concat([l, haopen, haclose], axis=1).min(axis=1)

    o2 = ema(haopen, len2)
    h2 = ema(hahigh, len2)
    l2 = ema(halow, len2)
    c2 = ema(haclose, len2)

    trend = np.where(o2 > c2, 'downtrend', 'uptrend')

    return pd.DataFrame({
        'Date': df['Date'],
        'HA_Open': o2,
        'HA_High': h2,
        'HA_Low': l2,
        'HA_Close': c2,
        'Trend': trend
    })

def get_trend_phases(df):
    phases = []
    current_trend = df.iloc[0]['Trend']
    start_time = df.iloc[0]['Date']

    for i in range(1, len(df)):
        row = df.iloc[i]
        if row['Trend'] != current_trend:
            phases.append({
                'Start': start_time,
                'End': df.iloc[i-1]['Date'],
                'Trend': current_trend
            })
            current_trend = row['Trend']
            start_time = row['Date']

    phases.append({'Start': start_time, 'End': df.iloc[-1]['Date'], 'Trend': current_trend})
    return pd.DataFrame(phases)

def get_binance_klines(symbol="ETHUSDT", interval="1h", limit=1000, api_key='', api_secret=''):
    client = Client(api_key, api_secret)
    # client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"  # ✅ Redirect to testnet
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)

    df = pd.DataFrame(klines, columns=[
        "Open Time", "Open", "High", "Low", "Close", "Volume",
        "Close Time", "Quote Asset Volume", "Number of Trades",
        "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ])
    df['Date'] = pd.to_datetime(df['Open Time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    df['Open'] = df['Open'].astype(float)
    df['High'] = df['High'].astype(float)
    df['Low'] = df['Low'].astype(float)
    df['Close'] = df['Close'].astype(float)
    return df[['Date', 'Open', 'High', 'Low', 'Close']]

if __name__ == "__main__":
    api_key = ""  # specify key
    api_secret = ""  # specify key
    symbol = "ETHUSDT"  # specify symbol
    polling_interval = 60  # specify seconds

    logger.info("%-10s | %-10s | %s", "Timeframe", "Price", "Trend Phase")
    logger.info("%s", "-" * 40)

    try:
        while True:
            for tf, len1, len2 in [("1h", 4, 4), ("4h", 1, 1)]:
                df = get_binance_klines(symbol=symbol, interval=tf, limit=1000, api_key=api_key, api_secret=api_secret)
                current_price = df['Close'].iloc[-1]
                ha_df = smoothed_heikin_ashi(df, len1=len1, len2=len2)

                trend_phases = get_trend_phases(ha_df)
                current_trend = trend_phases.iloc[-1]['Trend']

                logger.info("%-10s | %-10.2f | %s", tf, current_price, current_trend)

            time.sleep(polling_interval)

    except KeyboardInterrupt:
        logger.info("Polling stopped.")