import streamlit as st
import streamlit.components.v1 as components
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from collections import deque
from dataclasses import dataclass
from typing import Optional, List
import ccxt
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

==========================================

১. Cloud-Safe Logging Setup

==========================================

logger = logging.getLogger("pure_blueprint_final")
logger.setLevel(logging.INFO)
if not logger.handlers:
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

st.set_page_config(page_title="Pure Blueprint Final + Whale Info", layout="wide")
st_autorefresh(interval=30000, key="bot_refresh")

==========================================

২. Session State & Memory

==========================================

MAX_HISTORY = 300
if 'trigger_history' not in st.session_state:
st.session_state.trigger_history = deque(maxlen=MAX_HISTORY)
if 'triggered_set' not in st.session_state:
st.session_state.triggered_set = set()
if 'signal_cooldowns' not in st.session_state:
st.session_state.signal_cooldowns = {}

now = datetime.now()
expired_keys = [k for k, v in st.session_state.signal_cooldowns.items() if now - v > timedelta(minutes=30)]
for k in expired_keys:
del st.session_state.signal_cooldowns[k]

==========================================

৩. Alert Engine

==========================================

STATIC_DIR = Path(file).parent.absolute() / "static"
WEB_AUDIO_PATH = "app/static/alert.mp3" if os.path.exists("/mount/src/app/static/alert.mp3") else "static/alert.mp3"

def trigger_pro_alerts(coin, direction, entry, delay_index=0):
flash_color = "rgba(0, 255, 170, 0.3)" if direction == "BUY" else "rgba(255, 68, 68, 0.3)"
safe_coin = coin.replace("/", "")
audio_id = f"alarm_{safe_coin}{direction}"
ls_key = f"lastSMCAlert{safe_coin}_{direction}"
js_delay = delay_index * 2000

js_code = f"""  
<audio id="{audio_id}" preload="auto" style="display:none">  
    <source src="{WEB_AUDIO_PATH}" type="audio/mpeg">  
</audio>  
<script>  
    setTimeout(() => {{  
        try {{  
            const mainDoc = document;  
            const mainWindow = window;  
            const sigKey = "{coin}_{direction}_{entry}";  
            const lsKey = "{ls_key}";  
            let allowAlert = true;  

            if (!mainWindow.localStorage.getItem("notifAsked")) {{  
                if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();  
                mainWindow.localStorage.setItem("notifAsked", "1");  
            }}  

            try {{  
                if (mainWindow.localStorage.getItem(lsKey) === sigKey) allowAlert = false;  
                else mainWindow.localStorage.setItem(lsKey, sigKey);  
            }} catch (e) {{ allowAlert = true; }}  

            if (allowAlert) {{  
                try {{  
                    if (mainWindow.flashTimeout) clearTimeout(mainWindow.flashTimeout);  
                    if (!mainWindow.originalBgColor) mainWindow.originalBgColor = mainWindow.getComputedStyle(mainDoc.body).backgroundColor;  
                    mainDoc.body.style.transition = "background-color 0.3s ease";  
                    mainDoc.body.style.backgroundColor = "{flash_color}";  
                    mainWindow.flashTimeout = setTimeout(() => {{  
                        mainDoc.body.style.backgroundColor = mainWindow.originalBgColor;  
                        mainWindow.originalBgColor = null;  
                    }}, 2000);  
                }} catch (e) {{}}  

                try {{  
                    let audio = mainDoc.getElementById("{audio_id}");  
                    if (audio) {{  
                        audio.pause(); audio.currentTime = 0;  
                        audio.play().catch(e => console.log("Autoplay Blocked"));  
                        setTimeout(() => {{ audio.pause(); audio.currentTime = 0; }}, 5000);  
                    }}  
                }} catch (e) {{}}  

                try {{  
                    if ('speechSynthesis' in window) {{  
                        let msg = new SpeechSynthesisUtterance("Blueprint Final {direction} signal on {safe_coin}");  
                        window.speechSynthesis.speak(msg);  
                    }}  
                    if ("Notification" in window && Notification.permission === "granted") {{  
                        new Notification("🎯 Blueprint Pro: {coin} {direction}", {{ body: "Entry: {entry}" }});  
                    }}  
                }} catch (e) {{}}  
            }}  
        }} catch (e) {{ console.error("Alert Error:", e); }}  
    }}, {js_delay});  
</script>  
"""  
components.html(js_code, height=0, width=0)

==========================================

৪. API Caching

==========================================

@st.cache_data(ttl=30, show_spinner=False)
def fetch_data_safe(exchange_id: str, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
try:
exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True, 'timeout': 5000})
ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)
return df
except Exception as e:
logger.error(f"Error fetching {symbol} {timeframe}: {e}")
return None

==========================================

৫. Pure Blueprint Final Engine

==========================================

