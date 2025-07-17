import streamlit as st
import pandas as pd
import datetime
from signal_engine import generate_signals_multi, backtest_mock
from telegram_alert import send_telegram_message, log_trade

st.set_page_config(page_title="📈 Options Signal Generator", layout="wide")
st.title("📊 Automated Options Signal Engine")

# Sidebar Inputs
st.sidebar.header("🔧 Configuration")
index = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
expiry_date = st.sidebar.date_input("Select Expiry Date", datetime.date.today())

# Generate Signals
if st.sidebar.button("🚀 Generate All Strategies"):
    with st.spinner("🔍 Generating signals for all 5 strategies..."):
        signals_df = generate_signals_multi(index, strike_type, expiry_date)

        if not signals_df.empty:
            st.success("✅ Strategies Generated!")
            st.subheader("📌 Signals Grouped by Premium Band")

            # Show grouped signals
            for band in signals_df["Premium Band"].unique():
                group_df = signals_df[signals_df["Premium Band"] == band]
                st.markdown(f"### 💰 Premium Band: `{band}`")
                st.dataframe(group_df, use_container_width=True)

                for i, row in group_df.iterrows():
                    msg = (
                        f"🔍 Signal: {row['Signal']}\n"
                        f"💸 Entry: ₹{row['Entry']} | 🎯 Target: ₹{row['Target']} | 🛑 SL: ₹{row['Stop Loss']}\n"
                        f"📊 Strategy: {row['Strategy']} ({row['Reason']})\n"
                        f"📅 Expiry: {row['Expiry']} | 💰 Band: {row['Premium Band']}"
                    )
                    if st.button(f"📤 Send to Telegram: {row['Signal']}", key=f"btn_{i}"):
                        sent = send_telegram_message(msg)
                        if sent:
                            st.success("✅ Sent to Telegram!")
                            log_trade(row)
                        else:
                            st.error("❌ Failed to send.")

            # Show Backtest
            st.markdown("### 🧪 Backtest Summary")
            backtest_df = backtest_mock(signals_df)
            st.dataframe(backtest_df, use_container_width=True)

        else:
            st.warning("⚠️ No strong signals found with current indicators or volume filters.")

# Trade History Section
st.markdown("## 🧾 Trade History Log")
try:
    df_log = pd.read_csv("trade_log.csv")
    st.dataframe(df_log, use_container_width=True)
    st.info(f"📌 Total Trades Logged: {len(df_log)}")
except FileNotFoundError:
    st.warning("No trade history yet.")
