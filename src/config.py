import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ متغير BOT_TOKEN غير موجود. أضفه في GitHub Secrets")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
STATE_FILE = "state.json"
MAX_FILE_SIZE = 45 * 1024 * 1024