@dataclass
class PureBlueprintSetup:
symbol: str
direction: str
entry_price: float
sl: float
tp: float
setup_type: str
cvd_status: str

class PureBlueprintEngineFinal:
def init(self, exchange_id='kucoin'):
self.exchange_id = exchange_id
self.WHALE_MULTIPLIER = 1.6  # ✅ Configurable Whale Volume Multiplier

def approx_cvd(self, df: pd.DataFrame) -> float:  
    """CVD Proxy - Used for UI Information only, not as a hard block"""  
    buy_pressure = df['close'] - df['low']  
    sell_pressure = df['high'] - df['close']  
    total_pressure = buy_pressure + sell_pressure + 1e-9  
    delta = df['volume'] * ((buy_pressure - sell_pressure) / total_pressure)  
    return delta.sum()  

def execute_engine(self, symbol: str) -> List[PureBlueprintSetup]:  
    df_1d = fetch_data_safe(self.exchange_id, symbol, '1d', limit=5)  
    df_1m = fetch_data_safe(self.exchange_id, symbol, '1m', limit=100)  
      
    if df_1d is None or df_1m is None or len(df_1m) < 30:  
        return []  

    # 1. D1 High/Low Mark  
    pdh = df_1d['high'].iloc[-2]  
    pdl = df_1d['low'].iloc[-2]  

    # ✅ Added min_periods=20 to avoid initial NaNs  
    df_1m['vol_avg'] = df_1m['volume'].rolling(20, min_periods=20).mean()  
      
    # ✅ Using last_close for confirmation, current_price for entry execution  
    last_close = df_1m['close'].iloc[-2]  
    current_price = df_1m['close'].iloc[-1]  
      
    valid_setups = []  

    # =========================================================  
    # BUY LOGIC  
    # =========================================================  
    buy_triggered = False  
    for i in range(len(df_1m) - 30, len(df_1m) - 2): # Checking history excluding the last running candle  
        m1_close = df_1m['close'].iloc[i]  
          
        # 2. M1 Close < Daily Low & Min Sweep Distance (0.08%)  
        if m1_close < pdl:  
            sweep_distance = (pdl - m1_close) / pdl  
            if sweep_distance >= 0.0008:   
                  
                # 3. Wait for GREEN candle  
                for j in range(i + 1, len(df_1m) - 1): # Exclude the very last running candle from being the confirmation candle  
                    is_green = df_1m['close'].iloc[j] > df_1m['open'].iloc[j]  
                      
                    if is_green:  
                        green_high = df_1m['high'].iloc[j]  
                        green_low = df_1m['low'].iloc[j]  
                          
                        # ✅ Configurable Whale Volume Check  
                        whale_entered = (df_1m['volume'].iloc[i] > df_1m['vol_avg'].iloc[i] * self.WHALE_MULTIPLIER) or \  
                                        (df_1m['volume'].iloc[j] > df_1m['vol_avg'].iloc[j] * self.WHALE_MULTIPLIER)  
                          
                        if whale_entered:  
                            # ✅ 4. Last completed candle breaks green's High (No repainting)  
                            if last_close > green_high:  
                                entry = current_price  
                                # ✅ Added SL Buffer (0.02% safety from wick hunts)  
                                sl = green_low * 0.9998              
                                tp = pdh                    
                                  
                                cvd_value = self.approx_cvd(df_1m.iloc[i:j+1])  
                                cvd_status = "🟢 CVD Positive" if cvd_value > 0 else "🔴 CVD Negative (Info)"  
                                  
                                risk = entry - sl  
                                if risk > 0 and (entry - sl) / entry < 0.015:   
                                    valid_setups.append(PureBlueprintSetup(  
                                        symbol, "BUY", round(entry, 4), round(sl, 4), round(tp, 4),   
                                        f"Blueprint: 0.08% Sweep + Vol ({self.WHALE_MULTIPLIER}x)", cvd_status  
                                    ))  
                                    buy_triggered = True  
                                    break  
                if buy_triggered: break  

    # =========================================================  
    # SELL LOGIC  
    # =========================================================  
    sell_triggered = False  
    for i in range(len(df_1m) - 30, len(df_1m) - 2):  
        m1_close = df_1m['close'].iloc[i]  
          
        # 2. M1 Close > Daily High & Min Sweep Distance (0.08%)  
        if m1_close > pdh:  
            sweep_distance = (m1_close - pdh) / pdh  
            if sweep_distance >= 0.0008:   
                  
                # 3. Wait for RED candle  
                for j in range(i + 1, len(df_1m) - 1):  
                    is_red = df_1m['close'].iloc[j] < df_1m['open'].iloc[j]  
                      
                    if is_red:  
                        red_high = df_1m['high'].iloc[j]  
                        red_low = df_1m['low'].iloc[j]  
                          
                        # ✅ Configurable Whale Volume Check  
                        whale_entered = (df_1m['volume'].iloc[i] > df_1m['vol_avg'].iloc[i] * self.WHALE_MULTIPLIER) or \  
                                        (df_1m['volume'].iloc[j] > df_1m['vol_avg'].iloc[j] * self.WHALE_MULTIPLIER)  
                          
                        if whale_entered:  
                            # ✅ 4. Last completed candle breaks red's Low (No repainting)  
                            if last_close < red_low:  
                                entry = current_price  
                                # ✅ Added SL Buffer (0.02% safety from wick hunts)  
                                sl = red_high * 1.0002              
                                tp = pdl                   
                                  
                                cvd_value = self.approx_cvd(df_1m.iloc[i:j+1])  
                                cvd_status = "🔴 CVD Negative" if cvd_value < 0 else "🟢 CVD Positive (Info)"  
                                  
                                risk = sl - entry  
                                if risk > 0 and (sl - entry) / entry < 0.015:   
                                    valid_setups.append(PureBlueprintSetup(  
                                        symbol, "SELL", round(entry, 4), round(sl, 4), round(tp, 4),   
                                        f"Blueprint: 0.08% Sweep + Vol ({self.WHALE_MULTIPLIER}x)", cvd_status  
                                    ))  
                                    sell_triggered = True  
                                    break  
                if sell_triggered: break  

    return valid_setups

