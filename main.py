import logging
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    IMPORTANT_COINS,
    WATCHLIST_COINS,
    ALL_COINS,
    TARGET_TF_MINUTES,
    CLOSE_BUFFER_SECONDS,
)
from market_data import get_45m_candles
from indicators import add_indicators, get_snapshot, detect_signal, candle_color
from state import load_state, save_state, arm, disarm, get_armed

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("rsi-bot")


# ---------- /rsi and /ma: simple on-demand snapshot ----------

def format_snapshot_line(symbol: str, snap: dict) -> str:
    side = "Long" if snap["position"] == "ABOVE" else "Short"
    arrow = "🟢" if side == "Long" else "🔴"
    return f"{arrow}{symbol}-{side}"


def snapshot_symbol(symbol: str) -> str:
    try:
        candles = get_45m_candles(symbol)
    except Exception as e:
        log.error("Failed to fetch candles for %s: %s", symbol, e)
        return f"⚠️{symbol}: fetch failed"

    if len(candles) < 20:
        return f"⚠️{symbol}: not enough history yet"

    candles = add_indicators(candles)
    snap = get_snapshot(candles)
    if not snap:
        return f"⚠️{symbol}: indicators not ready yet"

    return format_snapshot_line(symbol, snap)


async def cmd_rsi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/rsi — snapshot of the IMPORTANT coins list."""
    lines = [snapshot_symbol(sym) for sym in IMPORTANT_COINS]
    await update.message.reply_text("\n".join(lines))


async def cmd_ma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ma — snapshot of the WATCHLIST coins list."""
    lines = [snapshot_symbol(sym) for sym in WATCHLIST_COINS]
    await update.message.reply_text("\n".join(lines))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "RSI/MA bot.\n"
        "/rsi — important coins snapshot\n"
        "/ma — watchlist coins snapshot\n"
        "Retest alerts fire automatically for all coins, no command needed."
    )


# ---------- Retest alert: scheduled, auto ----------
# Sequence per symbol:
#   1. RSI breaks its MA in the correct 50-zone (same logic as before) -> "armed"
#   2. We wait for the NEXT closed candle after the break.
#      - Armed LONG  -> need a RED candle   (pullback/retest) to confirm.
#      - Armed SHORT -> need a GREEN candle (pullback/retest) to confirm.
#   3. On confirmation -> send alert, clear armed state.
#   4. A new break (in either direction) always re-arms/overwrites old state.

def process_symbol_for_retest(symbol: str, state: dict) -> str | None:
    try:
        candles = get_45m_candles(symbol)
    except Exception as e:
        log.error("Retest check failed to fetch %s: %s", symbol, e)
        return None

    if len(candles) < 20:
        return None

    candles = add_indicators(candles)
    latest = candles.iloc[-1]
    latest_iso = latest["open_time"].isoformat()

    alert_msg = None

    # 1) check retest confirmation against PRIOR armed state first
    armed = get_armed(state, symbol)
    if armed and latest_iso > armed["break_time"]:
        color = candle_color(latest)
        if armed["direction"] == "LONG" and color == "RED":
            alert_msg = (
                f"🎯 {symbol} retest confirmed — LONG\n"
                f"Broke {armed['break_time']}, retest candle {latest_iso}\n"
                f"Close: {latest['close']:.6g}"
            )
            disarm(state, symbol)
        elif armed["direction"] == "SHORT" and color == "GREEN":
            alert_msg = (
                f"🎯 {symbol} retest confirmed — SHORT\n"
                f"Broke {armed['break_time']}, retest candle {latest_iso}\n"
                f"Close: {latest['close']:.6g}"
            )
            disarm(state, symbol)
        # else: still waiting, stays armed, no action

    # 2) check for a NEW break (always re-arms, even if we just fired above)
    new_signal = detect_signal(candles)
    if new_signal:
        arm(state, symbol, new_signal["side"], new_signal["candle_time"].isoformat())

    return alert_msg


async def scheduled_retest_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    log.info("Running scheduled retest check across %d coins...", len(ALL_COINS))
    state = load_state()
    alerts = []
    for symbol in ALL_COINS:
        msg = process_symbol_for_retest(symbol, state)
        if msg:
            alerts.append(msg)
    save_state(state)

    for msg in alerts:
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

    if not alerts:
        log.info("No retest confirmations this cycle.")


def next_45m_boundary(now: datetime) -> datetime:
    """Next UTC time that's a multiple of 45 minutes past midnight."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes_since_midnight = (now - midnight).total_seconds() / 60
    next_bucket = ((int(minutes_since_midnight) // TARGET_TF_MINUTES) + 1) * TARGET_TF_MINUTES
    return midnight + timedelta(minutes=next_bucket, seconds=CLOSE_BUFFER_SECONDS)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables."
        )

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rsi", cmd_rsi))
    app.add_handler(CommandHandler("ma", cmd_ma))

    start_time = next_45m_boundary(datetime.now(timezone.utc))
    app.job_queue.run_repeating(
        scheduled_retest_check,
        interval=timedelta(minutes=TARGET_TF_MINUTES),
        first=start_time,
        name="retest_alert_check",
    )
    log.info("First retest check at %s UTC, then every %dm", start_time, TARGET_TF_MINUTES)

    app.run_polling()


if __name__ == "__main__":
    main()
