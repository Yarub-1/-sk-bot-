import requests
import pandas as pd
import time
from datetime import datetime

BOT_TOKEN = "8791976068:AAG9M46lLkox7o5O2qzOVPRz0H0go01ZYeM"
CHAT_ID   = "1853838900"

SYMBOLS = [
    # الذهب
    ("XAUUSD=X", "XAUUSD",  "5m",  8),
    ("XAUUSD=X", "XAUUSD",  "15m", 11),
    ("XAUUSD=X", "XAUUSD",  "30m", 12),
    ("XAUUSD=X", "XAUUSD",  "1h",  14),
    ("XAUUSD=X", "XAUUSD",  "4h",  10),
    # الناسداك
    ("NQ=F",     "NAS100",  "5m",  9),
    ("NQ=F",     "NAS100",  "15m", 12),
    ("NQ=F",     "NAS100",  "30m", 14),
    ("NQ=F",     "NAS100",  "1h",  15),
    # US500
    ("ES=F",     "US500",   "5m",  8),
    ("ES=F",     "US500",   "15m", 11),
    ("ES=F",     "US500",   "30m", 13),
    ("ES=F",     "US500",   "1h",  14),
    # القهوة
    ("KC=F",     "COFFEE",  "5m",  12),
    ("KC=F",     "COFFEE",  "15m", 15),
    ("KC=F",     "COFFEE",  "30m", 18),
    ("KC=F",     "COFFEE",  "1h",  20),
    # GBPUSD
    ("GBPUSD=X", "GBPUSD",  "5m",  8),
    ("GBPUSD=X", "GBPUSD",  "15m", 10),
    ("GBPUSD=X", "GBPUSD",  "30m", 11),
    ("GBPUSD=X", "GBPUSD",  "1h",  14),
    ("GBPUSD=X", "GBPUSD",  "4h",  10),
    # النفط
    ("CL=F",     "USOIL",   "5m",  9),
    ("CL=F",     "USOIL",   "15m", 12),
    ("CL=F",     "USOIL",   "30m", 13),
    ("CL=F",     "USOIL",   "1h",  16),
    # البيتكوين
    ("BTC-USD",  "BTCUSDT", "5m",  9),
    ("BTC-USD",  "BTCUSDT", "15m", 12),
    ("BTC-USD",  "BTCUSDT", "30m", 14),
    ("BTC-USD",  "BTCUSDT", "1h",  16),
    ("BTC-USD",  "BTCUSDT", "4h",  11),
    # EURUSD
    ("EURUSD=X", "EURUSD",  "5m",  9),
    ("EURUSD=X", "EURUSD",  "15m", 12),
    ("EURUSD=X", "EURUSD",  "30m", 13),
    ("EURUSD=X", "EURUSD",  "1h",  15),
    ("EURUSD=X", "EURUSD",  "4h",  10),
    # GBPJPY
    ("GBPJPY=X", "GBPJPY",  "5m",  10),
    ("GBPJPY=X", "GBPJPY",  "15m", 12),
    ("GBPJPY=X", "GBPJPY",  "30m", 14),
    ("GBPJPY=X", "GBPJPY",  "1h",  16),
    ("GBPJPY=X", "GBPJPY",  "4h",  11),
]

last_signal = {}

def send_telegram(message):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_data(symbol, interval):
    try:
        period_map = {"5m":"1d","15m":"5d","30m":"5d","1h":"10d","4h":"60d"}
        period  = period_map.get(interval, "5d")
        url     = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params  = {"interval": interval, "range": period, "includePrePost": "false"}
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

def check_symbol(symbol, name, interval, sensitivity):
    df = get_data(symbol, interval)
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
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking...")
        for symbol, name, interval, sensitivity in SYMBOLS:
            try:
                check_symbol(symbol, name, interval, sensitivity)
                time.sleep(1)
            except Exception as e:
                print(f"Error {name} {interval}: {e}")
        print("Waiting 60 seconds...")
        time.sleep(60)

if __name__ == "__main__":
    main()
