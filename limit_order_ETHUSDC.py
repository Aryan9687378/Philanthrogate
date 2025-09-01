from config_ETHUSDC import client, SYMBOL, get_quantity_from_balance, cancel_all_open_orders
from binance.client import Client
from logger_config import logger

def place_post_only_limit_order(direction, price):
    quantity = get_quantity_from_balance()
    if quantity <= 0:
        logger.info("Insufficient balance to place order.")
        return

    side = Client.SIDE_BUY if direction == "long" else Client.SIDE_SELL
    try:
        client.futures_create_order(
            symbol=SYMBOL,
            side=side,
            type=Client.ORDER_TYPE_MARKET, # specify market or limit
            quantity=quantity,
            #price=str(price), # uncomment for limit
            #timeInForce='GTX' # uncomment for limit
        )
        logger.info(f"Placed {direction.upper()} limit order at {price} for quantity {quantity}")
    except Exception as e:
        logger.error("Order placement error: %s", e)