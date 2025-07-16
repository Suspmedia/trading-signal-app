# signal_engine.py

import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import datetime

def get_symbol(index):
    symbol_map = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN"
    }
    return symbol_map.get(index, "^NSEI")

def fetch_data(symbol):
    df = yf.download(symbol, period="5d", interval="5m", progress=False)
    df.dropna(inplace=True)

    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in data: {missing}")

    return df

def calculate_indicators(df):
    df["RSI"] = RSIIndicator(close=df["Close"]).rsi()
    macd = MACD(close=df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()
    return df

def is_signal(df):
    if df.empty:
        return None
    latest = df.iloc[-1]
    signal = None

    if latest["RSI"] < 30 and latest["MACD"] > latest["MACD_signal"] and latest["Close"] > latest["VWAP"]:
        signal = "BUY"
    elif latest["RSI"] > 70 and latest["MACD"] < latest["MACD_signal"] and latest["Close"] < latest["VWAP"]:
        signal = "SELL"

    return signal

def generate_signals(index, strategy, strike_type, expiry_date):
    symbol = get_symbol(index)
    df = fetch_data(symbol)
    
    if df.empty:
        return pd.DataFrame()

    df = calculate_indicators(df)
    signal = is_signal(df)

    if signal is None:
        return pd.DataFrame()

    last_price = df["Close"].iloc[-1]
    atm_strike = round(last_price / 50) * 50

    if strike_type == "ATM":
        strike = atm_strike
    elif strike_type == "ITM":
        strike = atm_strike - 100
    else:
        strike = atm_strike + 100

    option_type = "CE" if signal == "BUY" else "PE"

    entry = round(40 + (last_price % 20), 2)
    target = round(entry * 2.1, 2)
    sl = round(entry * 0.7, 2)

    signal_data = {
        "Signal": [f"{index} {signal} {strike} {option_type}"],
        "Entry": [f"₹{entry}"],
        "Target": [f"₹{target}"],
        "Stop Loss": [f"₹{sl}"],
        "Strategy": [strategy],
        "Strike Type": [strike_type],
        "Expiry": [expiry_date.strftime("%d %b %Y")]
    }

    return pd.DataFrame(signal_data)