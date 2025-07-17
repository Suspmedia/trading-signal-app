import requests
import streamlit as st
import csv
from datetime import datetime
import os

# Load from secrets
BOT_TOKEN = st.secrets["BOT_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

# ✅ Send Telegram Message (Plain Text Mode)
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message  # No parse_mode for plain text
    }
    try:
        response = requests.post(url, data=payload)
        st.write("Telegram Status Code:", response.status_code)
        st.write("Telegram Response:", response.text)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Telegram send failed: {e}")
        return False

# ✅ Log Sent Trade Signal to CSV
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
