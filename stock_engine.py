import yfinance as yf
import pandas as pd
import requests
from ta.momentum import RSIIndicator
from ta.trend import MACD
import datetime
import time

# ---------------------- Fetch Full NSE F&O Stock List ----------------------
def get_nse_fo_stocks():
    try:
        url = "https://www.nseindia.com/api/liveEquity-derivatives"
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        response = session.get(url, headers=headers)
        data = response.json()
        stocks = [item["symbol"] for item in data.get("data", []) if item.get("symbol")]
        return list(sorted(set(stocks)))
    except Exception as e:
        print("Error fetching F&O stocks:", e)
        return []

# ---------------------- Get Option Chain OI Levels ----------------------
def get_stock_oi_levels(symbol):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
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
    except:
        return None

# ---------------------- Fetch Stock OHLC ----------------------
def fetch_stock_data(symbol):
    try:
        df = yf.download(symbol + ".NS", period="5d", interval="5m", progress=False)
        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

# ---------------------- Signal Check ----------------------
def check_signal(df):
    try:
        df["RSI"] = RSIIndicator(close=df["Close"]).rsi()
        macd = MACD(close=df["Close"])
        df["MACD"] = macd.macd()
        df["MACD_signal"] = macd.macd_signal()
        df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()

        latest = df.iloc[-1]
        if latest["RSI"] < 30 and latest["MACD"] > latest["MACD_signal"] and latest["Close"] > latest["VWAP"]:
            return "BUY"
        elif latest["RSI"] > 70 and latest["MACD"] < latest["MACD_signal"] and latest["Close"] < latest["VWAP"]:
            return "SELL"
        else:
            return None
    except:
        return None

# ---------------------- Generate Signal for Specific Stock ----------------------
def generate_stock_signals(stock, strategy, strike_type, expiry_date):
    df = fetch_stock_data(stock)
    if df.empty:
        return pd.DataFrame()

    signal = check_signal(df)
    if not signal:
        return pd.DataFrame()

    last_price = round(df["Close"].iloc[-1], 2)
    atm_strike = round(last_price / 10) * 10
    oi_data = get_stock_oi_levels(stock)

    if not oi_data:
        return pd.DataFrame()

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
        "Entry": [entry],
        "Target": [target],
        "Stop Loss": [sl],
        "Strategy": [strategy],
        "Strike Type": [strike_type + f" ({source})"],
        "Expiry": [expiry_date.strftime("%d %b %Y")],
        "Stock LTP": [last_price]  # ✅ New column
    }

    return pd.DataFrame(signal_data)

# ---------------------- Screen Stocks with Signals ----------------------
def get_suggested_stocks(expiry_date, strategy="Safe", strike_type="ATM", limit=25):
    fo_list = get_nse_fo_stocks()
    suggestions = []

    for symbol in fo_list:
        try:
            df = fetch_stock_data(symbol)
            if df.empty:
                continue
            signal = check_signal(df)
            if signal:
                suggestion_df = generate_stock_signals(symbol, strategy, strike_type, expiry_date)
                if not suggestion_df.empty:
                    suggestions.append((symbol, suggestion_df))
        except:
            continue

        if len(suggestions) >= limit:
            break

    return suggestions
