from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from binance.client import Client
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import os, time

# ==== Config ====
BOT_TOKEN = "8087180147:AAErqoc8rM_k-Tkyf0uxPuCe686cAoRiMbI"
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"

client = Client(API_KEY, API_SECRET)
USD_TO_VND = 25000

# ==== Hàm chung ====
def calculate_rsi(prices, period=21):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

symbols = [f"{s.lower()}usdt" for s in [
    "BTC", "YFI", "ETH", "BTCDOM", "MKR", "BNB", "BCH", "TAO", "AAVE", "SOL", "LTC", "HYPE",
    "COMP", "TRB", "BSV", "AVAX", "LINK", "ENS", "ETC", "METIS", "KSM", "GMX", "NMR", "EGLD",
    "INJ", "AUCTION", "UNI", "SSV", "ORDI", "TRUMP", "ZEN", "LPT", "NEO", "AR", "XVS", "MOVR",
    "ICP", "PENDLE", "ATOM", "APT", "VANA", "CVX", "DOT", "RAY", "GAS", "SUI", "OMNI", "TON",
    "QTUM", "XRP", "FXS", "BERA", "CAKE", "AXS", "NEAR", "FIL", "ORCA", "MORPHO", "JTO", "ZRO",
    "CYBER", "ETHW", "TIA", "UMA", "MASK", "EIGEN", "RUNE", "LDO", "ALL", "KAITO", "VIRTUAL",
    "ETHFI", "ONDO", "WLD", "ADA", "BAND", "WIF", "LQTY", "CRV", "NXPC", "FARTCOIN", "SUSHI",
    "BNT", "TWT", "MTL", "OP", "AGLD", "SNX", "ME", "ENA", "STX", "DYDX", "DRIFT", "SUPER", "IO",
    "APE", "PHB", "ACE", "HIGH", "IMX", "RONIN", "ARB", "RED", "SYRUP", "JUP", "ARKM", "ARK",
    "SAFE", "KNC", "TREE", "KAVA", "ALICE", "INIT", "XLM", "THE", "TRX", "COW", "SCR", "HYPER",
    "GTC", "WCT", "UXLINK", "CELO", "AXL", "NIL", "ICNT", "NEWT", "SEI", "POL", "SAND", "LISTA",
    "ZRX", "PERP", "STORJ", "POPCAT", "1INCH", "SAGA", "BEL", "GLM", "HBAR", "DOGE", "KERNEL",
    "OM", "DYM", "PARTI", "PNUT", "MANTA", "FLUX", "MAGIC", "SONIC", "CFX", "IOTA", "JOE", "ZETA",
    "MINA", "PYTH", "SXP", "ONG", "ID", "STG", "YALA", "SAPIEN", "POWR", "YGG", "LUNA", "HAEDAL",
    "TA", "EDU", "MOODENG", "BB", "POLYX", "STEEM", "ICX", "AI", "STRK", "SYN", "COOKIE", "MOVE",
    "MERL", "TNSR", "HOOK", "BICO", "AIXBT", "NTRN", "CATI", "AI16Z", "SAHARA", "1000FLOKI",
    "STO", "CUDIS", "AEVO", "GRT", "CETUS", "FIDA", "KAS", "W", "GOAT", "IN", "SLERF", "HFT",
    "SXT", "CGPT", "BLUR", "CTSI", "SIGN", "CHESS", "MAV", "VELVET", "WOO", "MOCA", "NFP", "OGN",
    "USUAL", "ZK", "1000LUNC", "KMNO", "DAM", "RIF", "RARE", "BIGTIME", "COTI", "C98", "XAI",
    "BRETT", "TANSSI", "ATA", "SOLV", "PORTAL", "CHILLGUY", "GMT", "CHZ", "ACT", "ALT", "GRIFFAIN",
    "SOPH", "H", "SKL", "PIXEL", "TRU", "FLM", "HUMA", "NKN", "AVAAI", "ROSE", "KOMA", "1000BONK",
    "ARPA", "RDNT", "WAXP", "ACH", "FIO", "1000RATS", "PEOPLE", "ARC", "T", "GALA", "ANIME",
    "ALPHA", "JASMY", "USTC", "TOKEN", "1000SHIB", "G", "ZIL", "ONE", "1000PEPE", "CELR", "CKB",
    "PUMP", "IOST", "MEME"
]]

