import streamlit as st
import pandas as pd
import datetime
from signal_engine import generate_signals
from telegram_alert import send_telegram_message, log_trade

st.set_page_config(page_title="Trading Signal App", layout="wide")
st.title("📈 Options Trading Signal Generator")

st.sidebar.header("🔍 Configuration")
index = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
strategy = st.sidebar.radio("Select Strategy", ["Safe", "Min Investment", "Max Profit"])
strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
expiry_date = st.sidebar.date_input("Select Expiry Date", datetime.date.today())

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
                        log_trade(row)
                    else:
                        st.error("❌ Failed to send to Telegram.")
        else:
            st.warning("⚠️ No strong signals found.")

# Trade History Section
st.header("📊 Trade History")
try:
    df_log = pd.read_csv("trade_log.csv")
    st.dataframe(df_log, use_container_width=True)
    total_trades = len(df_log)
    st.info(f"✅ Total Trades Logged: {total_trades}")
except FileNotFoundError:
    st.warning("No trade history found yet.")
