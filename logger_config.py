import logging
from logging.handlers import TimedRotatingFileHandler
import os

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("TradeBot")
logger.setLevel(logging.INFO)

log_file = os.path.join(log_dir, "trade.log")
handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=3)
handler.suffix = "%Y-%m-%d"
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)