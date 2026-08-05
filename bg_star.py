import streamlit as st
import streamlit.components.v1 as components
import os
import logging
import requests
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from dataclasses import dataclass
from streamlit_autorefresh import st_autorefresh

logger = logging.getLogger("balanced_scalper_v3")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(ch)

st.set_page_config(page_title="Balanced Pro Scalper v3", layout="wide")
st_autorefresh(interval=5000, key="bot_refresh")

# --- মূল পরিবর্তনটি এখানে করা হয়েছে ---
# st.secrets এর বদলে os.getenv ব্যবহার করা হয়েছে যাতে রেন্ডারের Environment Variables সরাসরি কাজ করে
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_NEW_SECURE_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8614370967")

def send_telegram(msg):
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "YOUR_REAL_CHAT_ID": return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
    except Exception as e: logger.error(f"TG fail: {e}")

if 't_hist' not in st.session_state: st.session_state.t_hist = deque(maxlen=300)
if 't_set' not in st.session_state: st.session_state.t_set = set()
if 's_cool' not in st.session_state: st.session_state.s_cool = {}
now = datetime.now()
st.session_state.s_cool = {k: v for k, v in st.session_state.s_cool.items() if now - v <= timedelta(minutes=30)}

WEB_AUDIO = "app/static/alert.mp3" if os.path.exists("/mount/src/app/static/alert.mp3") else "static/alert.mp3"
def trigger_pro_alerts(coin, tf, dir, entry, delay=0):
    fc = "rgba(0,255,170,0.3)" if dir == "BUY" else "rgba(255,68,68,0.3)"
    sc = coin.replace("/", "")
    js = f"""<audio id="a_{sc}_{dir}" src="{WEB_AUDIO}" preload="auto"></audio><script>
    setTimeout(()=>{{try{{const d=document,w=window;if(!w.localStorage.getItem("nA")){{if("Notification" in w)Notification.requestPermission();w.localStorage.setItem("nA","1");}}
    const sk="{coin}_{tf}_{dir}_{entry}", lk="ls_{sc}_{tf}_{dir}"; let ok=true;
    try{{if(w.localStorage.getItem(lk)===sk)ok=false; else w.localStorage.setItem(lk,sk);}}catch(e){{ok=true;}}
    if(ok){{try{{if(w.fT)clearTimeout(w.fT);if(!w.oB)w.oB=w.getComputedStyle(d.body).backgroundColor;d.body.style.transition="background-color 0.3s";d.body.style.backgroundColor="{fc}";
    w.fT=setTimeout(()=>{{d.body.style.backgroundColor=w.oB;w.oB=null;}},2000);let a=d.getElementById("a_{sc}_{dir}");if(a){{a.pause();a.currentTime=0;a.play().catch(e=>{{}});}}
    if('speechSynthesis' in w)w.speechSynthesis.speak(new SpeechSynthesisUtterance("Balanced Scalper v3 {dir} on {sc}"));
    if("Notification" in w && Notification.permission==="granted")new Notification("🎯 {coin} {tf} {dir}",{{body:"Live Entry: {entry}"}});
    }}catch(e){{}}}}}}catch(e){{}}}},{delay*2000});</script>"""
    components.html(js, height=0, width=0)

@st.cache_resource
def get_exchange(ex_id): return getattr(ccxt, ex_id)({'enableRateLimit': True, 'timeout': 5000})

