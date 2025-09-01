import time
from config_ETHUSDC import client, SYMBOL, get_unique_order_id
from binance.client import Client
from logger_config import logger

def update_single_trailing_stoploss(direction, quantity, tick_size, entry_price, price_precision):
    logger.info("Placing fixed stop-loss...")

    side = Client.SIDE_SELL if direction == "long" else Client.SIDE_BUY
    sl_pct = 0.0088  # stop-loss distance (e.g., 0.88%)

    def round_price(p):
        return round(round(p / tick_size) * tick_size, price_precision)

    def place_market_stop_order(stop_price):
        client_order_id = get_unique_order_id("stop_market")
        try:
            client.futures_create_order(
                symbol=SYMBOL,
                side=side,
                type=Client.FUTURE_ORDER_TYPE_STOP_MARKET,
                stopPrice=str(stop_price),
                quantity=round(quantity, 3),
                reduceOnly=True,
                newClientOrderId=client_order_id
            )
            logger.info("[PLACED FIXED SL] stop: %s", stop_price)
            return client_order_id
        except Exception as e:
            logger.error("Error placing SL Market Order: %s", e)
            return None

    # Calculate stop-loss only once
    if direction == "long":
        sl_price = round_price(entry_price * (1 - sl_pct))
    else:
        sl_price = round_price(entry_price * (1 + sl_pct))

    # Place stop-loss and exit
    place_market_stop_order(sl_price)
    logger.info("Fixed stop-loss order placed. Exiting function.")