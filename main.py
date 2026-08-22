import logging
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    IMPORTANT_COINS,
    WATCHLIST_COINS,
    TARGET_TF_MINUTES,
    CLOSE_BUFFER_SECONDS,
)
from market_data import get_45m_candles
from indicators import add_indicators, detect_signal
from state import load_state, save_state, already_alerted, mark_alerted

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("rsi-bot")


def format_signal_message(symbol: str, signal: dict) -> str:
    arrow = "🟢 LONG" if signal["side"] == "LONG" else "🔴 SHORT"
    return (
        f"{arrow} setup — {symbol}\n"
        f"Candle: {signal['candle_time']} UTC\n"
        f"Close: {signal['close']:.6g}\n"
        f"RSI: {signal['rsi']:.2f}  |  RSI-MA: {signal['rsi_ma']:.2f}"
    )


def check_symbol(symbol: str, state: dict) -> str | None:
    """Fetch data, run indicators, return a formatted message if a NEW signal fired."""
    try:
        candles = get_45m_candles(symbol)
    except Exception as e:
        log.error("Failed to fetch candles for %s: %s", symbol, e)
        return None

    if len(candles) < 20:
        log.warning("Not enough 45m candles yet for %s (%d)", symbol, len(candles))
        return None

    candles = add_indicators(candles)
    signal = detect_signal(candles)
    if not signal:
        return None

    candle_iso = signal["candle_time"].isoformat()
    if already_alerted(state, symbol, candle_iso):
        return None  # already alerted this exact candle before

    mark_alerted(state, symbol, candle_iso)
    return format_signal_message(symbol, signal)


async def auto_check_important(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs on the 45m schedule, checks IMPORTANT_COINS, pushes any signals."""
    log.info("Running scheduled check on important coins...")
    state = load_state()
    messages = []
    for symbol in IMPORTANT_COINS:
        msg = check_symbol(symbol, state)
        if msg:
            messages.append(msg)
    save_state(state)

    if not messages:
        log.info("No signals this cycle.")
        return

    for msg in messages:
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/check — on-demand scan of the less-important watchlist."""
    await update.message.reply_text("Checking watchlist coins, one sec...")
    state = load_state()
    messages = []
    for symbol in WATCHLIST_COINS:
        msg = check_symbol(symbol, state)
        if msg:
            messages.append(msg)
    save_state(state)

    if not messages:
        await update.message.reply_text("No setups on the watchlist right now.")
        return

    for msg in messages:
        await update.message.reply_text(msg)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "RSI alert bot running.\n"
        "- Important coins are auto-checked every 45m.\n"
        "- Send /check to scan the watchlist coins on demand."
    )


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
    app.add_handler(CommandHandler("check", cmd_check))

    start_time = next_45m_boundary(datetime.now(timezone.utc))
    app.job_queue.run_repeating(
        auto_check_important,
        interval=timedelta(minutes=TARGET_TF_MINUTES),
        first=start_time,
        name="important_coins_check",
    )
    log.info("First scheduled check at %s UTC, then every %dm", start_time, TARGET_TF_MINUTES)

    app.run_polling()


if __name__ == "__main__":
    main()
