import ccxt
import pandas as pd
import time
import threading
import concurrent.futures
import streamlit as st
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import date, datetime

==========================================

1. SMC STATE MACHINE & DATA CLASSES

==========================================

class SMCState(Enum):
WAIT_FOR_LEVELS = "WAIT_FOR_LEVELS"
WATCH_BREAK = "WATCH_BREAK"
WAIT_CONFIRMATION = "WAIT_CONFIRMATION"
ENTRY_READY = "ENTRY_READY"

@dataclass
class SignalResult:
symbol: str
direction: str
entry_price: float
stop_loss: float
take_profit: float
position_size: float  # Added Risk Management
timestamp: pd.Timestamp

@dataclass
class CoinStateTracker:
state: SMCState = SMCState.WAIT_FOR_LEVELS
direction: Optional[str] = None
pdh: float = 0.0
pdl: float = 0.0
wait_candles: int = 0
conf_candle_high: float = 0.0
conf_candle_low: float = 0.0

last_processed_time: Optional[pd.Timestamp] = None  
current_date: Optional[date] = None  
trade_taken_pdl: bool = False  
trade_taken_pdh: bool = False  
daily_loss_count: int = 0  # Added Risk Management

==========================================

2. RISK MANAGEMENT & ALERTS

==========================================

ACCOUNT_BALANCE = 1000.0  # Base capital
RISK_PER_TRADE_PERCENT = 1.0  # 1% risk per trade
MAX_DAILY_LOSSES = 2

def calculate_position_size(entry: float, sl: float) -> float:
risk_amount = ACCOUNT_BALANCE * (RISK_PER_TRADE_PERCENT / 100)
sl_distance = abs(entry - sl)
if sl_distance == 0: return 0.0
qty = risk_amount / sl_distance
return round(qty, 4)

def trigger_pro_alerts(msg: str):
# Dummy implementation for your actual system
print(f"🔔 [TELEGRAM/DISCORD]: {msg}")

def play_tts_voice(direction: str, symbol: str):
# Dummy implementation
print(f"🔊 [TTS]: '{direction} signal generated for {symbol}'")

def trigger_vibration():
# Dummy implementation
print("📳 [VIBRATION]: Bzzzz!")

==========================================

3. THE INSTITUTIONAL SMC ENGINE

==========================================

class SMCStrategyEngine:
def init(self, max_wait_candles: int = 5):
self.trackers: Dict[str, CoinStateTracker] = {}
self.max_wait_candles = max_wait_candles

def get_tracker(self, symbol: str) -> CoinStateTracker:  
    if symbol not in self.trackers:  
        self.trackers[symbol] = CoinStateTracker()  
    return self.trackers[symbol]  

def reset_tracker_for_signal_expire(self, symbol: str):  
    tracker = self.get_tracker(symbol)  
    tracker.state = SMCState.WATCH_BREAK  
    tracker.direction = None  
    tracker.wait_candles = 0  

def calculate_daily_levels(self, symbol: str, df_daily: pd.DataFrame, current_time: pd.Timestamp):  
    if len(df_daily) < 2: return  
          
    tracker = self.get_tracker(symbol)  
    current_date = current_time.date()  
      
    # New Day Reset  
    if tracker.current_date != current_date:  
        tracker.current_date = current_date  
        tracker.trade_taken_pdl = False  
        tracker.trade_taken_pdh = False  
        tracker.daily_loss_count = 0  
        tracker.state = SMCState.WATCH_BREAK   
          
    yesterday_candle = df_daily.iloc[-2]  
    tracker.pdh = float(yesterday_candle['high'])  
    tracker.pdl = float(yesterday_candle['low'])  

def process_m1_candle(self, symbol: str, df_m1: pd.DataFrame) -> Optional[SignalResult]:  
    if len(df_m1) < 2: return None  
          
    tracker = self.get_tracker(symbol)  
    if tracker.state == SMCState.WAIT_FOR_LEVELS or tracker.pdh == 0.0: return None  
    if tracker.daily_loss_count >= MAX_DAILY_LOSSES: return None # Risk Filter  

    last_closed = df_m1.iloc[-2]  
    current_time = last_closed.name  

    if tracker.last_processed_time == current_time: return None  
    tracker.last_processed_time = current_time  

    high = float(last_closed['high'])  
    low = float(last_closed['low'])  
    close = float(last_closed['close'])  
    open_price = float(last_closed['open'])  
      
    # 1. FIXED BUY/SELL LOGIC (True Liquidity Sweep)  
    if tracker.state == SMCState.WATCH_BREAK:  
        if low < tracker.pdl and close > tracker.pdl and not tracker.trade_taken_pdl:  
            tracker.direction = 'BUY'  
            tracker.state = SMCState.WAIT_CONFIRMATION  
            tracker.wait_candles = 0  
            return None  
        elif high > tracker.pdh and close < tracker.pdh and not tracker.trade_taken_pdh:  
            tracker.direction = 'SELL'  
            tracker.state = SMCState.WAIT_CONFIRMATION  
            tracker.wait_candles = 0  
            return None  

    elif tracker.state == SMCState.WAIT_CONFIRMATION:  
        tracker.wait_candles += 1  
        if tracker.wait_candles > self.max_wait_candles:  
            self.reset_tracker_for_signal_expire(symbol)  
            return None  

        is_green = close > open_price  
        is_red = close < open_price  

        if (tracker.direction == 'BUY' and is_green) or (tracker.direction == 'SELL' and is_red):  
            tracker.conf_candle_high = high  
            tracker.conf_candle_low = low  
            tracker.state = SMCState.ENTRY_READY  
            tracker.wait_candles = 0  

    elif tracker.state == SMCState.ENTRY_READY:  
        tracker.wait_candles += 1  
        if tracker.wait_candles > self.max_wait_candles:  
            self.reset_tracker_for_signal_expire(symbol)  
            return None  

        if tracker.direction == 'BUY' and high > tracker.conf_candle_high:  
            entry = tracker.conf_candle_high  
            sl = tracker.conf_candle_low  
            tp = max(tracker.pdh, entry + ((entry - sl) * 2.5))  
            pos_size = calculate_position_size(entry, sl)  
              
            tracker.trade_taken_pdl = True  
            tracker.state = SMCState.WATCH_BREAK  
            return SignalResult(symbol, 'BUY', entry, sl, tp, pos_size, current_time)  

        elif tracker.direction == 'SELL' and low < tracker.conf_candle_low:  
            entry = tracker.conf_candle_low  
            sl = tracker.conf_candle_high  
            tp = min(tracker.pdl, entry - ((sl - entry) * 2.5))  
            pos_size = calculate_position_size(entry, sl)  
              
            tracker.trade_taken_pdh = True  
            tracker.state = SMCState.WATCH_BREAK  
            return SignalResult(symbol, 'SELL', entry, sl, tp, pos_size, current_time)  
              
    return None

