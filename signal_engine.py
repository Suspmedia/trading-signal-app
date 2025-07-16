import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import datetime
import requests

# ---------------------- OI DATA SCRAPER ----------------------
def get_oi_levels(index="NIFTY"):
    symbol_map = {
        "NIFTY": "NIFTY",
        "BANKNIFTY": "BANKNIFTY"
    }

    if index not in symbol_map:
        return {"support": None, "resistance": None, "note": "OI not available"}

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol_map[index]}"
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
            "resistance_strike": int(max_ce["strike"]),
            "support_oi": max_pe["PE_OI"],
            "resistance_oi": max_ce["CE_OI"]
        }

    except Exception as e:
        print("OI Error:", e)
        return {"support_strike": None, "resistance_strike": None}

# ---------------------- SIGNAL ENGINE ----------------------

def get_symbol(index):
    return {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN"
    }.get(index, "^NSEI")

def fetch_data(symbol):
    df = yf.download(symbol, period="5d", interval="5m", progress=False)
    df.dropna(inplace=True)

    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

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
    if latest["RSI"] < 30 and latest["MACD"] > latest["MACD_signal"] and latest["Close"] > latest["VWAP"]:
        return "BUY"
    if latest["RSI"] > 70 and latest["MACD"] < latest["MACD_signal"] and latest["Close"] < latest["VWAP"]:
        return "SELL"
    return None

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

    # ----------------- OI Strike Selection -----------------
    oi_data = get_oi_levels(index)

    if signal == "BUY" and oi_data["support_strike"]:
        strike = oi_data["support_strike"]
        source = "OI Support"
    elif signal == "SELL" and oi_data["resistance_strike"]:
        strike = oi_data["resistance_strike"]
        source = "OI Resistance"
    else:
        # Fallback to strategy-based
        source = "Default"
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
        "Strike Type": [strike_type + f" ({source})"],
        "Expiry": [expiry_date.strftime("%d %b %Y")]
    }

    return pd.DataFrame(signal_data)
