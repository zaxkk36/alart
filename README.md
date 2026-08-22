[Uploading README.md…]()
# RSI Cross Alert Bot

Telegram bot for a custom RSI(7) / SMA(14)-of-RSI entry setup on Binance
USDT-M Futures, 45-minute timeframe.

## Strategy

- **Long:** RSI(7) crosses above its 14-period SMA, while both RSI and the
  SMA are below 50 at that candle's close.
- **Short:** RSI(7) crosses below its 14-period SMA, while both RSI and the
  SMA are above 50 at that candle's close.
- Timeframe: 45 minutes (built by aggregating 3x native 15m Binance candles,
  since Binance has no native 45m interval).

## Watchlists

- **Important coins** — checked automatically every 45m, alerts pushed to
  your Telegram chat with no action needed. Edit the `IMPORTANT_COINS` list
  in `config.py` to change these.
- **Watchlist coins** — only checked when you send `/check` to the bot in
  Telegram. Edit `WATCHLIST_COINS` in `config.py` to change these.

## Setup

1. **Create a Telegram bot**
   - Message [@BotFather](https://t.me/BotFather) on Telegram, `/newbot`,
     follow the prompts, copy the token it gives you.
2. **Get your chat ID**
   - Message your new bot anything, then visit
     `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and
     find `"chat":{"id": ...}` in the response. That number is your
     `TELEGRAM_CHAT_ID`.
3. **Local test (optional)**
   ```bash
   cp .env.example .env   # fill in your real values
   pip install -r requirements.txt
   export $(cat .env | xargs)   # or use a tool like python-dotenv
   python main.py
   ```

## Deploy to Railway

1. Push this folder to a GitHub repo.
2. In Railway: New Project → Deploy from GitHub repo → select the repo.
3. Railway will detect the `Procfile` and run it as a worker.
4. In the Railway project's **Variables** tab, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Deploy. Check the logs — you should see
   `First scheduled check at ... UTC, then every 45m`.
6. In Telegram, message your bot `/start` to confirm it's alive, and
   `/check` any time to scan the watchlist coins on demand.

## Notes / things to know

- Signals are deduplicated per symbol+candle in `state.json`, so the bot
  won't spam the same signal twice even across restarts (as long as
  `state.json` persists — on Railway, add a volume if you want this to
  survive redeploys; otherwise it just resets, which only risks one
  duplicate alert after a redeploy).
- This is currently **break-only** (RSI crosses its MA, both sides of 50) —
  no re-touch/retest requirement, per your last confirmation. That can be
  added as a stricter variant later.
- XAUUSDT and LITUSDT are treated as their Binance Futures listings as
  given — double check the exact symbol spelling on Binance Futures matches
  before going live, since a typo'd symbol will just fail silently in logs.
