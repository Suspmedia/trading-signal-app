import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import datetime
from signal_engine import generate_signals_multi, backtest_mock
from telegram_alert import send_telegram_message, log_trade

# ------------------- Configuration -------------------
st.set_page_config(page_title="📈 Auto Options Signal Bot", layout="wide")
st.title("📊 Automated Options Signal Generator")

# 🔁 Auto-refresh every 10 minutes (600,000 ms)
st_autorefresh(interval=600000, limit=None, key="auto_refresh")

# ------------------- Sidebar -------------------
st.sidebar.header("🔧 Configuration")
index = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
expiry_date = st.sidebar.date_input("Select Expiry Date", datetime.date.today())
auto_send = st.sidebar.checkbox("✅ Auto-Send to Telegram", value=True)

# ------------------- Signal Generation -------------------
if st.sidebar.button("🚀 Generate Signals"):
    with st.spinner("⏳ Analyzing strategies..."):
        signals_df = generate_signals_multi(index, strike_type, expiry_date)

        if not signals_df.empty:
            st.success(f"✅ {len(signals_df)} Signals Generated!")

            # 📦 Group by Premium Band
            for band in signals_df["Premium Band"].unique():
                band_df = signals_df[signals_df["Premium Band"] == band]
                st.markdown(f"### 💰 Premium Band: `{band}`")
                st.dataframe(band_df, use_container_width=True)

                for i, row in band_df.iterrows():
                    msg = (
                        f"🔍 Signal: {row['Signal']}\n"
                        f"💸 Entry: ₹{row['Entry']} | 🎯 Target: ₹{row['Target']} | 🛑 SL: ₹{row['Stop Loss']}\n"
                        f"📊 Strategy: {row['Strategy']} ({row.get('Reason', '-')})\n"
                        f"📅 Expiry: {row['Expiry']} | 💰 Band: {row['Premium Band']}"
                    )
                    
                    if auto_send:
                        sent = send_telegram_message(msg)
                        if sent:
                            st.success(f"📤 Sent: {row['Signal']}")
                            log_trade(row)
                        else:
                            st.error(f"❌ Failed to send: {row['Signal']}")

        else:
            st.warning("⚠️ No strong signals found with current strategy and filters.")

        # ------------------- Backtest Results -------------------
        st.markdown("### 🧪 Backtest Summary")
        bt_summary = backtest_mock(signals_df)
        st.dataframe(bt_summary, use_container_width=True)

# ------------------- Trade History -------------------
st.markdown("## 📘 Trade History")
try:
    df_log = pd.read_csv("trade_log.csv")
    st.dataframe(df_log, use_container_width=True)
    st.info(f"📌 Total Trades Logged: {len(df_log)}")
except FileNotFoundError:
    st.warning("No trade history yet.")
