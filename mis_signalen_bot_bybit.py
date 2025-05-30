# mis_signalen_bot_bybit.py
# Telegram signaalbot voor Bybit gebaseerd op 1%-strategie (30 mei)
# LET OP: vereenvoudigde basisversie

import ccxt
import time
import requests

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

symbols = symbols = [
    "JASMY/USDT", "PEPE/USDT", "RENDER/USDT", "GRT/USDT", "INJ/USDT", "FET/USDT",
    "AR/USDT", "AVA/USDT", "CELO/USDT", "COMP/USDT", "SOLO/USDT", "PRIME/USDT",
    "ALGO/USDT", "APT/USDT", "ARKM/USDT", "BABYDOGE/USDT", "BONK/USDT", "CGPT/USDT",
    "CPOOL/USDT", "CRV/USDT", "DRIFT/USDT", "ENA/USDT", "ENS/USDT", "FLOKI/USDT",
    "GRASS/USDT", "HBAR/USDT", "ICX/USDT", "ICP/USDT", "ID/USDT", "HTX/USDT",
    "IMX/USDT", "KAS/USDT", "KAVA/USDT", "KMNO/USDT", "OP/USDT", "PENDLE/USDT",
    "ONE/USDT", "QNT/USDT", "RUNE/USDT", "STX/USDT", "SUI/USDT", "ZEN/USDT",
    "ZRX/USDT", "ANKR/USDT", "G/USDT", "SUNDOG/USDT", "TRX/USDT", "ACH/USDT"
]

def send_telegram(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": CHAT_ID,
        "text": msg
    })

def fetch_data(exchange, symbol):
    try:
        candles = exchange.fetch_ohlcv(symbol, timeframe="1m", limit=10)
        return candles
    except Exception as e:
        send_telegram(f"Fout bij ophalen {symbol}: {e}")
        return []

def check_signal(candles):
    if not candles or len(candles) < 2:
        return False
    last = candles[-1]
    prev = candles[-2]
    if last[4] > prev[4] and last[1] > last[3]:
        return True
    return False

def main():
    exchange = ccxt.bybit({"enableRateLimit": True})
    while True:
        for symbol in symbols:
            candles = fetch_data(exchange, symbol)
            if check_signal(candles):
                send_telegram(f"LONG-signaal 1% 📈: {symbol}")
        time.sleep(300)  # Check elke 5 min

if __name__ == "__main__":
    main()
