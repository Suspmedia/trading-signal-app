import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
import requests
from datetime import datetime, timedelta

# ---------------------- OI + LTP SCRAPER ----------------------
def get_oi_levels(index="NIFTY"):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={index}"
        response = session.get(url, headers=headers)
        data = response.json()
        strike_data = []
        for record in data["records"]["data"]:
            strike = record.get("strikePrice")
            ce = record.get("CE", {})
            pe = record.get("PE", {})
            ce_oi = ce.get("openInterest", 0)
            pe_oi = pe.get("openInterest", 0)
            strike_data.append({"strike": strike, "CE_OI": ce_oi, "PE_OI": pe_oi})
        df = pd.DataFrame(strike_data)
        max_pe = df.loc[df["PE_OI"].idxmax()]
        max_ce = df.loc[df["CE_OI"].idxmax()]
        return {
            "support_strike": int(max_pe["strike"]),
            "resistance_strike": int(max_ce["strike"])
        }
    except Exception as e:
        print("OI Error:", e)
        return {"support_strike": None, "resistance_strike": None}

def get_option_chain_ltp(index="NIFTY"):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={index}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        response = session.get(url, headers=headers)
        data = response.json()
        strike_prices = {}
        for record in data["records"]["data"]:
            strike = record.get("strikePrice")
            ce_ltp = record.get("CE", {}).get("lastPrice")
            pe_ltp = record.get("PE", {}).get("lastPrice")
            strike_prices[strike] = {"CE": ce_ltp, "PE": pe_ltp}
        return strike_prices
    except Exception as e:
        print("LTP Fetch Error:", e)
        return {}

# ---------------------- UTILITY ----------------------
def get_symbol(index):
    return {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN"}.get(index, "^NSEI")

def fetch_data(symbol):
    df = yf.download(symbol, period="5d", interval="5m", progress=False, auto_adjust=True)
    df.dropna(inplace=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df if not df.empty else pd.DataFrame()

def calculate_indicators(df):
    df["RSI"] = RSIIndicator(close=df["Close"]).rsi()
    macd = MACD(close=df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()
    return df

def premium_band(entry):
    if entry <= 50:
        return "₹0–50"
    elif entry <= 150:
        return "₹51–150"
    else:
        return "₹151+"

def generate_signals_multi(index, strike_type, expiry_date):
    df = fetch_data(get_symbol(index))
    if df.empty:
        return pd.DataFrame()

    df = calculate_indicators(df)
    current = df.iloc[-1]
    avg_volume = df["Volume"].rolling(window=20).mean().iloc[-1]
    if current["Volume"] < 1.2 * avg_volume:
        return pd.DataFrame()

    last_price = current["Close"]
    atm_strike = round(last_price / 50) * 50
    oi_data = get_oi_levels(index)
    option_chain = get_option_chain_ltp(index)

    strategies = ["Safe", "Min Investment", "Max Profit", "Reversal", "Breakout"]
    results = []

    for strategy in strategies:
        if strategy == "Safe":
            signal = "BUY" if current["MACD"] > current["MACD_signal"] and current["Close"] > current["VWAP"] else "SELL"
            strike = oi_data["support_strike"] if signal == "BUY" else oi_data["resistance_strike"]
            reason = "OI Support/Resistance"

        elif strategy == "Min Investment":
            best_strike, min_ltp = atm_strike, float("inf")
            signal = "BUY" if current["MACD"] > current["MACD_signal"] else "SELL"
            for k, v in option_chain.items():
                ltp = v.get("CE" if signal == "BUY" else "PE")
                if ltp and 5 < ltp < min_ltp:
                    best_strike = k
                    min_ltp = ltp
            strike = best_strike
            reason = "Lowest Premium"

        elif strategy == "Max Profit":
            signal = "BUY" if current["MACD"] > current["MACD_signal"] and current["RSI"] < 60 else "SELL"
            strike = atm_strike - 50 if signal == "BUY" else atm_strike + 50
            reason = "Momentum"

        elif strategy == "Reversal":
            if current["RSI"] < 30 and current["MACD"] > current["MACD_signal"]:
                signal = "BUY"
                strike = atm_strike
                reason = "RSI Reversal Up"
            elif current["RSI"] > 70 and current["MACD"] < current["MACD_signal"]:
                signal = "SELL"
                strike = atm_strike
                reason = "RSI Reversal Down"
            else:
                continue

        elif strategy == "Breakout":
            recent_high = df["High"].rolling(window=20).max().iloc[-2]
            recent_low = df["Low"].rolling(window=20).min().iloc[-2]
            if current["Close"] > recent_high and current["MACD"] > current["MACD_signal"]:
                signal = "BUY"
                strike = atm_strike + 50
                reason = "Breakout Up"
            elif current["Close"] < recent_low and current["MACD"] < current["MACD_signal"]:
                signal = "SELL"
                strike = atm_strike - 50
                reason = "Breakout Down"
            else:
                continue

        else:
            continue

        option_type = "CE" if signal == "BUY" else "PE"
        entry = option_chain.get(strike, {}).get(option_type, round(40 + last_price % 20, 2))
        target = round(entry * 2.1, 2)
        sl = round(entry * 0.7, 2)

        results.append({
            "Signal": f"{index} {signal} {strike} {option_type}",
            "Entry": f"{entry}",
            "Target": f"{target}",
            "Stop Loss": f"{sl}",
            "Strategy": strategy,
            "Reason": reason,
            "Premium Band": premium_band(entry),
            "Expiry": expiry_date.strftime("%d %b %Y")
        })

    return pd.DataFrame(results)

# ---------------------- BACKTEST MOCKUP ----------------------
def backtest_mock(df_signals):
    results = []
    for _, row in df_signals.iterrows():
        entry = float(row["Entry"])
        target = float(row["Target"])
        sl = float(row["Stop Loss"])
        mock_price = np.random.normal(loc=entry, scale=(target - sl) / 4)
        if mock_price >= target:
            outcome = "Target Hit"
            profit = target - entry
        elif mock_price <= sl:
            outcome = "SL Hit"
            profit = sl - entry
        else:
            outcome = "Hold"
            profit = mock_price - entry
        results.append({
            "Signal": row["Signal"],
            "Outcome": outcome,
            "Profit": round(profit, 2),
            "Strategy": row["Strategy"]
        })

    df_bt = pd.DataFrame(results)
    summary = df_bt.groupby("Strategy").agg(
        Trades=("Outcome", "count"),
        Wins=("Outcome", lambda x: (x == "Target Hit").sum()),
        Losses=("Outcome", lambda x: (x == "SL Hit").sum()),
        Avg_PnL=("Profit", "mean")
    )
    summary["Win %"] = (summary["Wins"] / summary["Trades"] * 100).round(2)
    return summary.reset_index()
