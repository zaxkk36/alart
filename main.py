import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import (
    TELEGRAM_BOT_TOKEN,
    IMPORTANT_COINS,
    WATCHLIST_COINS,
)
from market_data import get_45m_candles
from indicators import add_indicators, get_snapshot

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("rsi-bot")


def format_snapshot_line(symbol: str, snap: dict) -> str:
    zone = "✅ in zone" if snap["in_zone"] else "— outside 50-zone"
    arrow = "🟢" if snap["position"] == "ABOVE" else "🔴"
    return (
        f"{arrow} {symbol}: RSI {snap['rsi']:.1f} vs MA {snap['rsi_ma']:.1f} "
        f"→ {snap['bias']} {zone}"
    )


def snapshot_symbol(symbol: str) -> str:
    """Fetch data, compute indicators, return one formatted line (or an error note)."""
    try:
        candles = get_45m_candles(symbol)
    except Exception as e:
        log.error("Failed to fetch candles for %s: %s", symbol, e)
        return f"⚠️ {symbol}: failed to fetch data ({e})"

    if len(candles) < 20:
        return f"⚠️ {symbol}: not enough candle history yet"

    candles = add_indicators(candles)
    snap = get_snapshot(candles)
    if not snap:
        return f"⚠️ {symbol}: indicators not ready yet"

    return format_snapshot_line(symbol, snap)


async def cmd_rsi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/rsi — snapshot of the IMPORTANT coins list."""
    await update.message.reply_text("Checking important coins...")
    lines = [snapshot_symbol(sym) for sym in IMPORTANT_COINS]
    await update.message.reply_text("📊 Important coins (45m)\n\n" + "\n".join(lines))


async def cmd_ma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ma — snapshot of the WATCHLIST (less important) coins list."""
    await update.message.reply_text("Checking watchlist coins...")
    lines = [snapshot_symbol(sym) for sym in WATCHLIST_COINS]
    await update.message.reply_text("📊 Watchlist coins (45m)\n\n" + "\n".join(lines))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "RSI/MA snapshot bot.\n"
        "No auto alerts — check on demand:\n"
        "/rsi — important coins\n"
        "/ma — watchlist coins"
    )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Set the TELEGRAM_BOT_TOKEN environment variable.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rsi", cmd_rsi))
    app.add_handler(CommandHandler("ma", cmd_ma))

    log.info("Bot starting (on-demand only, no scheduler)...")
    app.run_polling()


if __name__ == "__main__":
    main()
