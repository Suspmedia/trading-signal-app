import streamlit as st
from streamlit_autorefresh import st_autorefresh
import datetime
import pandas as pd

from signal_engine import generate_signals_multi
from stock_engine import generate_stock_signals, get_suggested_stocks
from telegram_alert import send_telegram_message, log_trade

# Set page config
st.set_page_config(page_title="📈 Options Signal Generator", layout="wide")
st.title("📊 Automated Options Signal Generator")

# Auto-refresh every 10 minutes
st_autorefresh(interval=600000, limit=None, key="main_autorefresh")

# Tab selector
mode = st.radio("Choose Mode", ["📊 Index Options", "📦 Stock Options"])

# ---------- Index Options ----------
if mode == "📊 Index Options":
    st.sidebar.header("Index Signal Settings")
    index = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
    strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
    expiry_date = st.sidebar.date_input("Expiry Date", datetime.date.today())
    auto_send = st.sidebar.checkbox("📤 Auto-Send to Telegram", value=True)

    if st.sidebar.button("🚀 Generate Index Signals"):
        with st.spinner("Analyzing index..."):
            signals_df, index_ltp = generate_signals_multi(index, strike_type, expiry_date)
            if not signals_df.empty:
                st.success(f"✅ {len(signals_df)} Signals Found")
                st.markdown(f"**📈 Index LTP:** ₹{index_ltp}")
                for _, row in signals_df.iterrows():
                    st.write(row)

                    msg = (
                        f"🔍 Signal: {row['Signal']}\n"
                        f"📈 Index LTP: ₹{row['Index LTP']}\n"
                        f"💸 Entry: ₹{row['Entry']} | 🌟 Target: ₹{row['Target']} | 🚑 SL: ₹{row['Stop Loss']}\n"
                        f"📊 Strategy: {row['Strategy']} | 🦓 Expiry: {row['Expiry']}"
                    )
                    if auto_send:
                        sent = send_telegram_message(msg)
                        if sent:
                            log_trade(row)
                        else:
                            st.error("❌ Failed to send to Telegram")
            else:
                st.warning("⚠️ No strong signals found.")

# ---------- Stock Options ----------
elif mode == "📦 Stock Options":
    st.sidebar.header("Stock Signal Settings")
    expiry_date = st.sidebar.date_input("Expiry Date", datetime.date.today())
    strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
    strategy = st.sidebar.radio("Strategy", ["Safe", "Min Investment", "Max Profit", "Reversal", "Breakout"])
    auto_send = st.sidebar.checkbox("📤 Auto-Send to Telegram", value=True)

    # Smart suggestions
    st.subheader("🧐 Suggested Stocks with Signals")
    with st.spinner("Scanning F&O stocks..."):
        suggested = get_suggested_stocks(expiry_date, strategy, strike_type)
        suggested_symbols = [sym for sym, df in suggested]

    selected_stock = st.selectbox("Select a Suggested Stock", suggested_symbols)
    manual_symbol = st.text_input("Or search manually (e.g., RELIANCE, BHEL)")

    if st.button("🚀 Generate Stock Signal"):
        stock_to_check = manual_symbol.strip().upper() if manual_symbol else selected_stock
        with st.spinner(f"Analyzing {stock_to_check}..."):
            signal_df = generate_stock_signals(stock_to_check, strategy, strike_type, expiry_date)
            if not signal_df.empty:
                st.success("✅ Signal Generated")
                st.write(f"📈 Stock LTP: ₹{signal_df.iloc[0]['Stock LTP']}")
                st.dataframe(signal_df, use_container_width=True)

                row = signal_df.iloc[0]
                msg = (
                    f"🔍 Signal: {row['Signal']}\n"
                    f"📈 Stock LTP: ₹{row['Stock LTP']}\n"
                    f"💸 Entry: ₹{row['Entry']} | 🌟 Target: ₹{row['Target']} | 🚑 SL: ₹{row['Stop Loss']}\n"
                    f"📊 Strategy: {row['Strategy']} | 🦓 Expiry: {row['Expiry']}"
                )

                if auto_send:
                    sent = send_telegram_message(msg)
                    if sent:
                        log_trade(row)
                    else:
                        st.error("❌ Failed to send to Telegram")
            else:
                st.warning("⚠️ No valid signal or option chain for this stock.")

# ---------- Trade History ----------
st.markdown("## 📘 Trade History")
try:
    df_log = pd.read_csv("trade_log.csv")
    st.dataframe(df_log, use_container_width=True)
    st.info(f"📌 Total Trades Logged: {len(df_log)}")
except FileNotFoundError:
    st.warning("No trade history yet.")

# ---------- Disclaimer Footer ----------
st.markdown("""
<hr style='border:1px solid #999999;' />

<div style='text-align: center; color: gray; font-size: 14px;'>
🔐 <b>Disclaimer:</b> This tool is for personal research and educational purposes only.<br>
It is not financial advice. The creator is not a SEBI-registered advisor. Use at your own risk.
</div>
""", unsafe_allow_html=True)
