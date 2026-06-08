import requests
import pandas as pd
import time
from datetime import datetime

BOT_TOKEN  = "8791976068:AAG9M46lLkox7o5O2qzOVPRz0H0go01ZYeM"
CHAT_ID    = "1853838900"
TWELVE_KEY = "04141b201ee547f8b2ba600cbcc287b5"

# الرموز التي تستخدم Twelve Data (فوركس + ذهب + بيتكوين)
TWELVE_SYMBOLS = [
    ("XAU/USD", "XAUUSD",  "5min",  8),
    ("XAU/USD", "XAUUSD",  "15min", 11),
    ("XAU/USD", "XAUUSD",  "30min", 12),
    ("XAU/USD", "XAUUSD",  "1h",    14),
    ("XAU/USD", "XAUUSD",  "4h",    10),
    ("GBP/USD", "GBPUSD",  "5min",  8),
    ("GBP/USD", "GBPUSD",  "15min", 10),
    ("GBP/USD", "GBPUSD",  "30min", 11),
    ("GBP/USD", "GBPUSD",  "1h",    14),
    ("GBP/USD", "GBPUSD",  "4h",    10),
    ("EUR/USD", "EURUSD",  "5min",  9),
    ("EUR/USD", "EURUSD",  "15min", 12),
    ("EUR/USD", "EURUSD",  "30min", 13),
    ("EUR/USD", "EURUSD",  "1h",    15),
    ("EUR/USD", "EURUSD",  "4h",    10),
    ("GBP/JPY", "GBPJPY",  "5min",  10),
    ("GBP/JPY", "GBPJPY",  "15min", 12),
    ("GBP/JPY", "GBPJPY",  "30min", 14),
    ("GBP/JPY", "GBPJPY",  "1h",    16),
    ("GBP/JPY", "GBPJPY",  "4h",    11),
    ("BTC/USD", "BTCUSDT", "5min",  9),
    ("BTC/USD", "BTCUSDT", "15min", 12),
    ("BTC/USD", "BTCUSDT", "30min", 14),
    ("BTC/USD", "BTCUSDT", "1h",    16),
    ("BTC/USD", "BTCUSDT", "4h",    11),
]

# الرموز التي تستخدم Yahoo Finance
YAHOO_SYMBOLS = [
    ("NQ=F",     "NAS100", "5min",  9),
    ("NQ=F",     "NAS100", "15min", 12),
    ("NQ=F",     "NAS100", "30min", 14),
    ("NQ=F",     "NAS100", "1h",    15),
    ("XAGUSD=X", "XAGUSD", "5min",  11),
    ("XAGUSD=X", "XAGUSD", "15min", 14),
    ("XAGUSD=X", "XAGUSD", "30min", 16),
    ("XAGUSD=X", "XAGUSD", "1h",    18),
    ("ES=F",     "US500",  "5min",  8),
    ("ES=F",     "US500",  "15min", 11),
    ("ES=F",     "US500",  "30min", 13),
    ("ES=F",     "US500",  "1h",    14),
    ("KC=F",     "COFFEE", "5min",  12),
    ("KC=F",     "COFFEE", "15min", 15),
    ("KC=F",     "COFFEE", "30min", 18),
    ("KC=F",     "COFFEE", "1h",    20),
    ("CL=F",     "USOIL",  "5min",  9),
    ("CL=F",     "USOIL",  "15min", 12),
    ("CL=F",     "USOIL",  "30min", 13),
    ("CL=F",     "USOIL",  "1h",    16),
]

last_signal = {}

