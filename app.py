import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import datetime
import requests
import plotly.graph_objects as go
from signal_engine import generate_signals_multi, backtest_mock
from telegram_alert import send_telegram_message, log_trade

# ------------------- Configuration -------------------
st.set_page_config(page_title="📈 Option Signal Generator", layout="wide")
st.title("📊 Automated Options Signal Generator")

# 🔁 Auto-refresh entire page every 10 minutes
st_autorefresh(interval=600000, limit=None, key="main_refresh")

# ------------------- Sidebar -------------------
st.sidebar.header("🔧 Signal Configuration")
index = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
strike_type = st.sidebar.radio("Strike Type", ["ATM", "ITM", "OTM"])
expiry_date = st.sidebar.date_input("Select Expiry Date", datetime.date.today())
auto_send = st.sidebar.checkbox("✅ Auto-Send to Telegram", value=True)

# ------------------- Signal Generator -------------------
if st.sidebar.button("🚀 Generate Signals"):
    with st.spinner("⏳ Analyzing strategies..."):
        signals_df = generate_signals_multi(index, strike_type, expiry_date)

        if not signals_df.empty:
            st.success(f"✅ {len(signals_df)} Signals Generated!")

            # Show signals by Premium Band
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

        # Backtest Summary
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

# ------------------- Real-Time Premium Chart Section -------------------
st.markdown("## 📈 Real-Time Option Premium Chart (Live Market Only)")

# Refresh every 5 min for this section
st_autorefresh(interval=300000, limit=None, key="chart_refresh")

# Option Chart Inputs
st.subheader("🔍 Chart Configuration")
chart_index = st.selectbox("Chart Index", ["NIFTY", "BANKNIFTY"])
option_type = st.radio("Option Type", ["CE", "PE"], horizontal=True)
chart_strike = st.number_input("Strike Price", min_value=10000, max_value=55000, step=50)
chart_expiry = st.date_input("Expiry Date", value=datetime.date.today())

# Check if market is open
now = datetime.datetime.now()
is_market_live = now.weekday() < 5 and datetime.time(9, 15) <= now.time() <= datetime.time(15, 30)

def get_option_premium_chart_data(symbol, strike, expiry, opt_type):
    try:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        response = session.get(url, headers=headers)
        data = response.json()

        rows = data["records"]["data"]
        for row in rows:
            if row.get("strikePrice") == strike:
                option = row.get(opt_type, {})
                if option.get("expiryDate") == expiry.strftime("%d-%b-%Y"):
                    return option.get("lastPrice")

        return None
    except Exception as e:
        st.error(f"Data error: {e}")
        return None

# Plot chart if market is live
if is_market_live:
    st.success("📡 Market is live. Fetching real-time premiums...")
    key = f"{chart_index}_{option_type}_{chart_strike}_{chart_expiry}"
    if "price_log" not in st.session_state:
        st.session_state.price_log = {}

    price = get_option_premium_chart_data(chart_index, chart_strike, chart_expiry, option_type)
    if price:
        st.session_state.price_log.setdefault(key, []).append((now, price))
        df_chart = pd.DataFrame(st.session_state.price_log[key], columns=["Time", "Premium"])
        fig = go.Figure(data=go.Scatter(x=df_chart["Time"], y=df_chart["Premium"], mode="lines+markers"))
        fig.update_layout(title=f"{chart_index} {chart_strike} {option_type} Premium", xaxis_title="Time", yaxis_title="Premium")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Could not fetch premium. Try a different strike or expiry.")
else:
    st.info("📴 Market is closed. Chart will update during live hours (Mon–Fri, 9:15–15:30).")
