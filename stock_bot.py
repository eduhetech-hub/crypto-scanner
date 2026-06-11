import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "8214436158:AAHwQhLD2_EtkC01dOzrljOsk5x-ddUMWro"
TELEGRAM_CHAT_ID = "1860540903"

# Top 10 High-Liquidity US Stocks & ETFs
WATCHLIST = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", 
    "AMD", "TSLA", "AMZN", "META", "JPM"
]

ACCOUNT_SIZE = 10000      # Your total trading capital in USD
RISK_PER_TRADE = 0.01     # 1% risk per trade
# ==========================================

def calculate_atr(data, window=14):
    high, low, close = data['High'], data['Low'], data['Close']
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    return 100 - (100 / (1 + (gain / loss)))

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
        print("✅ Stock signal sent to Telegram successfully!")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def scan_stocks():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🔍 Running Institutional Stock Scanner for {today_str}...\n")
    
    # 1. MACRO REGIME FILTER: Check S&P 500 (SPY) 200 EMA
    spy_data = yf.download("SPY", period="1y", progress=False)    spy_ema200 = spy_data['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
    spy_current = spy_data['Close'].iloc[-1]
    macro_bullish = spy_current > spy_ema200
    
    if not macro_bullish:
        print("⚠️ MACRO WARNING: S&P 500 is below its 200-day EMA. Market is bearish.")
        msg = f"🚨 *STOCK MARKET REGIME ALERT* 🚨\n"
        msg += f"📅 Date: {today_str}\n"
        msg += f"📉 *SPY Status:* Bearish (Below 200 EMA)\n"
        msg += "🛑 *Action:* NO TRADES. The macro trend is down. Protect capital and wait."
        send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)
        return

    valid_signals = []

    for ticker in WATCHLIST:
        time.sleep(1.5) # Prevent API rate limits
        try:
            df = yf.download(ticker, period="1y", progress=False)
            if len(df) < 200: continue

            # Calculate Indicators
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            df['RSI'] = calculate_rsi(df, window=14)
            df['ATR'] = calculate_atr(df, window=14)
            df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
            df = df.dropna()

            # Extract previous candle data (Prevents repainting)
            prev_close = df['Close'].shift(1).iloc[-1]
            prev_ema50 = df['EMA_50'].shift(1).iloc[-1]
            prev_ema200 = df['EMA_200'].shift(1).iloc[-1]
            prev_rsi = df['RSI'].shift(1).iloc[-1]
            prev_volume = df['Volume'].shift(1).iloc[-1]
            prev_vol_sma = df['Vol_SMA_20'].shift(1).iloc[-1]
            
            current_atr = df['ATR'].iloc[-1]
            current_price = df['Close'].iloc[-1]
            current_open = df['Open'].iloc[-1]

            signal = None
            reasoning = ""

            # THE INSTITUTIONAL BUY LOGIC (Long Only)
            if (prev_ema50 > prev_ema200) and \
               (40 <= prev_rsi <= 55) and \
               (prev_close > current_open) and \
               (prev_volume > (1.2 * prev_vol_sma)):
                                signal = "🟢 LONG"
                entry = current_price
                stop_loss = entry - (2 * current_atr)
                take_profit = entry + (4 * current_atr) # 1:2 Risk/Reward
                reasoning = "Trend pullback to value + Volume spike + Bullish candle."

            if signal:
                risk_amount = ACCOUNT_SIZE * RISK_PER_TRADE
                risk_per_unit = abs(entry - stop_loss)
                position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
                
                valid_signals.append({
                    "ticker": ticker,
                    "signal": signal,
                    "entry": entry,
                    "stop": stop_loss,
                    "target": take_profit,
                    "size": position_size,
                    "risk_amt": risk_amount,
                    "reason": reasoning
                })
                print(f"✅ High-Expectancy Setup Found: {ticker}")
            else:
                print(f"⏳ No setup: {ticker}")

        except Exception as e:
            print(f"⚠️ Error scanning {ticker}: {e}")

    # Format Telegram Message
    msg = f"🚨 *INSTITUTIONAL STOCK SCANNER* 🚨\n"
    msg += f"📅 Date: {today_str}\n"
    msg += f"📊 *SPY Macro:* 🟢 Bullish (Above 200 EMA)\n"
    msg += f"💼 *Risk per Trade:* 1% (${ACCOUNT_SIZE * RISK_PER_TRADE:.0f})\n"
    msg += "──────────────────\n"

    if not valid_signals:
        msg += "⚠️ *NO HIGH-EXPECTANCY SETUPS TODAY.*\n"
        msg += "💡 *Action:* Cash is a position. Patience pays. Wait for the market."
    else:
        msg += f"🏆 *FOUND {len(valid_signals)} HIGH-PROBABILITY SETUP(S):*\n\n"
        for i, sig in enumerate(valid_signals, 1):
            msg += f"*{i}. {sig['ticker']}* ({sig['signal']})\n"
            msg += f"🎯 *Entry:* `${sig['entry']:,.2f}`\n"
            msg += f"🛑 *Stop Loss:* `${sig['stop']:,.2f}`\n"
            msg += f"💰 *Take Profit:* `${sig['target']:,.2f}` *(1:2 Risk/Reward)*\n"
            msg += f"📦 *Position Size:* `{sig['size']:.2f}` shares\n"
            msg += f"⚠️ *Capital at Risk:* `${sig['risk_amt']:.2f}`\n"
            msg += f"📝 *Logic:* {sig['reason']}\n"
            msg += "──────────────────\n"
        msg += "💡 *Execution:* Use your broker's Limit + Stop Loss orders."
    print("\n" + msg.replace("*", "").replace("`", ""))
    send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)

if __name__ == "__main__":
    scan_stocks()