def fetch_core(ex_id, sym, tf, lim):
    try:
        df = pd.DataFrame(get_exchange(ex_id).fetch_ohlcv(sym, tf, limit=lim), columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df.set_index('timestamp')
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_1d(ex, sym, lim): return fetch_core(ex, sym, '1d', lim)
@st.cache_data(ttl=15, show_spinner=False)
def fetch_1m(ex, sym, lim): return fetch_core(ex, sym, '1m', lim)
@st.cache_data(ttl=30, show_spinner=False)
def fetch_5m(ex, sym, lim): return fetch_core(ex, sym, '5m', lim)
@st.cache_data(ttl=60, show_spinner=False)
def fetch_15m(ex, sym, lim): return fetch_core(ex, sym, '15m', lim)

@dataclass
class Setup:
    coin: str; tf: str; dir: str; entry: float; sl: float; tp: float; type: str; d_stat: str; brk_time: pd.Timestamp

class Engine:
    def __init__(self): self.ex, self.wm = 'kucoin', 1.3  
    
    def cal_indicators(self, df, p=14):
        df['TR'] = df[['high','low','close']].assign(hc=lambda x: (x.high-x.close.shift()).abs(), lc=lambda x: (x.low-x.close.shift()).abs(), hl=lambda x: x.high-x.low)[['hl','hc','lc']].max(axis=1)
        df['ATR'] = df['TR'].ewm(alpha=1/p, adjust=False).mean()
        
        um, dm = df['high'].diff(), -df['low'].diff()
        df['+DM'] = np.where((um>dm)&(um>0), um, 0)
        df['-DM'] = np.where((dm>um)&(dm>0), dm, 0)
        df['TR_s'], df['+DM_s'], df['-DM_s'] = df['TR'].ewm(alpha=1/p, adjust=False).mean(), df['+DM'].ewm(alpha=1/p, adjust=False).mean(), df['-DM'].ewm(alpha=1/p, adjust=False).mean()
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
            
            # --- BUY LOGIC ---
            if c < pdl and (pdl - c) / pdl >= 0.0015:  
                for j in range(i+1, min(i+5, l_idx)):
                    is_green = df['close'].iloc[j] > df['open'].iloc[j]
                    if is_green:
                        conf_high = df['high'].iloc[j]
                        k = j + 1
                        
                        if k + 1 < len(df) and df['close'].iloc[k] > conf_high and df['volume'].iloc[k] > df['v_avg'].iloc[k] * self.wm:
                            
                            atr = df['ATR'].iloc[k]
                            if pd.isna(atr) or atr == 0: continue 
                            
                            entry_price = df['open'].iloc[k+1]
                            sl_price = df['low'].iloc[j] - (atr * 1.2)  
                            
                            d_val = (df['volume'].iloc[i:k+1]*((df['close'].iloc[i:k+1]-df['low'].iloc[i:k+1])-(df['high'].iloc[i:k+1]-df['close'].iloc[i:k+1]))/(df['high'].iloc[i:k+1]-df['low'].iloc[i:k+1]+1e-9)).sum()
                            trend_ok = df['close'].iloc[k] > df['ema20'].iloc[k]
                            
                            if d_val > 0 and trend_ok and df['ADX'].iloc[k] >= 15 and df['rsi'].iloc[k] < 75:
                                tp_price = entry_price + (atr * 2.5) 
                                res.append(Setup(sym, tf, "BUY", round(entry_price, 4), round(sl_price, 4), round(tp_price, 4), "Balanced Scalper v3", "🟢 EMA20 UPTREND", df.index[k]))
                                break

            # --- SELL LOGIC ---
            if c > pdh and (c - pdh) / pdh >= 0.0015:  
                for j in range(i+1, min(i+5, l_idx)):
                    is_red = df['close'].iloc[j] < df['open'].iloc[j]
                    if is_red:
                        conf_low = df['low'].iloc[j]
                        k = j + 1
                        
                        if k + 1 < len(df) and df['close'].iloc[k] < conf_low and df['volume'].iloc[k] > df['v_avg'].iloc[k] * self.wm:
                            
                            atr = df['ATR'].iloc[k]
                            if pd.isna(atr) or atr == 0: continue 
                            
                            entry_price = df['open'].iloc[k+1]
                            sl_price = df['high'].iloc[j] + (atr * 1.2)  
                            
                            d_val = (df['volume'].iloc[i:k+1]*((df['close'].iloc[i:k+1]-df['low'].iloc[i:k+1])-(df['high'].iloc[i:k+1]-df['close'].iloc[i:k+1]))/(df['high'].iloc[i:k+1]-df['low'].iloc[i:k+1]+1e-9)).sum()
                            trend_ok = df['close'].iloc[k] < df['ema20'].iloc[k]
                            
                            if d_val < 0 and trend_ok and df['ADX'].iloc[k] >= 15 and df['rsi'].iloc[k] > 25:
                                tp_price = entry_price - (atr * 2.5) 
                                res.append(Setup(sym, tf, "SELL", round(entry_price, 4), round(sl_price, 4), round(tp_price, 4), "Balanced Scalper v3", "🔴 EMA20 DOWNTREND", df.index[k]))
                                break
        return res

    def run(self, sym):
        d1 = fetch_1d(self.ex, sym, 5)
        if d1 is None or len(d1) < 2: return []
        pdh, pdl, all_s = d1['high'].iloc[-2], d1['low'].iloc[-2], []
        for tp, tn, fn in [("1m","1M",fetch_1m), ("5m","5M",fetch_5m), ("15m","15M",fetch_15m)]:
            df = fn(self.ex, sym, 200)
            if df is not None and len(df) >= 200: all_s.extend(self._scan(sym, df, pdh, pdl, tn))
        return all_s

eng = Engine()
st.title("🎯 Balanced Pro Scalper v3 (Optimized Sweep 0.15% + High Frequency)")
COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
def scan(c):
    try: return eng.run(c)
    except: return []

sigs = []
with ThreadPoolExecutor(min(5, len(COINS))) as ex:
    for f in as_completed({ex.submit(scan, c): c for c in COINS}): sigs.extend(f.result() or [])

mtf_c = {}
for s in sigs: mtf_c.setdefault((s.coin, s.dir), set()).add(s.tf)

if sigs:
    for i, s in enumerate(sigs):
        k, c_k = f"{s.coin}_{s.tf}_{s.dir}_{s.brk_time}", f"{s.coin}_{s.tf}_{s.dir}"
        if c_k not in st.session_state.s_cool or now >= st.session_state.s_cool[c_k] + timedelta(minutes=5):
            if k not in st.session_state.t_set:
                hc = len(mtf_c[(s.coin, s.dir)]) == 3
                tf_disp = "🔥 HIGH CONFIDENCE (1M+5M+15M)" if hc else s.tf
                
                st.success(f"{'🟩' if s.dir=='BUY' else '🟥'} **{s.coin} | {tf_disp}** | Dir: **{s.dir}**")
                st.warning(f"📊 Sweep ≥ 0.15% | Vol > 1.3x | ADX ≥ 15 | EMA20 | ATR SL & 2.5x TP | Entry: `{s.entry}` | SL: `{s.sl}` | TP: `{s.tp}`")
                send_telegram(f"🎯 {s.coin}\nTF: {tf_disp}\nDir: {s.dir}\nLive En: {s.entry}\nATR SL: {s.sl}\nDyn TP: {s.tp}\n{s.d_stat}")
                trigger_pro_alerts(s.coin, "High-Conf" if hc else s.tf, s.dir, s.entry, i)
                
                st.session_state.t_hist.append(k); st.session_state.t_set.add(k); st.session_state.s_cool[c_k] = now
else: st.info("🎯 Monitoring Balanced Scalper v3 (Sweep 0.15% + Volume 1.3x + Breakout Window 4 Candles + 2.5x ATR TP)...")
