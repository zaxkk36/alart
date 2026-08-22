"""
RSI (Wilder smoothing, matching TradingView's ta.rsi) + SMA of RSI,
and the entry-signal detection logic:

LONG signal:  RSI crosses ABOVE its SMA while both RSI and the SMA
              are below 50 at that candle close.
SHORT signal: RSI crosses BELOW its SMA while both RSI and the SMA
              are above 50 at that candle close.
"""
import pandas as pd

from config import RSI_LENGTH, RSI_MA_LENGTH, RSI_MID


def wilder_rsi(close: pd.Series, length: int = RSI_LENGTH) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    # where avg_loss is 0 (no losses in the window) RSI is 100
    rsi = rsi.where(avg_loss != 0, 100.0)
    return rsi


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rsi"] = wilder_rsi(df["close"], RSI_LENGTH)
    df["rsi_ma"] = df["rsi"].rolling(RSI_MA_LENGTH).mean()
    return df


def detect_signal(df: pd.DataFrame) -> dict | None:
    """
    Looks at the last two CLOSED candles of df (which should already
    have 'rsi' and 'rsi_ma' columns) and returns a signal dict if the
    most recent candle close is a valid cross, else None.
    """
    if len(df) < 2:
        return None

    prev, last = df.iloc[-2], df.iloc[-1]
    if pd.isna(prev["rsi_ma"]) or pd.isna(last["rsi_ma"]):
        return None  # not enough history yet for the MA to be valid

    crossed_up = prev["rsi"] <= prev["rsi_ma"] and last["rsi"] > last["rsi_ma"]
    crossed_down = prev["rsi"] >= prev["rsi_ma"] and last["rsi"] < last["rsi_ma"]

    if crossed_up and last["rsi"] < RSI_MID and last["rsi_ma"] < RSI_MID:
        return {
            "side": "LONG",
            "candle_time": last["open_time"],
            "close": last["close"],
            "rsi": last["rsi"],
            "rsi_ma": last["rsi_ma"],
        }

    if crossed_down and last["rsi"] > RSI_MID and last["rsi_ma"] > RSI_MID:
        return {
            "side": "SHORT",
            "candle_time": last["open_time"],
            "close": last["close"],
            "rsi": last["rsi"],
            "rsi_ma": last["rsi_ma"],
        }

    return None


def candle_color(candle) -> str:
    """'RED' if the candle closed below its open, 'GREEN' if above, else 'DOJI'."""
    if candle["close"] < candle["open"]:
        return "RED"
    if candle["close"] > candle["open"]:
        return "GREEN"
    return "DOJI"


def get_snapshot(df: pd.DataFrame) -> dict | None:
    """
    Returns the CURRENT state of the last closed candle: is RSI above
    or below its MA right now, and where both sit relative to 50.
    This is not a cross/signal check — just a snapshot for manual review.
    """
    if len(df) < 1:
        return None

    last = df.iloc[-1]
    if pd.isna(last["rsi_ma"]):
        return None  # not enough history yet for the MA to be valid

    position = "ABOVE" if last["rsi"] > last["rsi_ma"] else "BELOW"
    bias = "LONG watch" if position == "ABOVE" else "SHORT watch"

    # whether it also matches the original strategy's 50-zone filter
    in_zone = (
        (position == "ABOVE" and last["rsi"] < RSI_MID and last["rsi_ma"] < RSI_MID)
        or (position == "BELOW" and last["rsi"] > RSI_MID and last["rsi_ma"] > RSI_MID)
    )

    return {
        "candle_time": last["open_time"],
        "close": last["close"],
        "rsi": last["rsi"],
        "rsi_ma": last["rsi_ma"],
        "position": position,
        "bias": bias,
        "in_zone": in_zone,
    }
