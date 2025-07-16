# telegram_alert.py

import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "7623965196:AAGTNQwy6uYM76BIn5WQ_mv5Ae4MJ3hRlzk")
CHAT_ID = os.getenv("CHAT_ID", "521053521")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        return response.status_code == 200
    except Exception as e:
        print("Telegram send failed:", e)
        return False