def send_telegram(message):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_data_twelve(symbol, interval):
    try:
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol":     symbol,
            "interval":   interval,
            "outputsize": 200,
            "apikey":     TWELVE_KEY,
        }
        r    = requests.get(url, params=params, timeout=15)
        data = r.json()
        if data.get("status") == "error":
            print(f"Twelve error {symbol}: {data.get('message')}")
            return None
        values = data.get("values", [])
        if not values:
            return None
        df = pd.DataFrame(values)
        df = df.rename(columns={"datetime": "time"})
        df["time"]  = pd.to_datetime(df["time"])
        df["high"]  = df["high"].astype(float)
        df["low"]   = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df = df.sort_values("time").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Twelve error {symbol} {interval}: {e}")
        return None

def get_data_yahoo(symbol, interval):
    try:
        interval_map = {"5min":"5m","15min":"15m","30min":"30m","1h":"60m","4h":"1h"}
        period_map   = {"5min":"1d","15min":"5d","30min":"5d","1h":"10d","4h":"60d"}
        yf_interval  = interval_map.get(interval, "5m")
        period       = period_map.get(interval, "5d")
        url     = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params  = {"interval": yf_interval, "range": period, "includePrePost": "false"}
        headers = {"User-Agent": "Mozilla/5.0"}
        r       = requests.get(url, params=params, headers=headers, timeout=15)
        data    = r.json()
        result  = data.get("chart", {}).get("result", None)
        if not result:
            return None
        timestamps = result[0].get("timestamp", None)
        if not timestamps:
            return None
        ohlc = result[0]["indicators"]["quote"][0]
        df = pd.DataFrame({
            "time":  pd.to_datetime(timestamps, unit="s"),
            "high":  ohlc.get("high", []),
            "low":   ohlc.get("low", []),
            "close": ohlc.get("close", []),
        }).dropna()
        return df if len(df) >= 10 else None
    except Exception as e:
        print(f"Yahoo error {symbol} {interval}: {e}")
        return None

def pivot_high(high, left, right):
    result = [None] * len(high)
    for i in range(left, len(high) - right):
        window = high[i-left:i+right+1]
        if high[i] == max(window):
            result[i] = high[i]
    return result

def pivot_low(low, left, right):
    result = [None] * len(low)
    for i in range(left, len(low) - right):
        window = low[i-left:i+right+1]
        if low[i] == min(window):
            result[i] = low[i]
    return result

def sk_indicator(df, sensitivity):
    pivot_left_val  = sensitivity
    pivot_right_val = max(2, int(sensitivity / 2))
    highs  = list(df["high"])
    lows   = list(df["low"])
    closes = list(df["close"])
    ph_list = pivot_high(highs, pivot_left_val, pivot_right_val)
    pl_list = pivot_low(lows,   pivot_left_val, pivot_right_val)

    buy_wave_0 = None; buy_0_bar = None; buy_wave_A = None
    buy_mid = None; buy_waiting_B = False; buy_reached = False; buy_wave_B = None
    sell_wave_0 = None; sell_0_bar = None; sell_wave_A = None
    sell_mid = None; sell_waiting_B = False; sell_reached = False; sell_wave_B = None

    buy_signals  = [False] * len(df)
    sell_signals = [False] * len(df)

    for i in range(len(df)):
        pl = pl_list[i]; ph = ph_list[i]
        c = closes[i]; l = lows[i]; h = highs[i]

        if pl is not None:
            buy_wave_0 = pl; buy_0_bar = i; buy_wave_A = None
            buy_mid = None; buy_waiting_B = False; buy_reached = False; buy_wave_B = None

        if ph is not None and buy_wave_0 is not None and ph > buy_wave_0:
            if i > (buy_0_bar or 0):
                buy_wave_A = ph
                buy_mid = buy_wave_0 + (buy_wave_A - buy_wave_0) * 0.5
                buy_waiting_B = True; buy_reached = False; buy_wave_B = None

        if buy_waiting_B and buy_mid is not None and buy_wave_0 is not None:
            if l < buy_wave_0:
                buy_waiting_B = False; buy_reached = False
                buy_wave_B = None; buy_wave_A = None; buy_mid = None
            elif l <= buy_mid:
                buy_reached = True
                if buy_wave_B is None or l < buy_wave_B:
                    buy_wave_B = l

        if buy_reached and buy_wave_A is not None and c > buy_wave_A:
            buy_signals[i] = True; buy_reached = False; buy_waiting_B = False

        if ph is not None:
            sell_wave_0 = ph; sell_0_bar = i; sell_wave_A = None
            sell_mid = None; sell_waiting_B = False; sell_reached = False; sell_wave_B = None

        if pl is not None and sell_wave_0 is not None and pl < sell_wave_0:
            if i > (sell_0_bar or 0):
                sell_wave_A = pl
                sell_mid = sell_wave_A + (sell_wave_0 - sell_wave_A) * 0.5
                sell_waiting_B = True; sell_reached = False; sell_wave_B = None

        if sell_waiting_B and sell_mid is not None and sell_wave_0 is not None:
            if h > sell_wave_0:
                sell_waiting_B = False; sell_reached = False
                sell_wave_B = None; sell_wave_A = None; sell_mid = None
            elif h >= sell_mid:
                sell_reached = True
                if sell_wave_B is None or h > sell_wave_B:
                    sell_wave_B = h

        if sell_reached and sell_wave_A is not None and c < sell_wave_A:
            sell_signals[i] = True; sell_reached = False; sell_waiting_B = False

    return buy_signals, sell_signals

