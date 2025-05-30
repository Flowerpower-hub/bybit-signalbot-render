# Telegram Signaalstrategie v1.0 – MIS-caps

import ccxt
import time
import requests
import os
import datetime
import pytz

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

symbols = [
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
        "text": msg,
        "parse_mode": "Markdown"
    })

def binnen_tijdvenster():
    nu = datetime.datetime.now(pytz.timezone("Europe/Amsterdam")).time()
    return datetime.time(6, 30) <= nu <= datetime.time(22, 0)

def fetch_data(exchange, symbol, timeframe):
    try:
        candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=50)
        return candles
    except Exception as e:
        send_telegram(f"⚠️ STORING bij ophalen {symbol}\n❌ {e}")
        return []

def calc_smoothed_ma(values, periode=20):
    return sum(values[-periode:]) / periode

def check_long(candle, stoch_k, stoch_d, smma, low):
    return candle['close'] < candle['bb_lower'] or (candle['color'] == 'groen' and candle['prev_close'] < candle['bb_lower']) and stoch_k < 20 and stoch_d < 20 and smma <= low

def check_short(candle, stoch_k, stoch_d, smma, high):
    return candle['close'] > candle['bb_upper'] or (candle['color'] == 'rood' and candle['prev_close'] > candle['bb_upper']) and stoch_k > 80 and stoch_d > 80 and smma >= high

def analyse_candles(candles):
    if len(candles) < 21:
        return None
    closes = [c[4] for c in candles]
    lows = [c[3] for c in candles]
    highs = [c[2] for c in candles]
    smma = calc_smoothed_ma(closes)
    last = candles[-1]
    prev = candles[-2]

    bb_std = sum([(c - smma) ** 2 for c in closes[-20:]]) / 20
    bb_std = bb_std ** 0.5
    bb_upper = smma + 2 * bb_std
    bb_lower = smma - 2 * bb_std

    candle = {
        'close': last[4],
        'open': last[1],
        'high': last[2],
        'low': last[3],
        'bb_upper': bb_upper,
        'bb_lower': bb_lower,
        'smma': smma,
        'prev_close': prev[4],
        'color': 'groen' if last[4] > last[1] else 'rood'
    }

    stoch_k = 100 * ((last[4] - min(lows[-14:])) / (max(highs[-14:]) - min(lows[-14:])))
    stoch_d = sum([100 * ((c[4] - min(lows[-14:])) / (max(highs[-14:]) - min(lows[-14:]))) for c in candles[-3:]]) / 3

    return candle, stoch_k, stoch_d

def main():
    exchange = ccxt.bybit({'enableRateLimit': True})
    send_telegram("✅ Signaalsysteem gestart en actief sinds 06:30")

    while True:
        if not binnen_tijdvenster():
            time.sleep(60)
            continue

        for symbol in symbols:
            for timeframe in ['15m', '5m']:
                candles = fetch_data(exchange, symbol, timeframe)
                analyse = analyse_candles(candles)
                if analyse:
                    candle, stoch_k, stoch_d = analyse
                    if check_long(candle, stoch_k, stoch_d, candle['smma'], candle['low']):
                        send_telegram(f"""**{symbol}**
🔹 Richting: Long
🔹 Timeframe: {timeframe}
🔹 Signaal: Candle onder BB, Stoch < 20, SMMA onder low""")
                    elif check_short(candle, stoch_k, stoch_d, candle['smma'], candle['high']):
                        send_telegram(f"""**{symbol}**
🔻 Richting: Short
🔻 Timeframe: {timeframe}
🔻 Signaal: Candle boven BB, Stoch > 80, SMMA boven high""")

        time.sleep(300)

if __name__ == "__main__":
    main()
