from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = "8791976068:AAG9M46lLkox7o5O2qzOVPRz0H0go01ZYeM"
CHAT_ID   = "1853838900"

def send_telegram(message):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=data)

@app.route("/webhook", methods=["POST"])
def webhook():
    data    = request.json
    signal  = data.get("signal", "")
    symbol  = data.get("symbol", "")
    price   = data.get("price", "")
    tf      = data.get("timeframe", "")
    time_   = data.get("time", "")

    if signal == "BUY":
        emoji = "🟢"
        label = "شراء"
    else:
        emoji = "🔴"
        label = "بيع"

    message = (
        f"{emoji} <b>{label} | {symbol}</b>\n"
        f"⏱ الفريم: {tf}\n"
        f"💰 السعر: {price}\n"
        f"🕐 الوقت: {time_}\n"
        f"📊 مؤشر SK Fibonacci"
    )

    send_telegram(message)
    return {"status": "ok"}, 200

@app.route("/", methods=["GET"])
def index():
    return "SK Trading Bot is running ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
