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

# 👑 Premium Layout Config
st.set_page_config(page_title="BG STAR ANALYZER & BOT", layout="wide", initial_sidebar_state="collapsed")

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 
FEE_RATE = 0.002 
VIRTUAL_LEVERAGE = 10 
SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "AVAX/USDT", "LINK/USDT", "DOGE/USDT"]
DATA_FILE = "bgstar_trading_data.json" 

# ================= 🌟 DYNAMIC CSS (FIXED UI JUMP) =================
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #0B0E11 !important; color: #EAECEF !important; overflow-y: auto !important; }
    ::-webkit-scrollbar { width: 14px !important; }
    ::-webkit-scrollbar-track { background: #161A1E !important; }
    ::-webkit-scrollbar-thumb { background: #FCD535 !important; border-radius: 10px; border: 3px solid #161A1E; }
    [data-testid="stHeader"], header { display: none !important; }
    .block-container { padding-top: 15px !important; padding-right: 15px !important; padding-left: 10px !important; }
    
    /* Fixed Heights to prevent screen jumping */
    .analyzer-card { background-color: #181A20; border: 1px solid #2B3139; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 10px; height: 85px;}
    .analyzer-title { color: #848E9C; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .analyzer-val { font-size: 16px; font-weight: bold; }
    
    .sniper-btn { background: linear-gradient(90deg, #181A20 0%, #1E2329 100%); border: 1px solid #FCD535; border-radius: 8px; padding: 10px; text-align: center; font-weight: bold; color: #FCD535; margin: 15px 0; letter-spacing: 1px; min-height: 45px;}
    .stats-row { display: flex; justify-content: space-between; border-bottom: 1px solid #1E2329; padding: 8px 0; font-size: 13px; }
    
    .pos-card { background-color: #181A20; border-left: 4px solid #FCD535; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
    div.stButton > button { border-radius: 8px !important; font-weight: bold !important; width: 100% !important; background-color: #181A20 !important; color: #EAECEF !important; border: 1px solid #2B3139 !important;}
    div.stButton > button:hover { border-color: #FCD535 !important; }
    </style>
""", unsafe_allow_html=True)

# ================= 💾 SMART MEMORY =================
def load_saved_data():
    if os.path.exists(DATA_FILE):
        try: 
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return None
    return None

def save_trading_data():
    data = {
        'total_balance_inr': st.session_state.total_balance_inr, 'available_balance_inr': st.session_state.available_balance_inr,
        'total_fees_paid': st.session_state.total_fees_paid, 'bot_positions': st.session_state.bot_positions,
        'trade_history': st.session_state.trade_history, 'cooldowns': st.session_state.cooldowns,
        'auto_trade_active': st.session_state.auto_trade_active, 'active_coin': st.session_state.active_coin
    }
    with open(DATA_FILE, "w") as f: json.dump(data, f)

if 'app_start_time' not in st.session_state: 
    st.session_state.app_start_time = time.time()
    saved_data = load_saved_data()
    if saved_data:
        st.session_state.update(saved_data)
    else:
        st.session_state.total_balance_inr = 10000.0
        st.session_state.available_balance_inr = 10000.0
        st.session_state.total_fees_paid = 0.0
        st.session_state.bot_positions = {}
        st.session_state.trade_history = []
        st.session_state.cooldowns = {}
        st.session_state.auto_trade_active = True
        st.session_state.active_coin = "BNB/USDT"
        save_trading_data()

# ================= 🎛️ CONTROL PANEL (MOVED UP FOR NO DELAY) =================
# ফিক্সড: ড্রপডাউন ওপরে আনা হয়েছে যাতে এআই সাথে সাথে নতুন কয়েনের নিউজ আনতে পারে
st.session_state.active_coin = st.selectbox("📊 Select Coin Chart", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))
bot_switch = st.toggle("🤖 AUTO-TRADING ENGINE", value=st.session_state.auto_trade_active)
if bot_switch != st.session_state.auto_trade_active:
    st.session_state.auto_trade_active = bot_switch
    save_trading_data()
    st.rerun()

# ================= 🧠 FAST AI SENTIMENT =================
@st.cache_data(ttl=300) 
def get_real_ai_sentiment(coin_symbol):
    try:
        resp = requests.get('https://cointelegraph.com/rss', timeout=5)
        root = ET.fromstring(resp.content)
        latest_news = next((item.text for item in root.findall('./channel/item/title') if coin_symbol.lower() in item.text.lower() or 'crypto' in item.text.lower()), None)
        if not latest_news: return {"label": "neutral", "news": f"No immediate news for {coin_symbol}."}
        response = requests.post("https://api-inference.huggingface.co/models/ProsusAI/finbert", headers={"Authorization": f"Bearer {HF_API_KEY}"}, json={"inputs": latest_news}, timeout=5).json()
        if isinstance(response, list) and len(response) > 0 and isinstance(response[0], list): return {"label": response[0][0]['label'], "news": latest_news}
        return {"label": "neutral", "news": "AI Passive Mode Active."}
    except Exception: return {"label": "neutral", "news": "AI Offline. Relying on Technicals."}

active_sym = st.session_state.active_coin.split("/")[0]
ai_data = get_real_ai_sentiment(active_sym)
is_critical_danger = ai_data['label'] == "negative"

if is_critical_danger:
    st.markdown(f'<div style="background-color: #FF1744; color: white; padding: 10px; text-align: center; font-weight: bold; border-radius: 8px; margin-bottom: 15px;">🚨 AI WARNING: DANGER ON {active_sym}! 🚨<br><span style="font-size:11px; font-weight:normal;">{ai_data["news"]}</span></div>', unsafe_allow_html=True)

# ================= ⚡ ASYNC PARALLEL SCANNER =================
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
        
        trend_status = "📈 UP TREND" if curr_price > df['ema_50'].iloc[-1] else "📉 DOWN TREND"
        trend_color = "#00FF00" if "UP" in trend_status else "#FF1744"
        
        orderflow = "🟢 BUYERS 🔥" if df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1] and rsi > 50 else "🔴 SELLERS 🩸"
        orderflow_color = "#00FF00" if "BUYERS" in orderflow else "#FF1744"
        
        vol_ratio = (curr_vol / vol_sma) * 100
        vol_status = f"🔥 HIGH ({vol_ratio:.0f}%)" if curr_vol > vol_sma else f"❄️ LOW ({vol_ratio:.0f}%)"
        vol_color = "#00FF00" if curr_vol > vol_sma else "#848E9C"
        
        local_support, local_resistance = df['low'].tail(15).min(), df['high'].tail(15).max()
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]

        is_signal, signal_dir, alloc = False, "NONE", 0.0
        signal_text = "⏳ SCANNING MARKET"
        
        if curr_price > df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1] and curr_vol > vol_sma and rsi < 65:
            is_signal, signal_dir, alloc, signal_text = True, "LONG", 5.0, "🚀 SNIPER BUY"
        elif curr_price < df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] < df['ema_20'].iloc[-1] and curr_vol > vol_sma and rsi > 35:
            is_signal, signal_dir, alloc, signal_text = True, "SHORT", 5.0, "🧨 SNIPER SELL"
        
        return {
            'price': curr_price, 'signal': signal_dir, 'df': df, 
            'is_signal': is_signal, 'alloc': alloc, 'signal_text': signal_text,
            'sup': local_support, 'res': local_resistance, 'atr': atr,
            'trend': trend_status, 't_color': trend_color,
            'orderflow': orderflow, 'o_color': orderflow_color,
            'vol': vol_status, 'v_color': vol_color, 'raw_vol': curr_vol
        }
    except Exception as e: return None

radars = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    future_to_coin = {executor.submit(fetch_coin_radar, c): c for c in SCALPING_COINS}
    for future in concurrent.futures.as_completed(future_to_coin): radars[future_to_coin[future]] = future.result()

# ================= 💼 POSITION MANAGER & BACKGROUND ENGINE =================
data_changed = False
bot_is_warmed_up = (time.time() - st.session_state.app_start_time) > 10 

keys_to_del = [k for k, v in st.session_state.cooldowns.items() if time.time() > v]
for k in keys_to_del: del st.session_state.cooldowns[k]

positions_to_close = []
for symbol, pos in st.session_state.bot_positions.items():
    if symbol in radars and radars[symbol]:
        current_price = radars[symbol]['price']
        close_trade, reason = False, ""
        
        pnl_pct = ((current_price - pos['entry']) / pos['entry'] if pos['dir'] == "LONG" else (pos['entry'] - current_price) / pos['entry']) * VIRTUAL_LEVERAGE
        pos['live_pnl'] = pos['invested_inr'] * pnl_pct
        
        if (pos['dir'] == "LONG" and current_price >= pos['tp']) or (pos['dir'] == "SHORT" and current_price <= pos['tp']): close_trade, reason = True, "🎯 Auto TP Hit"
        elif (pos['dir'] == "LONG" and current_price <= pos['sl']) or (pos['dir'] == "SHORT" and current_price >= pos['sl']): close_trade, reason = True, "🛑 Auto SL Hit"
        elif is_critical_danger and symbol.split("/")[0] == active_sym: close_trade, reason = True, "🚨 AI Emergency Exit"
            
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
        if is_critical_danger and symbol.split("/")[0] == active_sym: continue
            
        if symbol not in st.session_state.bot_positions and data['is_signal'] and bot_is_warmed_up and symbol not in st.session_state.cooldowns:
            invest_amount = st.session_state.total_balance_inr * (data['alloc'] / 100.0)
            if st.session_state.available_balance_inr >= invest_amount and invest_amount > 10:
                st.session_state.available_balance_inr -= invest_amount
                atr_buffer = data['atr'] * 1.5 
                sl = data['sup'] - atr_buffer if data['signal'] == "LONG" else data['res'] + atr_buffer 
                tp = data['price'] + ((data['price'] - sl) * 1.5) if data['signal'] == "LONG" else data['price'] - ((sl - data['price']) * 1.5)
                st.session_state.bot_positions[symbol] = {'dir': data['signal'], 'entry': data['price'], 'invested_inr': invest_amount, 'tp': tp, 'sl': sl, 'live_pnl': 0.0}
                st.toast(f"⚡ Auto-Trade Triggered: {symbol}", icon="🚀")
                data_changed = True

active_invested = sum(p['invested_inr'] for p in st.session_state.bot_positions.values())
st.session_state.total_balance_inr = st.session_state.available_balance_inr + active_invested + sum(p['live_pnl'] for p in st.session_state.bot_positions.values())
if data_changed: save_trading_data()

# ================= 📊 VISUAL ANALYZER UI =================
tot_color = "#00FF00" if st.session_state.total_balance_inr >= 10000 else "#FF1744"
st.markdown(f"""
    <div style="display:flex; justify-content:space-between; text-align:center; background: #14181C; border: 1px solid #2B3139; border-radius: 8px; padding: 10px; margin-bottom: 15px;">
        <div style="flex: 1;"><div style="font-size:10px; color:#848E9C;">PORTFOLIO</div><div style="font-size:14px; font-weight:bold; color:{tot_color};">₹{st.session_state.total_balance_inr:,.1f}</div></div>
        <div style="flex: 1; border-left: 1px solid #2B3139;"><div style="font-size:10px; color:#848E9C;">MARGIN</div><div style="font-size:14px; font-weight:bold; color:#FCD535;">₹{active_invested:,.1f}</div></div>
    </div>
""", unsafe_allow_html=True)

if st.session_state.active_coin in radars and radars[st.session_state.active_coin]:
    data = radars[st.session_state.active_coin]
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f"<div class='analyzer-card'><div class='analyzer-title'>🧭 MARKET ({st.session_state.active_coin.split('/')[0]})</div><div class='analyzer-val' style='color:{data['t_color']}'>{data['trend']}</div></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='analyzer-card'><div class='analyzer-title'>⚡ ORDERFLOW</div><div class='analyzer-val' style='color:{data['o_color']}'>{data['orderflow']}</div></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='analyzer-card'><div class='analyzer-title'>📊 VOLUME</div><div class='analyzer-val' style='color:{data['v_color']}'>{data['vol']}</div></div>", unsafe_allow_html=True)
    
    df = data['df']
    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00FF00', decreasing_line_color='#FF1744')])
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_9'], mode='lines', line=dict(color='#00BFFF', width=1.5), name='EMA 9'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_50'], mode='lines', line=dict(color='#FFD700', width=1.5, dash='dot'), name='EMA 50'))
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, rangeslider=dict(visible=False)), yaxis=dict(showgrid=True, gridcolor='#2B3139', side='right'))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"<div style='text-align:center; font-size:22px; font-weight:bold; color:#FCD535; margin-top:10px;'>{st.session_state.active_coin} <br> <span style='color:#EAECEF'>${data['price']:.4f}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sniper-btn'>{data['signal_text']}</div>", unsafe_allow_html=True)

# ================= 💼 LIVE POSITIONS =================
if st.session_state.bot_positions:
    st.write("**💼 Live Positions:**")
    for c, p in list(st.session_state.bot_positions.items()):
        border_color = "#00FF00" if p['dir'] == "LONG" else "#FF1744"
        st.markdown(f"""
            <div class="pos-card" style="border-left-color: {border_color};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div><div><span style="font-weight:bold; font-size:16px;">{c}</span> <span style="font-size:11px; padding:2px 4px; border-radius:4px; background:rgba(255,255,255,0.1); color:{border_color};">{p['dir']} (10x)</span></div>
                    <div style="font-size:11px; color:#848E9C; margin-top:4px;">Entry: {p['entry']} | SL: {p['sl']:.4f}</div></div>
                    <div style="text-align:right;"><div style="font-weight:bold; font-size:18px; color:{'#00FF00' if p['live_pnl'] >= 0 else '#FF1744'};">₹{p['live_pnl']:,.2f}</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button(f"💰 Close {c} Manually", key=f"close_{c}"):
            fee_inr = (p['invested_inr'] * VIRTUAL_LEVERAGE) * FEE_RATE * 2
            net_pnl = p['live_pnl'] - fee_inr
            st.session_state.total_fees_paid += fee_inr
            st.session_state.available_balance_inr += p['invested_inr'] + net_pnl
            st.session_state.trade_history.insert(0, {'time': datetime.now().strftime("%H:%M"), 'coin': c, 'dir': p['dir'], 'pnl': net_pnl, 'reason': '👤 Manual Close'})
            st.session_state.cooldowns[c] = time.time() + 300
            del st.session_state.bot_positions[c]
            save_trading_data() 
            # ফিক্সড: বাটন কাজ করার সাথে সাথে UI আপডেট হবে
            st.rerun()

# ফিক্সড: UI Freeze কমানোর জন্য স্লিপ টাইম ৫ সেকেন্ড করা হলো
time.sleep(5)
st.rerun()
