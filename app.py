import streamlit as st
import pandas as pd
import datetime
from streamlit_autorefresh import st_autorefresh
from signal_engine import generate_signals_multi
from telegram_alert import send_telegram_message, log_trade

# Auto-refresh every 10 minutes
st_autorefresh(interval=600000, key="auto-refresh")

st.set_page_config(page_title="Trading Signal App", layout="wide")
st.title("📈 Options Trading Signal Generator")

# Sidebar Controls
st.sidebar.header("🔍 Configuration")
index = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
expiry_date = st.sidebar.date_input("Select Expiry Date", datetime.date.today())

# Generate Signals
if st.sidebar.button("Generate Signals"):
    with st.spinner("🔄 Analyzing strategies..."):
        signals_df = generate_signals_multi(index, strike_type, expiry_date)
        if not signals_df.empty and "No strong signal" not in signals_df["Signal"].iloc[0]:
            st.success("✅ Signals Generated!")
            st.dataframe(signals_df, use_container_width=True)

            selected_signal = st.selectbox("📤 Choose a signal to send to Telegram", signals_df["Signal"])
            if st.button("Send Selected Signal"):
                row = signals_df[signals_df["Signal"] == selected_signal].iloc[0]
                msg = (
                    f"*Signal:* {row['Signal']}\n"
                    f"*Entry:* {row['Entry']} | *Target:* {row['Target']} | *SL:* {row['Stop Loss']}\n"
                    f"*Strategy:* {row['Strategy']} | *Expiry:* {row['Expiry']}"
                )
                sent = send_telegram_message(msg)
                if sent:
                    st.success("✅ Signal sent to Telegram!")
                    log_trade(row)
                else:
                    st.error("❌ Failed to send to Telegram.")
        else:
            st.warning("⚠️ No strong signals found.")

# Trade History
st.header("📊 Trade History")
try:
    df_log = pd.read_csv("trade_log.csv")
    st.dataframe(df_log, use_container_width=True)
    st.info(f"✅ Total Trades Logged: {len(df_log)}")
except FileNotFoundError:
    st.warning("No trade history found yet.")
