import streamlit as st
from streamlit_autorefresh import st_autorefresh
import datetime
import pandas as pd

from signal_engine import generate_signals_multi
from stock_engine import generate_stock_signals, NIFTY_50
from telegram_alert import send_telegram_message, log_trade

# ----------------- Page Setup -----------------
st.set_page_config(page_title="📈 Option Signal Generator", layout="wide")
st.title("📊 Automated Options Signal Generator")

# 🔁 Auto-refresh every 10 minutes
st_autorefresh(interval=600000, limit=None, key="main_autorefresh")

# ----------------- Mode Selector -----------------
mode = st.radio("Choose Mode", ["📊 Index Options", "📦 Stock Options"])

# ----------------- Index Option Section -----------------
if mode == "📊 Index Options":
    st.sidebar.header("🧮 Index Signal Settings")
    index = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
    strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
    expiry_date = st.sidebar.date_input("Select Expiry Date", datetime.date.today())
    auto_send = st.sidebar.checkbox("📤 Auto-Send to Telegram", value=True)

    if st.sidebar.button("🚀 Generate Index Signals"):
        with st.spinner("🔍 Analyzing index..."):
            signals_df = generate_signals_multi(index, strike_type, expiry_date)

            if not signals_df.empty:
                st.success(f"✅ {len(signals_df)} Signals Generated")

                for i, row in signals_df.iterrows():
                    st.markdown(f"### 📌 {row['Signal']}")
                    st.write(row)

                    msg = (
                        f"🔍 Signal: {row['Signal']}\n"
                        f"💸 Entry: ₹{row['Entry']} | 🎯 Target: ₹{row['Target']} | 🛑 SL: ₹{row['Stop Loss']}\n"
                        f"📊 Strategy: {row['Strategy']} | 🕓 Expiry: {row['Expiry']}"
                    )

                    if auto_send:
                        sent = send_telegram_message(msg)
                        if sent:
                            st.success("📤 Sent to Telegram")
                            log_trade(row)
                        else:
                            st.error("❌ Failed to send to Telegram")
            else:
                st.warning("⚠️ No strong signals found.")

# ----------------- Stock Option Section -----------------
elif mode == "📦 Stock Options":
    st.sidebar.header("📦 Stock Signal Settings")
    stock = st.sidebar.selectbox("Select Stock (NIFTY 50)", sorted(NIFTY_50))
    strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
    expiry_date = st.sidebar.date_input("Select Expiry Date", datetime.date.today())
    strategy = st.sidebar.radio("Strategy", ["Safe", "Min Investment", "Max Profit", "Reversal", "Breakout"])
    auto_send = st.sidebar.checkbox("📤 Auto-Send to Telegram", value=True)

    if st.sidebar.button("🚀 Generate Stock Signal"):
        with st.spinner(f"Analyzing {stock}..."):
            signal_df = generate_stock_signals(stock, strategy, strike_type, expiry_date)

            if not signal_df.empty:
                st.success("✅ Signal Generated")
                st.dataframe(signal_df, use_container_width=True)

                row = signal_df.iloc[0]
                msg = (
                    f"🔍 Signal: {row['Signal']}\n"
                    f"💸 Entry: ₹{row['Entry']} | 🎯 Target: ₹{row['Target']} | 🛑 SL: ₹{row['Stop Loss']}\n"
                    f"📊 Strategy: {row['Strategy']} | 🕓 Expiry: {row['Expiry']}"
                )

                if auto_send:
                    sent = send_telegram_message(msg)
                    if sent:
                        st.success("📤 Sent to Telegram")
                        log_trade(row)
                    else:
                        st.error("❌ Failed to send to Telegram")
            else:
                st.warning("⚠️ No strong signals found.")

# ----------------- Trade History -----------------
st.markdown("## 📘 Trade History")
try:
    df_log = pd.read_csv("trade_log.csv")
    st.dataframe(df_log, use_container_width=True)
    st.info(f"📌 Total Trades Logged: {len(df_log)}")
except FileNotFoundError:
    st.warning("No trade history yet.")
