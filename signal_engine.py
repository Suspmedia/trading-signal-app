import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import requests

# ---------------------- OI DATA SCRAPER ----------------------
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

# ---------------------- OPTION LTP FETCHER ----------------------
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

# ---------------------- SIGNAL ENGINE ----------------------
def get_symbol(index):
    return {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN"}.get(index, "^NSEI")

def fetch_data(symbol):
    df = yf.download(symbol, period="5d", interval="5m", progress=False, auto_adjust=True)
    df.dropna(inplace=True)
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
    if latest["RSI"] < 40 and latest["MACD"] > latest["MACD_signal"] and latest["Close"] > latest["VWAP"]:
        return "BUY"
    if latest["RSI"] > 60 and latest["MACD"] < latest["MACD_signal"] and latest["Close"] < latest["VWAP"]:
        return "SELL"
    return None

def generate_signals_multi(index, strike_type, expiry_date):
    df = fetch_data(get_symbol(index))
    if df.empty:
        return pd.DataFrame()

    df = calculate_indicators(df)
    signal_direction = is_signal(df)
    if signal_direction is None:
        return pd.DataFrame()

    last_price = df["Close"].iloc[-1]
    atm_strike = round(last_price / 50) * 50
    oi_data = get_oi_levels(index)
    option_chain = get_option_chain_ltp(index)

    strategies = ["Safe (OI Support)", "Min Investment", "Max Profit"]
    results = []

    for strategy in strategies:
        # Strategy-specific strike selection
        if strategy == "Safe (OI Support)":
            strike = oi_data["support_strike"] if signal_direction == "BUY" else oi_data["resistance_strike"]
            source = "OI Support/Resistance"

        elif strategy == "Min Investment":
            best_strike, min_ltp = atm_strike, float("inf")
            for k, v in option_chain.items():
                ltp = v.get("CE" if signal_direction == "BUY" else "PE")
                if ltp and 5 < ltp < min_ltp:
                    best_strike = k
                    min_ltp = ltp
            strike = best_strike
            source = "Lowest Premium"

        elif strategy == "Max Profit":
            strike = atm_strike - 50 if signal_direction == "BUY" else atm_strike + 50
            source = "Momentum Play"

        else:
            strike = atm_strike
            source = "Default"

        option_type = "CE" if signal_direction == "BUY" else "PE"
        entry = option_chain.get(strike, {}).get(option_type)
        if not entry or entry < 1:
            entry = round(40 + (last_price % 20), 2)
        target = round(entry * 2.1, 2)
        sl = round(entry * 0.7, 2)

        results.append({
            "Signal": f"{index} {signal_direction} {strike} {option_type}",
            "Entry": f"₹{entry}",
            "Target": f"₹{target}",
            "Stop Loss": f"₹{sl}",
            "Strategy": strategy,
            "Strike Type": f"{strike_type} ({source})",
            "Expiry": expiry_date.strftime("%d %b %Y")
        })

    return pd.DataFrame(results)
