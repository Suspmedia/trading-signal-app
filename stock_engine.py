import yfinance as yf
import pandas as pd
import requests
from ta.momentum import RSIIndicator
from ta.trend import MACD
import datetime

# ------------------ NIFTY 50 STOCKS ------------------
NIFTY_50 = [
   "ADANIENT", "ADANIPORTS", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO",
    "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA",
    "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT",
    "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO",
    "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC", "INDUSINDBK",
    "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "M&M",
    "MARUTI", "NTPC", "NESTLEIND", "ONGC", "POWERGRID",
    "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TCS",
    "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN",
    "UPL", "ULTRACEMCO", "WIPRO"
]

# ------------------ NSE Option Chain ------------------
def get_stock_oi_levels(symbol):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol.upper()}"
        res = session.get(url, headers=headers)
        data = res.json()

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
        print("Stock OI Error:", e)
        return {"support_strike": None, "resistance_strike": None}

# ------------------ Fetch Stock Price ------------------
def fetch_stock_data(stock_symbol):
    try:
        df = yf.download(stock_symbol + ".NS", period="5d", interval="5m", progress=False)
        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"Error fetching {stock_symbol}: {e}")
        return pd.DataFrame()

# ------------------ Indicators ------------------
def calculate_indicators(df):
    df["RSI"] = RSIIndicator(close=df["Close"]).rsi()
    macd = MACD(close=df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()
    return df

# ------------------ Generate Signal ------------------
def generate_stock_signals(stock, strategy, strike_type, expiry_date):
    df = fetch_stock_data(stock)
    if df.empty:
        return pd.DataFrame()

    df = calculate_indicators(df)
    latest = df.iloc[-1]

    signal = None
    if latest["RSI"] < 30 and latest["MACD"] > latest["MACD_signal"] and latest["Close"] > latest["VWAP"]:
        signal = "BUY"
    elif latest["RSI"] > 70 and latest["MACD"] < latest["MACD_signal"] and latest["Close"] < latest["VWAP"]:
        signal = "SELL"

    if not signal:
        return pd.DataFrame()

    last_price = latest["Close"]
    atm_strike = round(last_price / 10) * 10
    oi_data = get_stock_oi_levels(stock)

    if signal == "BUY" and oi_data["support_strike"]:
        strike = oi_data["support_strike"]
        source = "OI Support"
    elif signal == "SELL" and oi_data["resistance_strike"]:
        strike = oi_data["resistance_strike"]
        source = "OI Resistance"
    else:
        source = "Default"
        if strike_type == "ATM":
            strike = atm_strike
        elif strike_type == "ITM":
            strike = atm_strike - 10
        else:
            strike = atm_strike + 10

    option_type = "CE" if signal == "BUY" else "PE"
    entry = round(40 + (last_price % 20), 2)
    target = round(entry * 2.1, 2)
    sl = round(entry * 0.7, 2)

    signal_data = {
        "Signal": [f"{stock.upper()} {signal} {strike} {option_type}"],
        "Entry": [f"{entry}"],
        "Target": [f"{target}"],
        "Stop Loss": [f"{sl}"],
        "Strategy": [strategy],
        "Strike Type": [strike_type + f" ({source})"],
        "Expiry": [expiry_date.strftime("%d %b %Y")]
    }

    return pd.DataFrame(signal_data)
