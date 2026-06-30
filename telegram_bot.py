import requests
from dotenv import load_dotenv
load_dotenv()
import os
import hashlib
import redis

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
REDIS_URL = os.getenv('REDIS_URL')


r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

DUPLICATE_SUPPRESS_SECONDS = 60


def _was_recently_sent(message):
    """Atomic check-and-set, same pattern as the msg_id dedup in gmail.py.
    Returns True if this exact text was already sent recently (so this call
    should be skipped), False if this call just claimed it and should send."""
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
    claimed = r.set(f"telegram_sent:{digest}", "1", nx=True, ex=DUPLICATE_SUPPRESS_SECONDS)
    return not claimed


def send_message(message):
    """Send a message to Telegram bot, suppressing exact-duplicate sends
    that happen within DUPLICATE_SUPPRESS_SECONDS of each other."""

    if _was_recently_sent(message):
        print(f"[TELEGRAM] duplicate suppressed: {message[:40]!r}...")
        return {"ok": False, "suppressed": True}

    print(f"[TELEGRAM] sending message: {message[:40]!r}...")

    url=f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(url, json=payload)
    return response.json()