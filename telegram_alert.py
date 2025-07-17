import requests
import streamlit as st
import csv
from datetime import datetime
import os

BOT_TOKEN = st.secrets["BOT_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        print("Telegram response:", response.status_code, response.text)  # Logs
        return response.status_code == 200
    except Exception as e:
        print("Telegram send failed:", e)
        return False

# ✅ Trade Logger
LOG_FILE = "trade_log.csv"

def log_trade(row):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Signal", "Entry", "Target", "Stop Loss", "Strategy", "Expiry"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            row["Signal"],
            row["Entry"],
            row["Target"],
            row["Stop Loss"],
            row["Strategy"],
            row["Expiry"]
        ])
