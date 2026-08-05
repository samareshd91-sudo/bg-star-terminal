import streamlit as st
import os
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ccxt
import pandas as pd
import numpy as np
import gc
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from apscheduler.schedulers.background import BackgroundScheduler

# ==========================================
# 1. PROPER LOGGING SETUP
# ==========================================
logger = logging.getLogger("balanced_scalper_v3")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(ch)

st.set_page_config(page_title="Balanced Pro Scalper v3 - Auto", layout="wide", page_icon="🎯")

# ==========================================
# 2. STABLE TELEGRAM SESSION
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

tg_session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
tg_session.mount('http://', adapter)
tg_session.mount('https://', adapter)

def send_telegram(msg):
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID": return
    try:
        tg_session.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, 
            timeout=5
        )
    except Exception as e: 
        logger.error(f"TG fail: {e}")

# ==========================================
# 3. THREAD-SAFE GLOBALS & CACHE
# ==========================================
COINS_TO_SCAN = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

# Thread-safe storage replacing st.session_state
COOLDOWNS = {}
SEEN_SIGS = set()
STATE_LOCK = threading.Lock()

# 1D Cache Storage
HTF_CACHE = {}
LAST_HTF_FETCH = 0
CACHE_LOCK = threading.Lock()

# Global flag to ensure scheduler strictly starts once
_SCHEDULER_RUNNING = False

# ==========================================
# 4. BALANCED SCALPER ENGINE (Thread-Safe)
# ==========================================
@dataclass
class Setup:
    coin: str; tf: str; dir: str; entry: float; sl: float; tp: float; type: str; d_stat: str; brk_time: pd.Timestamp

