# RSI/MA Snapshot + Retest Alert Bot

Binance USDT-M Futures, RSI(7) vs its 14-period SMA, 45-minute timeframe.

## Commands (on demand, no auto-push)

- `/rsi` — snapshot of the **important coins**: BTCUSDT, ETHUSDT, BNBUSDT,
  SOLUSDT, LITUSDT, ZECUSDT, HYPEUSDT, XAUUSDT
- `/ma` — snapshot of the **watchlist coins**: 1000PEPEUSDT, WIFUSDT,
  WLDUSDT, FARTCOINUSDT, PENGUUSDT, ENAUSDT, TAOUSDT

Output format, one line per coin:
```
🟢BTCUSDT-Long
🔴SOLUSDT-Short
```
🟢 = RSI currently above its MA (long bias). 🔴 = RSI currently below its
MA (short bias). This is just the current position, not a signal event.

Edit `IMPORTANT_COINS` / `WATCHLIST_COINS` in `config.py` to change either
list.

## Retest alert (automatic, no command needed)

Runs every 45m for **every coin in both lists combined**. Two-step logic:

1. **Break** — RSI(7) crosses its MA while both are on the correct side of
   50 (long: both <50, short: both >50). This "arms" the symbol.
2. **Retest** — the bot then watches subsequent closed 45m candles:
   - Armed **LONG** → needs a **RED** candle to confirm.
   - Armed **SHORT** → needs a **GREEN** candle to confirm.
3. On confirmation, you get pushed a Telegram alert and the symbol is
   cleared. A new break (either direction) always re-arms, overwriting
   whatever was there before.

Armed state is stored in `state.json` so it survives restarts (unless
Railway wipes local disk on redeploy — worst case you lose an in-progress
arm and have to wait for the next break).

## Setup

1. **Create a Telegram bot** — message [@BotFather](https://t.me/BotFather),
   `/newbot`, copy the token.
2. **Get your chat ID** — message your bot anything, then visit
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` (replace
   `<YOUR_TOKEN>`, no angle brackets) and find `"chat":{"id": ...}`.
3. **Local test (optional)**
   ```bash
   cp .env.example .env   # fill in real values
   pip install -r requirements.txt
   export $(cat .env | xargs)
   python main.py
   ```

## Deploy to Railway

1. Push this folder to a GitHub repo.
2. Railway: New Project → Deploy from GitHub repo → select the repo.
3. Railway detects the `Procfile` and runs it as a worker.
4. In Railway's **Variables** tab, add `TELEGRAM_BOT_TOKEN` and
   `TELEGRAM_CHAT_ID`.
5. Deploy, check logs for "First retest check at ... UTC, then every 45m".
6. In Telegram: `/start`, `/rsi`, `/ma` to confirm it's alive.

## Notes

- Binance has no native 45m interval — candles are built by aggregating
  3x native 15m klines, anchored to UTC midnight.
- No cap on how long a symbol stays "armed" waiting for a retest — it'll
  wait indefinitely until either the retest candle shows up or a new break
  overwrites it. Let me know if you'd rather it expire after N candles.
