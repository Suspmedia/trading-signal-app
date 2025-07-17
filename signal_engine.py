import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import datetime
import requests

# ---------------------- OI DATA SCRAPER ----------------------
def get_oi_levels(index="NIFTY"):
    symbol_map = {"NIFTY": "NIFTY", "BANKNIFTY": "BANKNIFTY"}
    if index not in symbol_map:
        return {"support_strike": None, "resistance_strike": None}
    headers = {"User-Agent": "Mozilla/5.0"}
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
            ce_ltp = record.get("CE", {}).get("lastPrice", None)
            pe_ltp = record.get("PE", {}).get("lastPrice", None)
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
    if df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(col in df.columns for col in required_cols): return pd.DataFrame()
    return df

def calculate_indicators(df):
    df["RSI"] = RSIIndicator(close=df["Close"]).rsi()
    macd = MACD(close=df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()
    return df

def is_signal(df):
    if df.empty: return None
    latest = df.iloc[-1]
    print(f"RSI: {latest['RSI']:.2f}, MACD: {latest['MACD']:.2f}, Signal: {latest['MACD_signal']:.2f}")
    if latest["RSI"] < 40 and latest["MACD"] > latest["MACD_signal"] and latest["Close"] > latest["VWAP"]:
        return "BUY"
    if latest["RSI"] > 60 and latest["MACD"] < latest["MACD_signal"] and latest["Close"] < latest["VWAP"]:
        return "SELL"
    if 40 <= latest["RSI"] <= 45 and latest["MACD"] > latest["MACD_signal"]:
        return "WEAK_BUY"
    if 55 <= latest["RSI"] <= 60 and latest["MACD"] < latest["MACD_signal"]:
        return "WEAK_SELL"
    return None

def generate_signals_multi(index, strike_type, expiry_date):
    symbol = get_symbol(index)
    df = fetch_data(symbol)
    if df.empty: return pd.DataFrame()
    df = calculate_indicators(df)
    signal_direction = is_signal(df)
    if signal_direction is None: return pd.DataFrame()

    last_price = df["Close"].iloc[-1]
    atm_strike = round(last_price / 50) * 50
    oi_data = get_oi_levels(index)
    option_chain = get_option_chain_ltp(index)
    results = []

    strategies = ["Safe (OI Support)", "Min Investment", "Max Profit", "Breakout", "Reversal"]

    for strategy in strategies:
        if strategy == "Safe (OI Support)":
            strike = oi_data["support_strike"] if "BUY" in signal_direction else oi_data["resistance_strike"]
            source = "OI Support/Resistance"

        elif strategy == "Min Investment":
            min_premium = float("inf")
            best_strike = atm_strike
            for strike_val, prices in option_chain.items():
                ltp = prices.get("CE" if "BUY" in signal_direction else "PE")
                if ltp and 10 <= ltp <= min_premium:
                    min_premium = ltp
                    best_strike = strike_val
            strike = best_strike
            source = "Lowest Premium OTM"

        elif strategy == "Max Profit":
            strike = atm_strike - 50 if "BUY" in signal_direction else atm_strike + 50
            source = "Directional (Momentum)"

        elif strategy == "Breakout":
            try:
                prev_high = df["High"].resample("1D").max().iloc[-2]
                prev_low = df["Low"].resample("1D").min().iloc[-2]
                if df.iloc[-1]["Close"] > prev_high:
                    signal_direction = "BUY"
                    strike = atm_strike
                    source = "Breakout High"
                elif df.iloc[-1]["Close"] < prev_low:
                    signal_direction = "SELL"
                    strike = atm_strike
                    source = "Breakout Low"
                else:
                    continue
            except:
                continue

        elif strategy == "Reversal":
            if df.iloc[-1]["RSI"] < 30 and "BUY" in signal_direction:
                strike = oi_data["support_strike"] or (atm_strike - 50)
                source = "Reversal from OI Support"
            elif df.iloc[-1]["RSI"] > 70 and "SELL" in signal_direction:
                strike = oi_data["resistance_strike"] or (atm_strike + 50)
                source = "Reversal from OI Resistance"
            else:
                continue

        else:
            strike = atm_strike
            source = "Default"

        option_type = "CE" if "BUY" in signal_direction else "PE"
        entry = option_chain.get(strike, {}).get(option_type, None)
        if not entry or entry < 1:
            entry = round(40 + (last_price % 20), 2)
        target = round(entry * 2.1, 2)
        sl = round(entry * 0.7, 2)

        signal_data = {
            "Signal": f"{index} {signal_direction.replace('WEAK_', '')} {strike} {option_type}",
            "Entry": f"₹{entry}",
            "Target": f"₹{target}",
            "Stop Loss": f"₹{sl}",
            "Strategy": strategy + (" (Weak)" if "WEAK" in signal_direction else ""),
            "Strike Type": f"{strike_type} ({source})",
            "Expiry": expiry_date.strftime("%d %b %Y")
        }
        results.append(signal_data)

    return pd.DataFrame(results)
