#!/usr/bin/env python3
"""Send a notification to Telegram.

Usage:
    python3 send_notification.py "Your message here"
    python3 send_notification.py "Morning briefing" --topic work

Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment or
.datacore/env/.env file.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Use Hermes venv python-telegram-bot
HERMES_VENV = Path.home() / ".hermes" / "hermes-agent" / "venv" / "lib" / "python3.11" / "site-packages"
if str(HERMES_VENV) not in sys.path:
    sys.path.insert(0, str(HERMES_VENV))

try:
    from telegram import Bot
except ImportError:
    print("Error: python-telegram-bot not available. Install with:")
    print("  uv pip install --python ~/.hermes/hermes-agent/venv/bin/python python-telegram-bot")
    sys.exit(1)


def load_env_file():
    env_path = Path.home() / "Data" / ".datacore" / "env" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v.strip().strip('"').strip("'"))


async def send_message(text: str, bot_token: str = None, chat_id: str = None) -> dict:
    load_env_file()
    bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not set"}
    if not chat_id:
        return {"ok": False, "error": "TELEGRAM_CHAT_ID not set"}

    try:
        bot = Bot(token=bot_token)
        message = await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        return {
            "ok": True,
            "message_id": message.message_id,
            "chat_id": message.chat_id,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Send Telegram notification")
    parser.add_argument("message", help="Message text to send")
    parser.add_argument("--topic", help="Optional topic/category prefix")
    args = parser.parse_args()

    text = args.message
    if args.topic:
        text = f"*{args.topic}*\n{text}"

    # Default signature as Tris (bot identity)
    if "\n\n— from" not in text and not text.endswith("— from Tris"):
        text += "\n\n— from Tris"

    result = asyncio.run(send_message(text))
    import json
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
