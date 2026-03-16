# Cuaresma Bot

Telegram bot that sends a daily Catholic prayer and Bible reading in Spanish during Cuaresma (Lent). It uses the Reina‑Valera 1909 Bible (RV1909) in JSON format and a 40‑day desert reading plan.

## Features

- `/start` – subscribe and receive today’s prayer + Bible reading.
- `/stop` – unsubscribe from the daily messages.
- Scheduled daily message at a fixed time using Telegram JobQueue.
- Full readings pulled from `rv_1909.json` using Spanish book names.
- Prayers and reading plan stored in JSON files for easy editing.
- Deployed as a long‑running background service on **Render**.

## Project Structure

- `cuaresma_bot.py` – main Telegram bot logic, handlers, and scheduler.
- `data/rv_1909.json` – RV1909 Bible text (book / chapter / verse entries).
- `data/cuaresma_readings.json` – 40‑day desert reading plan (day → references).
- `data/prayers.json` – full texts of the prayers used by the bot.
- `requirements.txt` – Python dependencies.
- `.env` – local environment variables (not committed), contains `TELEGRAM_TOKEN`.
- `.gitignore` – ignores virtualenv, `.env`, and OS‑specific files.

## Local Setup

1. **Clone and create virtualenv**

   ```bash
   git clone https://github.com/<your-user>/cuaresma-bot.git
   cd cuaresma-bot
   python3 -m venv .venv
   source .venv/bin/activate

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**

```bash
echo "TELEGRAM_TOKEN=8668092835:AAHx2ZDvhPXffnQtZkLxDkcbtZ6gz4MIIik" > .env / if you wanna use my bot

```
4. **Prepare data files**

```bash
ls data
# rv_1909.json
# cuaresma_readings.json
# prayers.json
```
5. **Run the bot**

```bash
python cuaresma_bot.py
