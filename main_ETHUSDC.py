import time
from datetime import datetime, timedelta
from config_ETHUSDC import client, SYMBOL
from config_ETHUSDC import get_current_position_notional, cancel_all_open_orders, get_tick_size, get_price_precision
from limit_order_ETHUSDC import place_post_only_limit_order
from TP_ETHUSDC import place_take_profit_orders
from SL_ETHUSDC import update_single_trailing_stoploss
from SHA_ETHUSDC import get_binance_klines, smoothed_heikin_ashi, get_trend_phases
import threading
from logger_config import logger

def get_latest_trend(df, len1, len2):
    ha_df = smoothed_heikin_ashi(df, len1, len2)
    trend_phases = get_trend_phases(ha_df)
    return trend_phases.iloc[-1]['Trend'], trend_phases.iloc[-1]['Start']

def has_open_position(direction):
    """
    Check if there is an open position in the given direction (long or short).
    """
    positions = client.futures_position_information(symbol=SYMBOL)
    for pos in positions:
        amt = float(pos['positionAmt'])
        if direction == "long" and amt > 0:
            return True
        elif direction == "short" and amt < 0:
            return True
    return False

def slide_limit_order(direction, end_time):
    from config_ETHUSDC import SYMBOL, close_all_positions

    cancel_all_open_orders()
    close_all_positions()

    last_price = None

    while datetime.now() < end_time:
        position_notional = get_current_position_notional()
        if position_notional >= 400000:
            logger.info("[%s] Position size reached %s, stopping new orders.", datetime.now(), position_notional)
            cancel_all_open_orders()
            break

        try:
            orderbook = client.futures_order_book(symbol=SYMBOL, limit=5)
            current_price = (
                float(orderbook['bids'][0][0]) if direction == "long"
                else float(orderbook['asks'][0][0])
            )
        except Exception as e:
            logger.error("Order book fetch error: %s", e)
            time.sleep(1)
            continue

        if last_price is None:
            cancel_all_open_orders()
            place_post_only_limit_order(direction, current_price)
            last_price = current_price
        elif direction == "long" and current_price > last_price:
            cancel_all_open_orders()
            place_post_only_limit_order(direction, current_price)
            last_price = current_price
        elif direction == "short" and current_price < last_price:
            cancel_all_open_orders()
            place_post_only_limit_order(direction, current_price)
            last_price = current_price

        time.sleep(1)

    logger.info("Sliding complete. Checking position status...")
    max_wait_seconds = 1 # set post waiting period
    start_check_time = datetime.now()

    while (datetime.now() - start_check_time).seconds < max_wait_seconds:
        position_notional = get_current_position_notional()
        if position_notional > 0:
            positions = client.futures_position_information(symbol=SYMBOL)
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    entry_price = float(pos['entryPrice'])
                    position_qty = abs(float(pos['positionAmt']))
                    direction_for_tp = "long" if float(pos['positionAmt']) > 0 else "short"
                    break
            else:
                return

            cancel_all_open_orders()
            place_take_profit_orders(direction_for_tp, entry_price, position_qty)

            tick_size = get_tick_size()
            price_precision = get_price_precision(tick_size)

            trailing_thread = threading.Thread(
                target=update_single_trailing_stoploss,
                args=(direction_for_tp, position_qty, tick_size, entry_price, price_precision),
                daemon=True
            )
            trailing_thread.start()
            break
        else:
            time.sleep(2)

def main():
    prev_trend_id = None
    polling_interval = 60

    while True:
        df_5m = get_binance_klines("ETHUSDT", "4h", 1000)
        df_1m = get_binance_klines("ETHUSDT", "1h", 1000)

        trend_5m, start_5m = get_latest_trend(df_5m, 1, 1)
        trend_1m, start_1m = get_latest_trend(df_1m, 4, 4)

        current_trend_id = f"{trend_1m}_{start_1m}_{trend_5m}_{start_5m}"

        if trend_1m == trend_5m and current_trend_id != prev_trend_id:
            direction = "long" if trend_1m == "uptrend" else "short"

            if not has_open_position(direction):
                end_time = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=1)
                slide_limit_order(direction, end_time)
            else:
                logger.info("Position already open in %s direction. Skipping new trade.", direction)

        prev_trend_id = current_trend_id
        time.sleep(polling_interval)

if __name__ == "__main__":
    main()