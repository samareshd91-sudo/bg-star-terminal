import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import concurrent.futures

# ================= 🔑 AI API SETTINGS =================
HF_API_KEY = "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"  

# 👑 Config
st.set_page_config(page_title="BG STAR PRO", layout="wide")

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 
FEE_RATE = 0.002 
VIRTUAL_LEVERAGE = 10 
SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "AVAX/USDT", "LINK/USDT", "DOGE/USDT"]
DATA_FILE = "bgstar_trading_data.json" 

# ================= 🌟 DYNAMIC CSS =================
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #0B0E11 !important; color: #EAECEF !important; overflow-y: scroll !important; }
    ::-webkit-scrollbar { width: 14px !important; }
    ::-webkit-scrollbar-track { background: #161A1E !important; }
    ::-webkit-scrollbar-thumb { background: #FCD535 !important; border-radius: 10px; border: 3px solid #161A1E; }
    [data-testid="stHeader"] { display: none !important; }
    .pos-card { background-color: #181A20; border-left: 4px solid #FCD535; border-radius: 8px; padding: 15px; margin-bottom: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .signal-log { background: #1E2329; border: 1px solid #363C4E; border-radius: 5px; padding: 8px; font-size: 11px; color: #848E9C; margin-bottom: 5px; }
    .hist-row { display: flex; justify-content: space-between; border-bottom: 1px solid #1E2329; padding: 5px 0; font-size: 12px;}
    </style>
""", unsafe_allow_html=True)

# ================= 💾 MEMORY FUNCTIONS =================
def load_saved_data():
    if os.path.exists(DATA_FILE):
        try: 
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return None
    return None

def save_trading_data():
    data = {
        'total_balance_inr': st.session_state.total_balance_inr,
        'available_balance_inr': st.session_state.available_balance_inr,
        'total_fees_paid': st.session_state.total_fees_paid,
        'bot_positions': st.session_state.bot_positions,
        'trade_history': st.session_state.trade_history,
        'cooldowns': st.session_state.cooldowns,
        'auto_trade_active': st.session_state.auto_trade_active,
        'active_coin': st.session_state.active_coin
    }
    with open(DATA_FILE, "w") as f: json.dump(data, f)

if 'app_start_time' not in st.session_state: 
    st.session_state.app_start_time = time.time()
    saved_data = load_saved_data()
    if saved_data:
        st.session_state.total_balance_inr = saved_data.get('total_balance_inr', 10000.0)
        st.session_state.available_balance_inr = saved_data.get('available_balance_inr', 10000.0)
        st.session_state.total_fees_paid = saved_data.get('total_fees_paid', 0.0)
        st.session_state.bot_positions = saved_data.get('bot_positions', {})
        st.session_state.trade_history = saved_data.get('trade_history', [])
        st.session_state.cooldowns = saved_data.get('cooldowns', {})
        st.session_state.auto_trade_active = saved_data.get('auto_trade_active', True)
        st.session_state.active_coin = saved_data.get('active_coin', "BTC/USDT")
    else:
        st.session_state.total_balance_inr = 10000.0
        st.session_state.available_balance_inr = 10000.0
        st.session_state.total_fees_paid = 0.0
        st.session_state.bot_positions = {}
        st.session_state.trade_history = []
        st.session_state.cooldowns = {}
        st.session_state.auto_trade_active = True
        st.session_state.active_coin = "BTC/USDT"
        save_trading_data()

# ================= 🧠 AI SENTIMENT =================
@st.cache_data(ttl=300) 
def get_real_ai_sentiment(coin_symbol):
    try:
        resp = requests.get('https://cointelegraph.com/rss', timeout=5)
        root = ET.fromstring(resp.content)
        latest_news = ""
        for item in root.findall('./channel/item/title'):
            if coin_symbol.lower() in item.text.lower() or 'crypto' in item.text.lower():
                latest_news = item.text
                break
        API_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        response = requests.post(API_URL, headers=headers, json={"inputs": latest_news}, timeout=5)
        result = response.json()
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            return {"label": result[0][0]['label'], "news": latest_news}
        return {"label": "neutral", "news": "Market stable."}
    except: return {"label": "neutral", "news": "AI Offline."}

active_sym = st.session_state.active_coin.split("/")[0]
ai_data = get_real_ai_sentiment(active_sym)
is_critical_danger = ai_data['label'] == "negative"

# Control UI
st.session_state.active_coin = st.selectbox("📊 Select Coin Chart", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))
bot_switch = st.toggle("🤖 AUTO-TRADING ENGINE", value=st.session_state.auto_trade_active)
if bot_switch != st.session_state.auto_trade_active:
    st.session_state.auto_trade_active = bot_switch
    save_trading_data()
    st.rerun()

# ================= ⚡ ASYNC SCANNER =================
def fetch_coin_radar(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        
        curr_price, curr_vol, vol_sma = df['close'].iloc[-1], df['volume'].iloc[-1], df['volume'].rolling(20).mean().iloc[-1]
        
        # Local Support/Resistance for TP/SL
        local_support, local_resistance = df['low'].tail(15).min(), df['high'].tail(15).max()
        df['tr'] = df[['high', 'low', 'close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['close']), abs(x['low'] - x['close'])), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]

        reasons = []
        is_signal, signal_dir, alloc = False, "NONE", 0.0
        
        # Trend Logic
        if curr_price > df['ema_50'].iloc[-1]: reasons.append("✅ Above EMA 50")
        else: reasons.append("❌ Below EMA 50")
        if df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]: reasons.append("✅ EMA 9 > 20")
        if curr_vol > vol_sma: reasons.append("✅ High Volume")
        
        if len(reasons) >= 3 and rsi < 65:
            is_signal, signal_dir, alloc = True, "LONG", 5.0
        elif curr_price < df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] < df['ema_20'].iloc[-1] and curr_vol > vol_sma:
            is_signal, signal_dir, alloc = True, "SHORT", 5.0
            reasons = ["✅ Down Trend Confirmed", "✅ High Volume"]
        
        return {'price': curr_price, 'signal': signal_dir, 'df': df, 'reasons': reasons, 'is_signal': is_signal, 'alloc': alloc, 'sup': local_support, 'res': local_resistance, 'atr': atr}
    except: return None

# 🚀 Parallel Execution (১ সেকেন্ডে ৮টা কয়েন স্ক্যান)
radars = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    future_to_coin = {executor.submit(fetch_coin_radar, c): c for c in SCALPING_COINS}
    for future in concurrent.futures.as_completed(future_to_coin):
        c = future_to_coin[future]
        radars[c] = future.result()

# ================= 💼 POSITION MANAGER =================
data_changed = False
time_since_app_opened = time.time() - st.session_state.app_start_time
bot_is_warmed_up = time_since_app_opened > 15 

current_time = time.time()
keys_to_del = [k for k, v in st.session_state.cooldowns.items() if current_time > v]
for k in keys_to_del: del st.session_state.cooldowns[k]

positions_to_close = []
for symbol, pos in st.session_state.bot_positions.items():
    if symbol in radars and radars[symbol]:
        current_price = radars[symbol]['price']
        close_trade, reason = False, ""
        
        pnl_pct = ((current_price - pos['entry']) / pos['entry'] if pos['dir'] == "LONG" else (pos['entry'] - current_price) / pos['entry']) * VIRTUAL_LEVERAGE
        pos['live_pnl'] = pos['invested_inr'] * pnl_pct
        
        if (pos['dir'] == "LONG" and current_price >= pos['tp']) or (pos['dir'] == "SHORT" and current_price <= pos['tp']): close_trade, reason = True, "🎯 Auto TP"
        elif (pos['dir'] == "LONG" and current_price <= pos['sl']) or (pos['dir'] == "SHORT" and current_price >= pos['sl']): close_trade, reason = True, "🛑 Auto SL"
        elif is_critical_danger and symbol.split("/")[0] == active_sym: close_trade, reason = True, "🚨 AI EXIT"
            
        if close_trade: positions_to_close.append((symbol, reason))

for symbol, reason in positions_to_close:
    pos = st.session_state.bot_positions[symbol]
    fee_inr = (pos['invested_inr'] * VIRTUAL_LEVERAGE) * FEE_RATE * 2 
    net_pnl_inr = pos['live_pnl'] - fee_inr
    st.session_state.total_fees_paid += fee_inr
    st.session_state.available_balance_inr += pos['invested_inr'] + net_pnl_inr
    st.session_state.trade_history.insert(0, {'time': datetime.now().strftime("%H:%M"), 'coin': symbol, 'dir': pos['dir'], 'pnl': net_pnl_inr, 'reason': reason})
    st.session_state.cooldowns[symbol] = time.time() + 300
    del st.session_state.bot_positions[symbol]
    data_changed = True

if st.session_state.auto_trade_active:
    for symbol, data in radars.items():
        if not data: continue
        if symbol not in st.session_state.bot_positions and data['is_signal'] and bot_is_warmed_up and symbol not in st.session_state.cooldowns:
            invest_amount = st.session_state.total_balance_inr * (data['alloc'] / 100.0)
            if st.session_state.available_balance_inr >= invest_amount and invest_amount > 10:
                st.session_state.available_balance_inr -= invest_amount
                atr_buffer = data['atr'] * 1.5 
                sl = data['sup'] - atr_buffer if data['signal'] == "LONG" else data['res'] + atr_buffer
                tp = data['price'] + ((data['price'] - sl) * 1.5) if data['signal'] == "LONG" else data['price'] - ((sl - data['price']) * 1.5)
                st.session_state.bot_positions[symbol] = {'dir': data['signal'], 'entry': data['price'], 'invested_inr': invest_amount, 'tp': tp, 'sl': sl, 'live_pnl': 0.0}
                st.toast(f"⚡ Sniper Auto-Trade: {symbol}", icon="🚀")
                data_changed = True

active_invested = sum(p['invested_inr'] for p in st.session_state.bot_positions.values())
st.session_state.total_balance_inr = st.session_state.available_balance_inr + active_invested + sum(p['live_pnl'] for p in st.session_state.bot_positions.values())
if data_changed: save_trading_data()

# ================= 📊 DASHBOARD UI =================
tot_color = "#00FF00" if st.session_state.total_balance_inr >= 10000 else "#FF1744"
pnl_color = "#00FF00" if (st.session_state.total_balance_inr - 10000) >= 0 else "#FF1744"

st.markdown(f"""
    <div style="background: linear-gradient(135deg, #14181C 0%, #0B0E11 100%); border: 2px solid #2B3139; border-radius: 12px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 10px;">
        <div style="display:flex; justify-content:space-between; text-align:center;">
            <div style="flex: 1;"><div style="font-size:9px; color:#848E9C; font-weight:bold;">PORTFOLIO</div><div style="font-size:13px; font-weight:bold; color:{tot_color};">₹{st.session_state.total_balance_inr:,.1f}</div></div>
            <div style="flex: 1; border-left: 1px solid #2B3139;"><div style="font-size:9px; color:#848E9C; font-weight:bold;">NET PNL</div><div style="font-size:13px; font-weight:bold; color:{pnl_color};">₹{st.session_state.total_balance_inr - 10000:,.1f}</div></div>
            <div style="flex: 1; border-left: 1px solid #2B3139;"><div style="font-size:9px; color:#848E9C; font-weight:bold;">MARGIN</div><div style="font-size:13px; font-weight:bold; color:#FCD535;">₹{active_invested:,.1f}</div></div>
        </div>
    </div>
""", unsafe_allow_html=True)

if st.session_state.active_coin in radars and radars[st.session_state.active_coin]:
    data = radars[st.session_state.active_coin]
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write(f"**🔍 Analysis:**")
        for r in data['reasons']: st.markdown(f"<div class='signal-log'>{r}</div>", unsafe_allow_html=True)
    with col2:
        df = data['df']
        fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark", xaxis=dict(rangeslider=dict(visible=False)))
        st.plotly_chart(fig, use_container_width=True)

if st.session_state.bot_positions:
    st.write("**💼 Live Positions:**")
    for c, p in list(st.session_state.bot_positions.items()):
        st.markdown(f"""
            <div class="pos-card">
                <div style="display:flex; justify-content:space-between;">
                    <div><span style="font-weight:bold;">{c}</span> <span style="font-size:11px; color:#00FF00;">{p['dir']} (10x)</span><br><span style="font-size:11px; color:#848E9C;">Margin: ₹{p['invested_inr']:.2f}</span></div>
                    <div style="text-align:right;"><span style="font-weight:bold; color:{'#00FF00' if p['live_pnl'] >= 0 else '#FF0000'};">₹{p['live_pnl']:.2f}</span></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button(f"💰 Close {c}", key=f"close_{c}"):
            fee_inr = (p['invested_inr'] * VIRTUAL_LEVERAGE) * FEE_RATE * 2
            net_pnl = p['live_pnl'] - fee_inr
            st.session_state.total_fees_paid += fee_inr
            st.session_state.available_balance_inr += p['invested_inr'] + net_pnl
            st.session_state.trade_history.insert(0, {'time': datetime.now().strftime("%H:%M"), 'coin': c, 'dir': p['dir'], 'pnl': net_pnl, 'reason': '👤 Manual Close'})
            st.session_state.cooldowns[c] = time.time() + 300
            del st.session_state.bot_positions[c]
            save_trading_data() 
            st.rerun()

if st.session_state.trade_history:
    st.write("**📜 Trade Logs:**")
    for h in st.session_state.trade_history[:5]:
        st.markdown(f"<div class='hist-row'><span>{h['time']} | {h['coin']} | {h['reason']}</span><span style='color:{'#00FF00' if h['pnl']>0 else '#FF1744'}'>₹{h['pnl']:.2f}</span></div>", unsafe_allow_html=True)

time.sleep(5)
st.rerun()
