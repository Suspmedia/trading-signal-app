# app.py
import streamlit as st
import pandas as pd
import datetime
from signal_engine import generate_signals
from telegram_alert import send_telegram_message

# --- App Config ---
st.set_page_config(page_title="Trading Signal App", layout="wide")
st.title("📈 Options Trading Signal Generator")

# --- Sidebar Inputs ---
st.sidebar.header("🔍 Configuration")

index = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
strategy = st.sidebar.radio("Select Strategy", ["Safe", "Min Investment", "Max Profit"])
strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
expiry_date = st.sidebar.date_input("Select Expiry Date", datetime.date.today())

# --- Generate Signal Button ---
if st.sidebar.button("Generate Signals"):
    with st.spinner("🔄 Analyzing data..."):
        signals_df = generate_signals(index, strategy, strike_type, expiry_date)

        if not signals_df.empty:
            st.success("✅ Signals Generated!")
            st.dataframe(signals_df, use_container_width=True)

            for i, row in signals_df.iterrows():
                if st.button(f"📤 Send to Telegram: {row['Signal']}", key=f"telegram_btn_{i}"):
                    msg = (
                        f"🔍 *Signal:* {row['Signal']}\n"
                        f"💸 *Entry:* {row['Entry']} | 🎯 *Target:* {row['Target']} | 🛑 *SL:* {row['Stop Loss']}\n"
                        f"📊 *Strategy:* {row['Strategy']} | 🕓 *Expiry:* {row['Expiry']}"
                    )
                    sent = send_telegram_message(msg)
                    if sent:
                        st.success("✅ Signal sent to Telegram!")
                    else:
                        st.error("❌ Failed to send to Telegram.")
        else:
            st.warning("⚠️ No strong signals found. Try again later or change filters.")

# --- About ---
st.sidebar.markdown("---")
st.sidebar.caption("Built using 🐍 Python + 🚀 Streamlit\nContact: @your_bot_name")