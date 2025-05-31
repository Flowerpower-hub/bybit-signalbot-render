
import ccxt
import time
import requests
import os
import datetime
import pytz
import csv

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

laatste_signalen = {}
bevestigde_signalen = {}

def send_telegram(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": CHAT_ID,
        "text": msg
    })

def log_signaal(symbol, richting, timeframe, signaaltype):
    tijd_nl = datetime.datetime.now(pytz.timezone("Europe/Amsterdam")).strftime("%Y-%m-%d %H:%M:%S")
    logrij = [tijd_nl, symbol, richting, timeframe, signaaltype]
    bestand = "signaal_log.csv"
    nieuw_bestand = not os.path.exists(bestand)
    with open(bestand, mode="a", newline="") as file:
        writer = csv.writer(file)
        if nieuw_bestand:
            writer.writerow(["tijd", "symbol", "richting", "timeframe", "type"])
        writer.writerow(logrij)

def binnen_tijdvenster():
    nu = datetime.datetime.now(pytz.timezone("Europe/Amsterdam")).time()
    return datetime.time(6, 30) <= nu <= datetime.time(22, 0)

def fetch_data(exchange, symbol, timeframe):
    try:
        return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=50)
    except Exception as e:
        send_telegram(f"STORING bij ophalen {symbol} ({timeframe})\nFout: {e}")
        return []

def bepaal_trend(candles):
    closes = [c[4] for c in candles]
    if len(closes) < 21:
        return None
    ema9 = sum(closes[-9:]) / 9
    ema21 = sum(closes[-21:]) / 21
    return "up" if ema9 > ema21 else "down"

def analyse_candles(candles):
    if len(candles) < 21:
        return None
    closes = [c[4] for c in candles]
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    smma = sum(closes[-20:]) / 20
    std = (sum([(c - smma) ** 2 for c in closes[-20:]]) / 20) ** 0.5
    bb_upper = smma + 2 * std
    bb_lower = smma - 2 * std
    bb_basis = smma
    bb_afstand_pct = (bb_upper - bb_lower) / bb_basis * 100
    if bb_afstand_pct < 2:
        return None
    candle = candles[-2]
    prev = candles[-3]
    kleur = "groen" if candle[4] > candle[1] else "rood"
    stoch_k = 100 * ((candle[4] - min(lows[-14:])) / (max(highs[-14:]) - min(lows[-14:])))
    stoch_d = sum([100 * ((c[4] - min(lows[-14:])) / (max(highs[-14:]) - min(lows[-14:]))) for c in candles[-4:-1]]) / 3
    return {
        "close": candle[4],
        "open": candle[1],
        "high": candle[2],
        "low": candle[3],
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "smma": smma,
        "color": kleur,
        "prev_close": prev[4],
        "stoch_k": stoch_k,
        "stoch_d": stoch_d
    }

def check_entry(info, richting):
    if richting == "long":
        return ((info["close"] < info["bb_lower"]) or
                (info["color"] == "groen" and info["prev_close"] < info["bb_lower"])) and                 info["stoch_k"] < 20 and info["stoch_d"] < 20
    elif richting == "short":
        return ((info["close"] > info["bb_upper"]) or
                (info["color"] == "rood" and info["prev_close"] > info["bb_upper"])) and                 info["stoch_k"] > 80 and info["stoch_d"] > 80
    return False

def main():
    print("✅ Start main()")

    exchange = ccxt.bybit({'enableRateLimit': True})
    send_telegram("Signaalsysteem actief sinds 06:30")

    while True:
        if not binnen_tijdvenster():
            time.sleep(60)
            continue

        for symbol in symbols:
            print(f"🔍 Ophalen 1h candles voor {symbol}"); candles_1h = fetch_data(exchange, symbol, '1h')
            print(f"📈 Trend bepalen voor {symbol}"); trend = bepaal_trend(candles_1h)
            if not trend:
                continue

            print(f"🔍 Ophalen 15m candles voor {symbol}"); candles_15m = fetch_data(exchange, symbol, '15m')
            print(f"🧠 Analyse 15m voor {symbol}"); analyse_15m = analyse_candles(candles_15m)
            if analyse_15m:
                richting = "long" if trend == "up" else "short"
                if check_entry(analyse_15m, richting):
                    sleutel = f"{symbol}_{richting}"
                    nu = datetime.datetime.now()
                    laatst = laatste_signalen.get(sleutel)
                    if not laatst or (nu - laatst).total_seconds() > 3600:
                        send_telegram(f"{symbol}\nTimeframe: 15m\nRichting: {richting.upper()}\nSignaal: Candle + Stoch validatie (BB & Trendfilter 1H)")
                        log_signaal(symbol, richting, "15m", "entry")
                        laatste_signalen[sleutel] = nu
                        bevestigde_signalen[sleutel] = nu

            print(f"🔍 Ophalen 5m candles voor {symbol}"); candles_5m = fetch_data(exchange, symbol, '5m')
            print(f"🧠 Analyse 5m voor {symbol}"); analyse_5m = analyse_candles(candles_5m)
            if analyse_5m:
                richting = "long" if trend == "up" else "short"
                sleutel = f"{symbol}_{richting}"
                if sleutel in bevestigde_signalen:
                    nu = datetime.datetime.now()
                    tijd_15m = bevestigde_signalen[sleutel]
                    if (nu - tijd_15m).total_seconds() < 1800:
                        if check_entry(analyse_5m, richting):
                            send_telegram(f"{symbol}\nTimeframe: 5m\nRichting: {richting.upper()}\nBevestiging van eerder 15m-signaal")
                            log_signaal(symbol, richting, "5m", "bevestiging")
                            del bevestigde_signalen[sleutel]

        time.sleep(300)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        tijd = datetime.datetime.now(pytz.timezone("Europe/Amsterdam")).strftime("%Y-%m-%d %H:%M:%S")
        foutmelding = f"CRASH op {tijd}\nFout: {str(e)}"
        try:
            send_telegram(foutmelding)
        except:
            pass
        raise

