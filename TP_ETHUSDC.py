import pandas as pd
from config_ETHUSDC import client, SYMBOL, get_tick_size, get_price_precision
from binance.client import Client
from logger_config import logger

def _calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 1) -> pd.Series:
    tr_df = pd.DataFrame({
        'high_low': high - low,
        'high_close': (high - close.shift(1)).abs(),
        'low_close': (low - close.shift(1)).abs()
    })
    tr = tr_df.max(axis=1)
    atr = tr.rolling(window=length).mean()
    return atr

def _get_recent_hlc(symbol: str, interval: str = "1h", limit: int = 100):
    """Fetch recent futures klines and return high/low/close as Series."""
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        "Open Time","Open","High","Low","Close","Volume",
        "Close Time","Quote Asset Volume","Number of Trades",
        "Taker Buy Base Asset Volume","Taker Buy Quote Asset Volume","Ignore"
    ])
    df["High"] = df["High"].astype(float)
    df["Low"] = df["Low"].astype(float)
    df["Close"] = df["Close"].astype(float)
    return df["High"], df["Low"], df["Close"]

def place_take_profit_orders(direction: str, entry_price: float, quantity: float):
    """
    Single TP, TAKE_PROFIT_MARKET (triggered market) at:
      - entry ± min(ATR, 1% of current price)

    direction: "long" or "short"
    """
    high, low, close = _get_recent_hlc(SYMBOL)
    atr_series = _calculate_atr(high, low, close, length=1)
    atr_value = float(atr_series.iloc[-1])

    current_price = float(client.futures_symbol_ticker(symbol=SYMBOL)['price'])
    one_percent = current_price * 0.01

    tp_distance = atr_value if atr_value <= one_percent else one_percent

    if direction == "long":
        target_price = entry_price + tp_distance
        side = Client.SIDE_SELL
    else:
        target_price = entry_price - tp_distance
        side = Client.SIDE_BUY

    tick_size = get_tick_size()
    price_precision = get_price_precision(tick_size)
    target_price = round(round(target_price / tick_size) * tick_size, price_precision)

    qty = round(quantity, 3)

    try:
        client.futures_create_order(
            symbol=SYMBOL,
            side=side,
            type=Client.FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
            stopPrice=str(target_price),
            quantity=qty,
            reduceOnly=True,
            workingType='CONTRACT_PRICE'
        )
        logger.info("[TP-MARKET] qty=%s trigger=%s (distance=%.2f | ATR=%.2f | 1%%=%.2f)", qty, target_price, tp_distance, atr_value, one_percent)
    except Exception as e:
        logger.error("Error placing TP-MARKET: %s", e)