def process_signal(df, name, interval, sensitivity):
    if df is None or len(df) < sensitivity * 3:
        print(f"No data: {name} {interval}")
        return
    buy_sigs, sell_sigs = sk_indicator(df, sensitivity)
    idx = len(df) - 2
    if idx < 0:
        return
    key      = f"{name}_{interval}"
    cur_time = str(df["time"].iloc[idx])
    price    = round(df["close"].iloc[idx], 5)
    if buy_sigs[idx]:
        sig_key = f"{key}_BUY_{cur_time}"
        if last_signal.get(key) != sig_key:
            last_signal[key] = sig_key
            send_telegram(f"🟢 <b>شراء | {name}</b>\n⏱ الفريم: {interval}\n💰 السعر: {price}\n🕐 الوقت: {cur_time}\n📊 مؤشر SK Fibonacci")
            print(f"BUY: {name} {interval} @ {price}")
    if sell_sigs[idx]:
        sig_key = f"{key}_SELL_{cur_time}"
        if last_signal.get(key) != sig_key:
            last_signal[key] = sig_key
            send_telegram(f"🔴 <b>بيع | {name}</b>\n⏱ الفريم: {interval}\n💰 السعر: {price}\n🕐 الوقت: {cur_time}\n📊 مؤشر SK Fibonacci")
            print(f"SELL: {name} {interval} @ {price}")

def main():
    send_telegram("🤖 <b>SK Trading Bot</b> يعمل الآن ✅\nيراقب جميع الرموز والفريمات...")
    print("SK Bot started...")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking Twelve Data symbols...")

        # Twelve Data — 8 طلبات في الدقيقة = ننتظر 8 ثواني بين كل طلب
        for symbol, name, interval, sensitivity in TWELVE_SYMBOLS:
            try:
                df = get_data_twelve(symbol, interval)
                process_signal(df, name, interval, sensitivity)
                time.sleep(8)  # 8 ثواني لضمان عدم تجاوز الحد
            except Exception as e:
                print(f"Error {name} {interval}: {e}")

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking Yahoo symbols...")

        # Yahoo Finance — بدون حد
        for symbol, name, interval, sensitivity in YAHOO_SYMBOLS:
            try:
                df = get_data_yahoo(symbol, interval)
                process_signal(df, name, interval, sensitivity)
                time.sleep(2)
            except Exception as e:
                print(f"Error {name} {interval}: {e}")

        print("Waiting 5 minutes...")
        time.sleep(300)  # ننتظر 5 دقائق بين كل دورة

if __name__ == "__main__":
    main()