class Engine:
    def __init__(self):
        # EVERY WORKER GETS ITS OWN INDEPENDENT CCXT INSTANCE
        self.ex = ccxt.kucoin({'enableRateLimit': True, 'timeout': 10000})
        self.wm = 1.3  

    def fetch_with_retry(self, sym, tf, lim, retries=3):
        for attempt in range(retries):
            try:
                df = pd.DataFrame(self.ex.fetch_ohlcv(sym, tf, limit=lim), columns=['timestamp','open','high','low','close','volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df.set_index('timestamp')
            except Exception as e:
                logger.warning(f"Fetch err {sym} {tf}: {e}. Retry {attempt+1}/{retries}")
                time.sleep(2)
                try: self.ex.load_markets()
                except: pass
        return None

    def get_1d_cached(self, sym):
        global LAST_HTF_FETCH, HTF_CACHE
        
        with CACHE_LOCK:
            current_time = time.time()
            if current_time - LAST_HTF_FETCH > 3600:
                HTF_CACHE.clear()
                LAST_HTF_FETCH = current_time
                
            if sym not in HTF_CACHE:
                df = self.fetch_with_retry(sym, '1d', 5)
                if df is not None: 
                    HTF_CACHE[sym] = df
                    
            return HTF_CACHE.get(sym, None)
    
    def cal_indicators(self, df, p=14):
        df['TR'] = df[['high','low','close']].assign(hc=lambda x: (x.high-x.close.shift()).abs(), lc=lambda x: (x.low-x.close.shift()).abs(), hl=lambda x: x.high-x.low)[['hl','hc','lc']].max(axis=1)
        df['ATR'] = df['TR'].ewm(alpha=1/p, adjust=False).mean()
        
        um, dm = df['high'].diff(), -df['low'].diff()
        df['+DM'] = np.where((um>dm)&(um>0), um, 0)
        df['-DM'] = np.where((dm>um)&(dm>0), dm, 0)
        df['TR_s'] = df['TR'].ewm(alpha=1/p, adjust=False).mean()
        df['+DM_s'] = df['+DM'].ewm(alpha=1/p, adjust=False).mean()
        df['-DM_s'] = df['-DM'].ewm(alpha=1/p, adjust=False).mean()
        
        df['+DI'] = 100 * (df['+DM_s']/df['TR_s'])
        df['-DI'] = 100 * (df['-DM_s']/df['TR_s'])
        df['ADX'] = (100 * (abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI']+1e-9))).ewm(alpha=1/p, adjust=False).mean()
        
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        rs = gain.ewm(alpha=1/14, adjust=False).mean() / (loss.ewm(alpha=1/14, adjust=False).mean() + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    def _scan(self, sym, df, pdh, pdl, tf):
        df['v_avg'] = df['volume'].rolling(30, min_periods=30).mean().fillna(0)
        df = self.cal_indicators(df)
        l_idx, res = len(df)-2, []
        
        for i in range(len(df)-12, l_idx):
            if (l_idx - i) > 6: continue
            c = df['close'].iloc[i]
            
            # BUY LOGIC
            if c < pdl and (pdl - c) / pdl >= 0.0015:  
                for j in range(i+1, min(i+5, l_idx)):
                    if df['close'].iloc[j] > df['open'].iloc[j]:
                        conf_high = df['high'].iloc[j]
                        k = j + 1
                        if k + 1 < len(df) and df['close'].iloc[k] > conf_high and df['volume'].iloc[k] > df['v_avg'].iloc[k] * self.wm:
                            atr = df['ATR'].iloc[k]
                            if pd.isna(atr) or atr == 0: continue 
                            
                            entry_price = df['open'].iloc[k+1]
                            sl_price = df['low'].iloc[j] - (atr * 1.2)  
                            d_val = (df['volume'].iloc[i:k+1]*((df['close'].iloc[i:k+1]-df['low'].iloc[i:k+1])-(df['high'].iloc[i:k+1]-df['close'].iloc[i:k+1]))/(df['high'].iloc[i:k+1]-df['low'].iloc[i:k+1]+1e-9)).sum()
                            
                            if d_val > 0 and df['close'].iloc[k] > df['ema20'].iloc[k] and df['ADX'].iloc[k] >= 15 and df['rsi'].iloc[k] < 75:
                                tp_price = entry_price + (atr * 2.5) 
                                res.append(Setup(sym, tf, "BUY", round(entry_price, 4), round(sl_price, 4), round(tp_price, 4), "Balanced Scalper", "🟢 EMA20 UPTREND", df.index[k]))
                                break

            # SELL LOGIC
            if c > pdh and (c - pdh) / pdh >= 0.0015:  
                for j in range(i+1, min(i+5, l_idx)):
                    if df['close'].iloc[j] < df['open'].iloc[j]:
                        conf_low = df['low'].iloc[j]
                        k = j + 1
                        if k + 1 < len(df) and df['close'].iloc[k] < conf_low and df['volume'].iloc[k] > df['v_avg'].iloc[k] * self.wm:
                            atr = df['ATR'].iloc[k]
                            if pd.isna(atr) or atr == 0: continue 
                            
                            entry_price = df['open'].iloc[k+1]
                            sl_price = df['high'].iloc[j] + (atr * 1.2)  
                            d_val = (df['volume'].iloc[i:k+1]*((df['close'].iloc[i:k+1]-df['low'].iloc[i:k+1])-(df['high'].iloc[i:k+1]-df['close'].iloc[i:k+1]))/(df['high'].iloc[i:k+1]-df['low'].iloc[i:k+1]+1e-9)).sum()
                            
                            if d_val < 0 and df['close'].iloc[k] < df['ema20'].iloc[k] and df['ADX'].iloc[k] >= 15 and df['rsi'].iloc[k] > 25:
                                tp_price = entry_price - (atr * 2.5) 
                                res.append(Setup(sym, tf, "SELL", round(entry_price, 4), round(sl_price, 4), round(tp_price, 4), "Balanced Scalper", "🔴 EMA20 DOWNTREND", df.index[k]))
                                break
        return res

    def run(self, sym):
        d1 = self.get_1d_cached(sym)
        if d1 is None or len(d1) < 2: return []
        pdh, pdl, all_s = d1['high'].iloc[-2], d1['low'].iloc[-2], []
        
        for tp, tn, lim in [("1m","1M",200), ("5m","5M",200), ("15m","15M",200)]:
            df = self.fetch_with_retry(sym, tp, lim)
            if df is not None and len(df) >= 200: 
                all_s.extend(self._scan(sym, df, pdh, pdl, tn))
        return all_s

# Worker task function ensuring independent Engine per thread
def worker_task(coin):
    eng = Engine()
    return eng.run(coin)

# ==========================================
# 5. APSCHEDULER WORKER (Strictly Singleton)
# ==========================================
def scan_market_job():
    global COOLDOWNS, SEEN_SIGS
    logger.info("Executing scheduled Balanced Scalper scan...")
    try:
        sigs = []
        
        # Max 3 Workers, isolated CCXT instances
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = {ex.submit(worker_task, c): c for c in COINS_TO_SCAN}
            for f in as_completed(futures):
                try: sigs.extend(f.result() or [])
                except Exception as e: logger.error(f"Error scanning {futures[f]}: {e}")

        now = datetime.now()
        
        # Thread-safe cooldown cleanup
        with STATE_LOCK:
            keys_to_del = [k for k, v in COOLDOWNS.items() if now - v > timedelta(minutes=30)]
            for k in keys_to_del: del COOLDOWNS[k]

        mtf_c = {}
        for s in sigs: mtf_c.setdefault((s.coin, s.dir), set()).add(s.tf)

        if sigs:
            for s in sigs:
                c_k = f"{s.coin}_{s.tf}_{s.dir}"
                k = f"{c_k}_{s.brk_time}"
                
                with STATE_LOCK:
                    is_cool = c_k not in COOLDOWNS or now >= COOLDOWNS[c_k] + timedelta(minutes=5)
                    is_new = k not in SEEN_SIGS
                
                if is_cool and is_new:
                    hc = len(mtf_c[(s.coin, s.dir)]) == 3
                    tf_disp = "🔥 HIGH CONFIDENCE (1M+5M+15M)" if hc else s.tf
                    
                    msg = f"🚨 <b>Balanced Pro Scalper v3</b>\n\n"
                    msg += f"🪙 <b>Coin:</b> #{s.coin.replace('/USDT', '')}\n"
                    msg += f"📈 <b>Direction:</b> {'LONG 🟢' if s.dir == 'BUY' else 'SHORT 🔴'}\n"
                    msg += f"⏱ <b>Timeframe:</b> {tf_disp}\n\n"
                    msg += f"📍 <b>Entry:</b> {s.entry}\n"
                    msg += f"🛑 <b>SL (ATR):</b> {s.sl}\n"
                    msg += f"✅ <b>TP (2.5x):</b> {s.tp}\n\n"
                    msg += f"🧠 <b>Confluence:</b> {s.d_stat}\n"
                    msg += f"📊 <i>Sweep ≥ 0.15% | Vol > 1.3x | ADX ≥ 15</i>"
                    
                    send_telegram(msg)
                    logger.info(f"Signal sent: {s.coin} {s.dir} {s.tf}")
                    
                    with STATE_LOCK:
                        COOLDOWNS[c_k] = now
                        SEEN_SIGS.add(k)
                        
    except Exception as e:
        logger.error(f"Job Error: {e}")
    finally:
        gc.collect()

# Explicitly prevent double initialization across reruns
@st.cache_resource
def start_scheduler():
    global _SCHEDULER_RUNNING
    if not _SCHEDULER_RUNNING:
        scheduler = BackgroundScheduler()
        scheduler.add_job(scan_market_job, 'interval', seconds=60, id='balanced_scanner', replace_existing=True)
        scheduler.start()
        _SCHEDULER_RUNNING = True
        logger.info("APScheduler worker successfully started (Singleton Lock).")
        return scheduler
    return None

start_scheduler()

# ==========================================
# UI LAYOUT (Static Dashboard)
# ==========================================
st.title("🎯 Balanced Pro Scalper v3 (Background Engine)")

st.markdown("""
<style>
    .status-box { background-color: #0b2e13; border-left: 5px solid #28a745; padding: 20px; border-radius: 5px; margin-top: 20px;}
    .status-text { color: #28a745; font-size: 18px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='status-box'>
    <div class='status-text'>✅ Server is Online & Scanning 24/7</div>
    <p style='color:#ccc; margin-top:10px; font-size:14px;'>
        The background worker is executing seamlessly via APScheduler every 60 seconds.<br>
        Thread pool limited to 3 workers with thread-local isolated CCXT instances.<br>
        You can safely close this browser tab. Ensure UptimeRobot is pinging the URL.
    </p>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("⚙️ Engine Specs")
st.sidebar.info(
    "**Core Metrics:**\n\n"
    "• ThreadPool: 3 Workers\n"
    "• CCXT: Thread-Isolated\n"
    "• Interval: 60 Seconds\n"
    "• Cache: Thread-Safe 1D\n"
    "• Memory: Locked & GC Managed"
)
