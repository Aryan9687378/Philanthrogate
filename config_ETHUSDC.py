import time
from itertools import count
from binance.client import Client
from logger_config import logger

API_KEY = ""  # specify key
API_SECRET = ""  # specify key
SYMBOL = "ETHUSDT"  # specify symbol

client = Client(API_KEY, API_SECRET)
#client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

client.futures_change_leverage(symbol=SYMBOL, leverage=40)  # specify leverage

server_time = client.futures_time()['serverTime']
local_time = int(time.time() * 1000)
client.timestamp_offset = server_time - local_time
logger.info("Timestamp offset set: %s ms", client.timestamp_offset)

order_id_counter = count(1)

def get_unique_order_id(prefix):
    return f"{prefix}_{next(order_id_counter)}"

def get_quantity_from_balance(leverage=39):  # specify max allocated leverage
    try:
        balance_info = client.futures_account_balance()
        usdt_balance = next(item for item in balance_info if item['asset'] == 'USDT')
        available_usdt = float(usdt_balance['availableBalance'])
        price = float(client.futures_symbol_ticker(symbol=SYMBOL)['price'])
        quantity = round((available_usdt * leverage) / price, 3)
        return quantity
    except Exception as e:
        logger.error("Error fetching balance or price: %s", e)
        return 0

def cancel_all_open_orders():
    try:
        client.futures_cancel_all_open_orders(symbol=SYMBOL)
    except Exception as e:
        logger.error("Error cancelling orders: %s", e)

def close_all_positions():
    try:
        positions = client.futures_position_information(symbol=SYMBOL)
        for pos in positions:
            amt = float(pos['positionAmt'])
            if amt != 0:
                qty = abs(amt)
                side = Client.SIDE_SELL if amt > 0 else Client.SIDE_BUY
                client.futures_create_order(
                    symbol=SYMBOL,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=qty,
                    reduceOnly=True
                )
                logger.info("Closed position of size %s with side %s", qty, side)
    except Exception as e:
        logger.error("Error closing positions: %s", e)

def get_current_position_notional():
    try:
        positions = client.futures_position_information(symbol=SYMBOL)
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                return abs(float(pos['notional']))
        return 0
    except Exception as e:
        logger.error("Error fetching position info: %s", e)
        return 0

def get_tick_size():
    exchange_info = client.futures_exchange_info()
    for s in exchange_info['symbols']:
        if s['symbol'] == SYMBOL:
            for f in s['filters']:
                if f['filterType'] == 'PRICE_FILTER':
                    return float(f['tickSize'])
    raise Exception(f"Tick size not found for {SYMBOL}")

def get_price_precision(tick_size):
    return len(str(tick_size).split(".")[1].rstrip("0"))