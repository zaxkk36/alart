"""
Fetches klines from Binance USDT-M Futures and builds true 45-minute
candles by aggregating 3x 15-minute candles, anchored to UTC midnight
(00:00, 00:45, 01:30, 02:15, 03:00, ...) so it lines up with a 45m
chart on TradingView.
"""
import logging
import requests
import pandas as pd

from config import (
    BINANCE_FUTURES_KLINES_URL,
    BASE_INTERVAL,
    AGG_FACTOR,
    RAW_CANDLES_NEEDED,
)

log = logging.getLogger(__name__)

# Binance kline array indices
OPEN_TIME, OPEN, HIGH, LOW, CLOSE, VOLUME, CLOSE_TIME = range(7)


def fetch_raw_klines(symbol: str, limit: int = RAW_CANDLES_NEEDED) -> pd.DataFrame:
    """Fetch raw 15m klines for a symbol from Binance Futures."""
    params = {
        "symbol": symbol,
        "interval": BASE_INTERVAL,
        "limit": min(limit, 1500),  # Binance max per request
    }
    resp = requests.get(BINANCE_FUTURES_KLINES_URL, params=params, timeout=15)
    resp.raise_for_status()
    raw = resp.json()

    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df[["open_time", "open", "high", "low", "close", "volume"]]


def aggregate_to_45m(df_15m: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate 15m candles into 45m candles anchored to UTC midnight.
    Only keeps groups that have all 3 constituent 15m candles (a
    partial/still-forming 45m candle is dropped).
    """
    df = df_15m.copy()
    # minutes since UTC midnight for each candle's open time
    minutes_since_midnight = df["open_time"].dt.hour * 60 + df["open_time"].dt.minute
    # which 45m bucket this 15m candle belongs to
    df["bucket_start"] = df["open_time"] - pd.to_timedelta(
        minutes_since_midnight % 45, unit="m"
    )

    grouped = df.groupby("bucket_start")
    agg = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        n=("close", "count"),
    ).reset_index()

    # drop any bucket that doesn't have all 3 15m candles (incomplete)
    agg = agg[agg["n"] == AGG_FACTOR].drop(columns="n")
    agg = agg.rename(columns={"bucket_start": "open_time"})
    return agg.sort_values("open_time").reset_index(drop=True)


def get_45m_candles(symbol: str) -> pd.DataFrame:
    """Convenience wrapper: fetch raw data and return aggregated 45m candles."""
    raw = fetch_raw_klines(symbol)
    return aggregate_to_45m(raw)
