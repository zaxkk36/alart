# RSI vs MA Snapshot Bot

Telegram bot for checking RSI(7) vs its 14-period SMA on Binance USDT-M
Futures, 45-minute timeframe. **On-demand only — no auto alerts.**

## Strategy reference

- RSI(7), SMA(14) of RSI, 45m timeframe.
- RSI **above** its MA → long watch.
- RSI **below** its MA → short watch.
- "In zone ✅" also shown when the values additionally sit on the correct
  side of 50 (below 50 for a long watch, above 50 for a short watch) —
  matching the original entry filter, shown as a bonus signal, not a gate.

## Commands

- `/rsi` — snapshot of the **important coins**: BTCUSDT, ETHUSDT, BNBUSDT,
  SOLUSDT, LITUSDT, ZECUSDT, HYPEUSDT, XAUUSDT
- `/ma` — snapshot of the **watchlist coins**: 1000PEPEUSDT, WIFUSDT,
  WLDUSDT, FARTCOINUSDT, PENGUUSDT, ENAUSDT, TAOUSDT

Edit `IMPORTANT_COINS` / `WATCHLIST_COINS` in `config.py` to change either
list.

## Setup

1. **Create a Telegram bot**
   - Message [@BotFather](https://t.me/BotFather), `/newbot`, follow the
     prompts, copy the token.
2. **Local test (optional)**
   ```bash
   cp .env.example .env   # fill in your real token
   pip install -r requirements.txt
   export $(cat .env | xargs)
   python main.py
   ```

## Deploy to Railway

1. Push this folder to a GitHub repo.
2. Railway: New Project → Deploy from GitHub repo → select the repo.
3. Railway detects the `Procfile` and runs it as a worker.
4. In Railway's **Variables** tab, add `TELEGRAM_BOT_TOKEN`.
5. Deploy, check logs for "Bot starting (on-demand only, no scheduler)...".
6. In Telegram, `/start` to confirm it's alive, then `/rsi` or `/ma`.

## Notes

- No `TELEGRAM_CHAT_ID` needed anymore — the bot replies directly in
  whichever chat sent the command.
- No state/persistence needed — every check is a fresh snapshot, no
  duplicate-alert tracking required since there are no auto alerts.
- This reports the **current RSI-vs-MA position**, not a cross event —
  it's meant for you to eyeball and decide, per your workflow.