engine = PureBlueprintEngineFinal()

==========================================

৬. Parallel Scanning & Dashboard UI

==========================================

st.title("🎯 Pure Blueprint Final + Volatility Info")
st.markdown("Filters: D1 H/L Sweep (Min 0.08%) ➔ Reversal Candle ➔ High Vol Spike (>1.6x) ➔ Completed Breakout (CVD Info)")

COINS_TO_SCAN = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

def scan_symbol(symbol):
try:
setups = engine.execute_engine(symbol)
if setups:
return [{
"coin": s.symbol,
"direction": s.direction,
"entry": s.entry_price,
"sl": s.sl,
"tp": s.tp,
"type": s.setup_type,
"cvd": s.cvd_status
} for s in setups]
except Exception as e:
logger.error(f"Error scanning {symbol}: {e}")
return []

detected_signals = []
max_workers = min(5, len(COINS_TO_SCAN))

with ThreadPoolExecutor(max_workers=max_workers) as executor:
futures = {executor.submit(scan_symbol, coin): coin for coin in COINS_TO_SCAN}
try:
for future in as_completed(futures, timeout=15):
res_list = future.result()
if res_list:
detected_signals.extend(res_list)
except TimeoutError:
logger.warning("Scanner batch timeout.")
except Exception as e:
logger.warning(f"Scanner batch issue: {e}")

==========================================

৭. Signal Execution & UI Rendering

==========================================

if detected_signals:
for index, sig in enumerate(detected_signals):
coin, direction, entry = sig["coin"], sig["direction"], sig["entry"]
sl, tp, sig_type, cvd_status = sig["sl"], sig["tp"], sig["type"], sig["cvd"]

current_signal_id = f"{coin}_{direction}_{entry}"  
    cooldown_key = f"{coin}_{direction}"  
      
    is_cooled_down = True  
    if cooldown_key in st.session_state.signal_cooldowns:  
        if datetime.now() < st.session_state.signal_cooldowns[cooldown_key] + timedelta(minutes=5): # 5 min cooldown  
            is_cooled_down = False  
              
    if current_signal_id not in st.session_state.triggered_set and is_cooled_down:  
        color_emoji = "🟩" if direction == "BUY" else "🟥"  
        st.success(f"{color_emoji} **{sig_type}** | **{coin}** | Dir: **{direction}**")  
          
        # CVD Info Alert  
        st.warning(f"📊 **High Activity Noted:** Volume > {engine.WHALE_MULTIPLIER}x | {cvd_status}")  
          
        st.markdown(f"""  
        - **Live Entry:** `{entry}` (Triggered by previous closed candle)  
        - **Stop Loss (SL):** `{sl}` (Reversal Extreme + Buffer)  
        - **Take Profit (TP):** `{tp}` (Opposite D1 Range)  
        """)  
          
        trigger_pro_alerts(coin, direction, entry, delay_index=index)  
          
        if len(st.session_state.trigger_history) == MAX_HISTORY:  
            oldest_sig = st.session_state.trigger_history.popleft()  
            st.session_state.triggered_set.discard(oldest_sig)  
              
        st.session_state.trigger_history.append(current_signal_id)  
        st.session_state.triggered_set.add(current_signal_id)  
        st.session_state.signal_cooldowns[cooldown_key] = datetime.now()

else:
st.info("🎯 Pure Blueprint Final Active: Monitoring for >0.08% D1 Sweeps and >1.6x Volatility Spikes...")