==========================================

4. MULTI-THREAD SCANNER & CACHING

==========================================

exchange = ccxt.kucoin({'enableRateLimit': True})
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
strategy_engine = SMCStrategyEngine()

Caching Dictionary (API রেট লিমিট বাঁচার জন্য)

d1_cache = {}
d1_last_fetch = {}

def get_cached_d1(symbol: str) -> pd.DataFrame:
now = time.time()
# Cache valid for 4 hours (14400 seconds)
if symbol not in d1_cache or (now - d1_last_fetch.get(symbol, 0)) > 14400:
daily_ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=3)
df_daily = pd.DataFrame(daily_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df_daily['timestamp'] = pd.to_datetime(df_daily['timestamp'], unit='ms')
df_daily.set_index('timestamp', inplace=True)
d1_cache[symbol] = df_daily
d1_last_fetch[symbol] = now
return d1_cache[symbol]

def process_single_coin(symbol: str):
try:
df_daily = get_cached_d1(symbol)

m1_ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=5)  
    df_m1 = pd.DataFrame(m1_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])  
    df_m1['timestamp'] = pd.to_datetime(df_m1['timestamp'], unit='ms')  
    df_m1.set_index('timestamp', inplace=True)  
    current_time = df_m1.index[-1]  

    strategy_engine.calculate_daily_levels(symbol, df_daily, current_time)  
    signal = strategy_engine.process_m1_candle(symbol, df_m1)  

    if signal:  
        msg = f"🚀 [{signal.direction}] {signal.symbol} | Entry: {signal.entry_price} | SL: {signal.stop_loss} | TP: {signal.take_profit} | Qty: {signal.position_size}"  
          
        # Update global state for Streamlit UI  
        st.session_state.alerts.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")  
          
        # Trigger Hardware/OS Alerts  
        trigger_pro_alerts(msg)  
        play_tts_voice(signal.direction, signal.symbol)  
        trigger_vibration()  
          
except Exception as e:  
    print(f"API Error {symbol}: {e}")

def background_scanner_loop():
while st.session_state.scanner_running:
# ThreadPool for parallel fetching (Fast Execution)
with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols)) as executor:
executor.map(process_single_coin, symbols)
time.sleep(15) # Wait before next poll

==========================================

5. STREAMLIT UI (NON-BLOCKING)

==========================================

st.set_page_config(page_title="Institutional Bot", layout="wide")

if 'alerts' not in st.session_state:
st.session_state.alerts = []
if 'scanner_running' not in st.session_state:
st.session_state.scanner_running = False

st.title("⚡ SMC Institutional Trading Bot")

col1, col2 = st.columns([1, 2])

with col1:
st.write("### Control Panel")
if not st.session_state.scanner_running:
if st.button("▶ Start Engine", use_container_width=True):
st.session_state.scanner_running = True
# Daemon thread prevents Streamlit UI freeze
threading.Thread(target=background_scanner_loop, daemon=True).start()
st.rerun()
else:
if st.button("⏹ Stop Engine", type="primary", use_container_width=True):
st.session_state.scanner_running = False
st.rerun()

st.metric("Risk Per Trade", f"{RISK_PER_TRADE_PERCENT}%")  
st.metric("Base Capital", f"${ACCOUNT_BALANCE}")

with col2:
st.write("### 🟢 Live Signal Feed")
# Refresh button (If using streamlit-autorefresh, this can be automated)
st.button("🔄 Refresh Logs")

log_container = st.container(height=400)  
with log_container:  
    if not st.session_state.alerts:  
        st.info("Scanner is monitoring... waiting for setups.")  
    else:  
        for alert in st.session_state.alerts[:15]:  
            if "BUY" in alert: st.success(alert)  
            elif "SELL" in alert: st.error(alert)  
            else: st.text(alert)