# ==== Các hàm scan gốc ====
def scan_rsi_15m_under30():
    return scan(symbols, Client.KLINE_INTERVAL_15MINUTE, 30, "lt")

def scan_rsi_15m_over70():
    return scan(symbols, Client.KLINE_INTERVAL_15MINUTE, 70, "gt")

def scan_rsi_h4_under30():
    return scan(symbols, Client.KLINE_INTERVAL_4HOUR, 30, "lt")

def scan_rsi_h4_over70():
    return scan(symbols, Client.KLINE_INTERVAL_4HOUR, 70, "gt")

def scan(symbols, interval, threshold, mode):
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, interval, threshold, mode): s for s in symbols}
        for f in as_completed(futures):
            r = f.result()
            if r: results.append(r)
    return sorted(results, key=lambda x: x['rsi'], reverse=(mode=="gt"))

def process_symbol(symbol, interval, threshold, mode):
    try:
        klines = client.futures_klines(symbol=symbol, interval=interval, limit=50)
        closes = pd.Series([float(k[4]) for k in klines])
        rsi = calculate_rsi(closes).iloc[-1]
        if (mode=="lt" and rsi < threshold) or (mode=="gt" and rsi > threshold):
            return {"symbol": symbol, "rsi": rsi}
    except Exception as e:
        print(f"Lỗi {symbol}: {e}")
    return None

# ==== Các hàm bổ sung (RSI 15m+4h đồng thời) ====
def scan_rsi_both_under30():
    results = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(process_symbol_both, symbol, "lt"): symbol for symbol in symbols}
        for f in as_completed(futures):
            r = f.result()
            if r: results.append(r)
    return sorted(results, key=lambda x: x['rsi_4h'])

def scan_rsi_both_over70():
    results = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(process_symbol_both, symbol, "gt"): symbol for symbol in symbols}
        for f in as_completed(futures):
            r = f.result()
            if r: results.append(r)
    return sorted(results, key=lambda x: x['rsi_4h'], reverse=True)

def process_symbol_both(symbol, mode):
    try:
        klines_15m = client.futures_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
        closes_15m = pd.Series([float(k[4]) for k in klines_15m])
        rsi_15m = calculate_rsi(closes_15m).iloc[-1]

        klines_4h = client.futures_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_4HOUR, limit=50)
        closes_4h = pd.Series([float(k[4]) for k in klines_4h])
        rsi_4h = calculate_rsi(closes_4h).iloc[-1]

        if (mode=="lt" and rsi_15m < 30 and rsi_4h < 30) or \
           (mode=="gt" and rsi_15m > 70 and rsi_4h > 70):
            return {"symbol": symbol.upper(), "rsi_15m": round(rsi_15m, 2), "rsi_4h": round(rsi_4h, 2)}
    except Exception as e:
        print(f"Lỗi xử lý {symbol}: {e}")
    return None

# ==== Telegram Bot ====
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("15m RSI <30", callback_data="rsi_15m_lt30"),
         InlineKeyboardButton("15m RSI >70", callback_data="rsi_15m_gt70")],
        [InlineKeyboardButton("H4 RSI <30", callback_data="rsi_h4_lt30"),
         InlineKeyboardButton("H4 RSI >70", callback_data="rsi_h4_gt70")],
        [InlineKeyboardButton("15m&4h <30", callback_data="rsi_both_lt30"),
         InlineKeyboardButton("15m&4h >70", callback_data="rsi_both_gt70")]
    ]
    await update.message.reply_text("Scan RSI :", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "rsi_15m_lt30": results = scan_rsi_15m_under30()
    elif choice == "rsi_15m_gt70": results = scan_rsi_15m_over70()
    elif choice == "rsi_h4_lt30": results = scan_rsi_h4_under30()
    elif choice == "rsi_h4_gt70": results = scan_rsi_h4_over70()
    elif choice == "rsi_both_lt30": results = scan_rsi_both_under30()
    elif choice == "rsi_both_gt70": results = scan_rsi_both_over70()
    else: results = []

    text = "\n".join([
        f"{r.get('symbol', '?')}: 15m={r.get('rsi_15m', r.get('rsi','?')):.1f}, 4h={r.get('rsi_4h', r.get('rsi','?')):.1f}"
        for r in results[:10]
    ]) or "No results found."
    await query.edit_message_text(f"{choice}:\n{text}")

# ==== Run bot ====
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", menu))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CallbackQueryHandler(button_callback))
app.run_polling()
