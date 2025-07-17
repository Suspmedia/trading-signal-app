import requests
import streamlit as st
import csv
from datetime import datetime
import os

# ✅ Load from Streamlit Secrets
BOT_TOKEN = st.secrets["BOT_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

# ✅ Send Telegram Message (Markdown + JSON method)
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"  # You can switch to "HTML" if needed
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            st.success("✅ Sent to Telegram")
            return True
        else:
            st.error(f"❌ Telegram failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        st.error(f"Telegram Exception: {e}")
        return False

# ✅ Log Trade to CSV
def log_trade(row):
    file_path = "trade_log.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="") as file:
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
