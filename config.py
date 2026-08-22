import os

# ---- Telegram ----
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")  # where retest alerts get pushed

# ---- Binance Futures ----
BINANCE_FUTURES_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
BASE_INTERVAL = "15m"        # native Binance interval we aggregate FROM
BASE_INTERVAL_MINUTES = 15
AGG_FACTOR = 3                # 3 x 15m = 45m
TARGET_TF_MINUTES = BASE_INTERVAL_MINUTES * AGG_FACTOR  # 45

# how many aggregated (45m) candles we want available for indicator calc
LOOKBACK_CANDLES = 150
RAW_CANDLES_NEEDED = LOOKBACK_CANDLES * AGG_FACTOR  # 15m candles to fetch

# ---- Strategy settings ----
RSI_LENGTH = 7
RSI_MA_LENGTH = 14      # SMA of RSI
RSI_MID = 50
RSI_UPPER = 70
RSI_LOWER = 30

# ---- Watchlists ----
IMPORTANT_COINS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "LITUSDT",
    "ZECUSDT",
    "HYPEUSDT",
    "XAUUSDT",
]

WATCHLIST_COINS = [
    "1000PEPEUSDT",
    "WIFUSDT",
    "WLDUSDT",
    "FARTCOINUSDT",
    "PENGUUSDT",
    "ENAUSDT",
    "TAOUSDT",
]

# every coin from both lists, deduped, order preserved — this is what the
# retest-alert scheduler watches. /rsi and /ma still use the lists above.
_seen = set()
ALL_COINS = []
for _sym in IMPORTANT_COINS + WATCHLIST_COINS:
    if _sym not in _seen:
        ALL_COINS.append(_sym)
        _seen.add(_sym)

# ---- Retest alert (auto, scheduled) ----
# how many seconds after a 45m candle should officially close do we wait
# before pulling data, to make sure Binance has published the final kline
CLOSE_BUFFER_SECONDS = 15

# where "armed, waiting for retest" state is persisted per symbol
STATE_FILE = "state.json"
