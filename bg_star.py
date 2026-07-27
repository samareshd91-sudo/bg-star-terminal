import streamlit as st
import streamlit.components.v1 as components
import os
import logging
import requests
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

# ==========================================
# 1. Cloud-Safe Logging Setup
# ==========================================

logger = logging.getLogger("pure_blueprint_final")
logger.setLevel(logging.INFO)
if not logger.handlers:
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

st.set_page_config(page_title="Pure Blueprint Pro + MTF Whale Info", layout="wide")
st_autorefresh(interval=15000, key="bot_refresh") # 15 Seconds Refresh

# ==========================================
# 2. Telegram Bot Setup (Secure)
# ==========================================

try:
    TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
except:
    TELEGRAM_BOT_TOKEN = "YOUR_NEW_SECURE_BOT_TOKEN" # Fallback

TELEGRAM_CHAT_ID = "8614370967" # আপনার আসল চ্যাট আইডি

def send_telegram(message):
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "YOUR_REAL_CHAT_ID":
        logger.warning("Telegram Chat ID is not set correctly! Messages will not be sent.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"  
    try:  
        response = requests.post(  
            url,  
            data={  
                "chat_id": TELEGRAM_CHAT_ID,  
                "text": message  
            },  
            timeout=5  
        )  
          
        try:  
            res_data = response.json()  
            is_ok = res_data.get("ok", False)  
        except ValueError:  
            logger.error(f"Invalid Telegram response (Not JSON): {response.text}")  
            return  

        if response.status_code == 200 and is_ok:  
            logger.info("Telegram message sent successfully.")  
        else:  
            logger.error(f"Telegram API Error {response.status_code}: {response.text}")  
              
    except Exception as e:  
        logger.error(f"Telegram sending failed: {e}")

# ==========================================
# 3. Session State & Memory
# ==========================================

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

# ==========================================
# 4. Alert Engine (Updated with Timeframe)
# ==========================================

STATIC_DIR = Path(__file__).parent.absolute() / "static"
WEB_AUDIO_PATH = "app/static/alert.mp3" if os.path.exists("/mount/src/app/static/alert.mp3") else "static/alert.mp3"

def trigger_pro_alerts(coin, timeframe, direction, entry, delay_index=0):
    flash_color = "rgba(0, 255, 170, 0.3)" if direction == "BUY" else "rgba(255, 68, 68, 0.3)"
    safe_coin = coin.replace("/", "")
    audio_id = f"alarm_{safe_coin}_{timeframe}_{direction}"
    ls_key = f"lastSMCAlert_{safe_coin}_{timeframe}_{direction}"
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
                const sigKey = "{coin}_{timeframe}_{direction}_{entry}";  
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
                            let msg = new SpeechSynthesisUtterance("Blueprint Pro {direction} signal on {safe_coin} {timeframe}");  
                            window.speechSynthesis.speak(msg);  
                        }}  
                        if ("Notification" in window && Notification.permission === "granted") {{  
                            new Notification("🎯 Blueprint MTF: {coin} {timeframe} {direction}", {{ body: "Entry: {entry}" }});  
                        }}  
                    }} catch (e) {{}}  
                }}  
            }} catch (e) {{ console.error("Alert Error:", e); }}  
        }}, {js_delay});  
    </script>  
    """  
    components.html(js_code, height=0, width=0)

# ==========================================
# 5. API Caching (Dynamic TTL per Timeframe) 🚀
# ==========================================

@st.cache_resource
def get_exchange(exchange_id: str):
    return getattr(ccxt, exchange_id)({'enableRateLimit': True, 'timeout': 5000})

def fetch_data_core(exchange_id: str, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
    try:
        exchange = get_exchange(exchange_id)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        logger.error(f"Error fetching {symbol} {timeframe}: {e}")
        return None

# ✅ Dynamic TTL Wrappers
@st.cache_data(ttl=3600, show_spinner=False) # 1 Hour cache for Daily
def fetch_1d(exchange_id, symbol, limit): return fetch_data_core(exchange_id, symbol, '1d', limit)

@st.cache_data(ttl=15, show_spinner=False) # 15s cache for 1M
def fetch_1m(exchange_id, symbol, limit): return fetch_data_core(exchange_id, symbol, '1m', limit)

@st.cache_data(ttl=30, show_spinner=False) # 30s cache for 5M
def fetch_5m(exchange_id, symbol, limit): return fetch_data_core(exchange_id, symbol, '5m', limit)

@st.cache_data(ttl=60, show_spinner=False) # 60s cache for 15M
def fetch_15m(exchange_id, symbol, limit): return fetch_data_core(exchange_id, symbol, '15m', limit)

# ==========================================
# 6. Pure Blueprint MTF Engine
# ==========================================

@dataclass
class PureBlueprintSetup:
    symbol: str
    timeframe: str
    direction: str
    entry_price: float
    sl: float
    tp: float
    setup_type: str
    delta_status: str

class PureBlueprintEngineFinal:
    def __init__(self, exchange_id='kucoin'):
        self.exchange_id = exchange_id
        self.WHALE_MULTIPLIER = 2.0

    def approx_delta(self, df: pd.DataFrame) -> float:  
        buy_pressure = df['close'] - df['low']  
        sell_pressure = df['high'] - df['close']  
        total_pressure = buy_pressure + sell_pressure + 1e-9  
        delta = df['volume'] * ((buy_pressure - sell_pressure) / total_pressure)  
        return delta.sum()  

    def _scan_timeframe(self, symbol: str, df_tf: pd.DataFrame, pdh: float, pdl: float, tf_name: str) -> List[PureBlueprintSetup]:  
        # ✅ Volume 30 Moving Average (More Stable)  
        df_tf['vol_avg'] = df_tf['volume'].rolling(30, min_periods=30).mean().fillna(0)  
        last_close = df_tf['close'].iloc[-2]   
        valid_setups = []  

        # =========================================================  
        # BUY LOGIC  
        # =========================================================  
        buy_triggered = False  
        for i in range(len(df_tf) - 30, len(df_tf) - 2):  
            tf_close = df_tf['close'].iloc[i]  
              
            if tf_close < pdl:  
                sweep_distance = (pdl - tf_close) / pdl  
                if sweep_distance >= 0.0008:   
                      
                    for j in range(i + 1, len(df_tf) - 1):   
                        is_green = df_tf['close'].iloc[j] > df_tf['open'].iloc[j]  
                          
                        if is_green:  
                            green_high = df_tf['high'].iloc[j]  
                            green_low = df_tf['low'].iloc[j]  
                              
                            whale_entered = (df_tf['volume'].iloc[i] > df_tf['vol_avg'].iloc[i] * self.WHALE_MULTIPLIER) or \
                                            (df_tf['volume'].iloc[j] > df_tf['vol_avg'].iloc[j] * self.WHALE_MULTIPLIER)  
                              
                            if whale_entered:  
                                if last_close > green_high:  
                                    entry = last_close    
                                    sl = green_low * 0.9998              
                                      
                                    risk = entry - sl  
                                    tp = entry + (risk * 2)   
                                      
                                    delta_value = self.approx_delta(df_tf.iloc[i:j+1])  
                                    delta_status = "🟢 Approx Delta Positive" if delta_value > 0 else "🔴 Approx Delta Negative (Info)"  
                                      
                                    if risk > 0 and (entry - sl) / entry < 0.015 and tp > entry:   
                                        valid_setups.append(PureBlueprintSetup(  
                                            symbol, tf_name, "BUY", round(entry, 4), round(sl, 4), round(tp, 4),   
                                            f"Pro Blueprint: 0.08% Sweep + Vol ({self.WHALE_MULTIPLIER}x)", delta_status  
                                        ))  
                                        buy_triggered = True  
                                        break  
                    if buy_triggered: break  

        # =========================================================  
        # SELL LOGIC  
        # =========================================================  
        sell_triggered = False  
        for i in range(len(df_tf) - 30, len(df_tf) - 2):  
            tf_close = df_tf['close'].iloc[i]  
              
            if tf_close > pdh:  
                sweep_distance = (tf_close - pdh) / pdh  
                if sweep_distance >= 0.0008:   
                      
                    for j in range(i + 1, len(df_tf) - 1):  
                        is_red = df_tf['close'].iloc[j] < df_tf['open'].iloc[j]  
                          
                        if is_red:  
                            red_high = df_tf['high'].iloc[j]  
                            red_low = df_tf['low'].iloc[j]  
                              
                            whale_entered = (df_tf['volume'].iloc[i] > df_tf['vol_avg'].iloc[i] * self.WHALE_MULTIPLIER) or \
                                            (df_tf['volume'].iloc[j] > df_tf['vol_avg'].iloc[j] * self.WHALE_MULTIPLIER)  
                              
                            if whale_entered:  
                                if last_close < red_low:  
                                    entry = last_close    
                                    sl = red_high * 1.0002              
                                      
                                    risk = sl - entry  
                                    tp = entry - (risk * 2)  
                                      
                                    delta_value = self.approx_delta(df_tf.iloc[i:j+1])  
                                    delta_status = "🔴 Approx Delta Negative" if delta_value < 0 else "🟢 Approx Delta Positive (Info)"  
                                      
                                    if risk > 0 and (sl - entry) / entry < 0.015 and tp < entry:   
                                        valid_setups.append(PureBlueprintSetup(  
                                            symbol, tf_name, "SELL", round(entry, 4), round(sl, 4), round(tp, 4),   
                                            f"Pro Blueprint: 0.08% Sweep + Vol ({self.WHALE_MULTIPLIER}x)", delta_status  
                                        ))  
                                        sell_triggered = True  
                                        break  
                    if sell_triggered: break  

        return valid_setups  

    def execute_engine(self, symbol: str) -> List[PureBlueprintSetup]:  
        df_1d = fetch_1d(self.exchange_id, symbol, limit=5)  
        if df_1d is None or len(df_1d) < 2:  
            return []  

        pdl = df_1d['low'].iloc[-2]  
        pdh = df_1d['high'].iloc[-2]  

        all_valid_setups = []  
          
        # ✅ Fetch using Dynamic Cache TTL Wrappers  
        timeframes_to_scan = [("1m", "1M", fetch_1m), ("5m", "5M", fetch_5m), ("15m", "15M", fetch_15m)]  
          
        for tf_param, tf_name, fetch_func in timeframes_to_scan:  
            df_tf = fetch_func(self.exchange_id, symbol, limit=200)  
            if df_tf is not None and len(df_tf) >= 30:  
                tf_setups = self._scan_timeframe(symbol, df_tf, pdh, pdl, tf_name)  
                all_valid_setups.extend(tf_setups)  

        return all_valid_setups

engine = PureBlueprintEngineFinal()

# ==========================================
# 7. Parallel Scanning & Dashboard UI
# ==========================================

st.title("🎯 Pure Blueprint Pro + MTF Volatility Info")
st.markdown("Filters: D1 H/L Sweep ➔ Reversal Candle ➔ Vol Spike (>2.0x) ➔ Breakout (Dynamic 1:2 RR)")

COINS_TO_SCAN = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

def scan_symbol(symbol):
    try:
        setups = engine.execute_engine(symbol)
        if setups:
            return [{
                "coin": s.symbol,
                "timeframe": s.timeframe,
                "direction": s.direction,
                "entry": s.entry_price,
                "sl": s.sl,
                "tp": s.tp,
                "type": s.setup_type,
                "delta": s.delta_status
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

# ==========================================
# 8. Signal Execution & UI Rendering
# ==========================================

if detected_signals:
    for index, sig in enumerate(detected_signals):
        coin, tf, direction, entry = sig["coin"], sig["timeframe"], sig["direction"], sig["entry"]
        sl, tp, sig_type, delta_status = sig["sl"], sig["tp"], sig["type"], sig["delta"]

        current_signal_id = f"{coin}_{tf}_{direction}_{entry}"  
        cooldown_key = f"{coin}_{tf}_{direction}"  
          
        is_cooled_down = True  
        if cooldown_key in st.session_state.signal_cooldowns:  
            if datetime.now() < st.session_state.signal_cooldowns[cooldown_key] + timedelta(minutes=5):   
                is_cooled_down = False  
                  
        if current_signal_id not in st.session_state.triggered_set and is_cooled_down:  
            color_emoji = "🟩" if direction == "BUY" else "🟥"  
              
            st.success(f"{color_emoji} **{sig_type}** | **{coin} | {tf}** | Dir: **{direction}**")  
            st.warning(f"📊 **High Activity Noted:** Volume > {engine.WHALE_MULTIPLIER}x | {delta_status}")  
              
            st.markdown(f"""  
            - **Breakout Entry:** `{entry}` (Triggered by {tf} close)  
            - **Stop Loss (SL):** `{sl}` (Reversal Extreme + Buffer)  
            - **Take Profit (TP):** `{tp}` (Dynamic 1:2 Risk/Reward)  
            """)  
              
            send_telegram(  
                f"🎯 {coin}\n"  
                f"Timeframe: {tf}\n"  
                f"Signal: {direction}\n"  
                f"Entry: {entry}\n"  
                f"SL: {sl}\n"  
                f"TP: {tp}\n"  
                f"{delta_status}"  
            )  
              
            trigger_pro_alerts(coin, tf, direction, entry, delay_index=index)  
              
            if len(st.session_state.trigger_history) == MAX_HISTORY:  
                oldest_sig = st.session_state.trigger_history.popleft()  
                st.session_state.triggered_set.discard(oldest_sig)  
                  
            st.session_state.trigger_history.append(current_signal_id)  
            st.session_state.triggered_set.add(current_signal_id)  
            st.session_state.signal_cooldowns[cooldown_key] = datetime.now()

else:
    st.info(f"🎯 Pure Blueprint MTF Active: Monitoring 1M, 5M, 15M for >0.08% D1 Sweeps, >{engine.WHALE_MULTIPLIER}x Volatility & 1:2 RR...")
