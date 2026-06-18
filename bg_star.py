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

# ================= 🔑 AI API SETTINGS =================
HF_API_KEY = "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"  

# 👑 Premium Layout Config
st.set_page_config(page_title="BG STAR SENTINEL", layout="wide", initial_sidebar_state="collapsed")

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 
FEE_RATE = 0.002 
VIRTUAL_LEVERAGE = 10 
SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "AVAX/USDT", "LINK/USDT", "DOGE/USDT"]
DATA_FILE = "bgstar_trading_data.json" 

# ================= 💾 SMART MEMORY SAVER =================
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

# ================= 🧠 Bot Memory Setup =================
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

# ================= 🤖 100% REAL AI SENTIMENT ENGINE =================
@st.cache_data(ttl=300) 
def get_real_ai_sentiment(coin_symbol):
    if HF_API_KEY == "":
        return {"label": "neutral", "news": "⚠️ API KEY MISSING!"}
    try:
        resp = requests.get('https://cointelegraph.com/rss', timeout=5)
        root = ET.fromstring(resp.content)
        latest_news = ""
        for item in root.findall('./channel/item/title'):
            if coin_symbol.lower() in item.text.lower() or 'crypto' in item.text.lower():
                latest_news = item.text
                break
        if not latest_news: return {"label": "neutral", "news": f"No immediate news for {coin_symbol}."}

        API_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        response = requests.post(API_URL, headers=headers, json={"inputs": latest_news}, timeout=10)
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            return {"label": result[0][0]['label'], "news": latest_news}
        return {"label": "neutral", "news": "Market stable."}
    except:
        return {"label": "neutral", "news": "AI Server Offline."}

active_sym = st.session_state.active_coin.split("/")[0]
ai_data = get_real_ai_sentiment(active_sym)
is_critical_danger = ai_data['label'] == "negative"

# ================= 🌟 DYNAMIC CSS =================
if is_critical_danger:
    st.markdown("""
        <style>
        .block-container { border: 2px solid #FF1744 !important; box-shadow: inset 0 0 50px rgba(255, 23, 68, 0.2); }
        .alert-box { background-color: #FF1744; color: white; padding: 10px; text-align: center; font-weight: 900; font-size: 16px; border-radius: 8px; margin-bottom: 15px; animation: blinker 1.5s linear infinite; }
        @keyframes blinker { 50% { opacity: 0.5; } }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("<style>.alert-box { display: none; }</style>", unsafe_allow_html=True)

st.markdown("""
    <style>
    [data-testid="stHeader"], header, #MainMenu, footer { display: none !important; visibility: hidden !important; }
    html, body, [data-testid="stAppViewContainer"], .main, .block-container { 
        background-color: #0B0E11 !important; color: #EAECEF !important; 
    }
    .block-container { padding-top: 15px !important; padding-right: 15px !important; padding-left: 10px !important; }
    .pos-card { background-color: #181A20; border-left: 4px solid #FCD535; border-radius: 8px; padding: 15px; margin-bottom: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .pos-long { border-left-color: #00FF00; }
    .pos-short { border-left-color: #FF0000; }
    .hist-row { display: flex; justify-content: space-between; border-bottom: 1px solid #1E2329; padding: 5px 0; font-size: 12px;}
    div.stButton > button { border-radius: 8px !important; font-weight: bold !important; width: 100% !important; background-color: #181A20 !important; color: #EAECEF !important; border: 1px solid #2B3139 !important;}
    div.stButton > button:hover { border-color: #FCD535 !important; }
    </style>
""", unsafe_allow_html=True)

if is_critical_danger:
    st.markdown(f'<div class="alert-box">🚨 AI WARNING: MARKET DANGER ON {active_sym}! 🚨<br><span style="font-size:11px;">News: {ai_data["news"]}</span></div>', unsafe_allow_html=True)

# 🎛️ CONTROL PANEL ROW
st.session_state.active_coin = st.selectbox("📊 Select Coin Chart", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))

switch_col1, switch_col2 = st.columns(2)
with switch_col1:
    bot_switch = st.toggle("🤖 AUTO-TRADING ENGINE", value=st.session_state.auto_trade_active)
    if bot_switch != st.session_state.auto_trade_active:
        st.session_state.auto_trade_active = bot_switch
        save_trading_data()
        st.rerun()
with switch_col2:
    pause_radar = st.checkbox("⏸️ PAUSE RADAR (Edit Mode)", value=False)

def fetch_coin_radar(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        # FIXED: Timezone setup to IST (+5:30)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        # FIXED: Zero Division Error Guard (Added 1e-10)
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        curr_vol, curr_price = df['volume'].iloc[-1], df['close'].iloc[-1]
        local_support, local_resistance = df['low'].tail(15).min(), df['high'].tail(15).max()
        
        trend_50 = "BULLISH" if curr_price > df['ema_50'].iloc[-1] else "BEARISH"
        ema_bullish = df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]
        macd_bullish = df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]
        
        signal_text, is_signal_active, signal_dir, alloc_pct = "🎯 SCANNING...", False, "NONE", 0.0
        
        if trend_50 == "BULLISH" and ema_bullish and curr_vol > vol_sma and rsi < 65 and macd_bullish:
            if is_critical_danger and coin == st.session_state.active_coin:
                pass # Blocked
            else:
                signal_text, is_signal_active, signal_dir, alloc_pct = "🚀 BUY", True, "LONG", (7.0 if rsi < 45 else 3.0)
        elif trend_50 == "BEARISH" and not ema_bullish and curr_vol > vol_sma and rsi > 35 and not macd_bullish:
            signal_text, is_signal_active, signal_dir, alloc_pct = "🧨 SELL", True, "SHORT", (7.0 if rsi > 55 else 3.0)
                
        return {'price': curr_price, 'signal': signal_text, 'dir': signal_dir, 'df': df, 'sup': local_support, 'res': local_resistance, 'atr': df['atr'].iloc[-1], 'is_signal_active': is_signal_active, 'alloc_pct': alloc_pct}
    except Exception as e: return None

# ================= 🤖 ENGINE LOGIC =================
data_changed = False 
radars = {}

# FIXED: Chart gets data even if Radar is paused
if pause_radar:
    chart_only_data = fetch_coin_radar(st.session_state.active_coin)
    if chart_only_data: radars[st.session_state.active_coin] = chart_only_data
else:
    for c in SCALPING_COINS:
        radars[c] = fetch_coin_radar(c)
        time.sleep(0.3) # FIXED: API Ban Trap Guard
        
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
            
            if (pos['dir'] == "LONG" and current_price >= pos['tp']) or (pos['dir'] == "SHORT" and current_price <= pos['tp']): close_trade, reason = True, "🎯 TP"
            elif (pos['dir'] == "LONG" and current_price <= pos['sl']) or (pos['dir'] == "SHORT" and current_price >= pos['sl']): close_trade, reason = True, "🛑 SL"
            elif is_critical_danger and symbol == st.session_state.active_coin: close_trade, reason = True, "🚨 AI EXIT"
                
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
            if symbol not in st.session_state.bot_positions and data['is_signal_active'] and bot_is_warmed_up and symbol not in st.session_state.cooldowns:
                invest_amount = st.session_state.total_balance_inr * (data['alloc_pct'] / 100.0)
                if st.session_state.available_balance_inr >= invest_amount and invest_amount > 10:
                    st.session_state.available_balance_inr -= invest_amount
                    atr_buffer = data['atr'] * 1.5 
                    sl = data['sup'] - atr_buffer if data['dir'] == "LONG" else data['res'] + atr_buffer
                    tp = data['price'] + ((data['price'] - sl) * 1.5) if data['dir'] == "LONG" else data['price'] - ((sl - data['price']) * 1.5)
                    st.session_state.bot_positions[symbol] = {'dir': data['dir'], 'entry': data['price'], 'invested_inr': invest_amount, 'tp': tp, 'sl': sl, 'live_pnl': 0.0}
                    st.toast(f"⚡ Auto-Trade: {symbol}", icon="🚀")
                    data_changed = True

# Updating Top Stats
active_invested = sum(p['invested_inr'] for p in st.session_state.bot_positions.values())
st.session_state.total_balance_inr = st.session_state.available_balance_inr + active_invested + sum(p['live_pnl'] for p in st.session_state.bot_positions.values())
if data_changed: save_trading_data()

# ================= 💼 TOP: MASTER PAPER TRADING BOX =================
tot_color = "#00FF00" if st.session_state.total_balance_inr >= 10000 else "#FF1744"
pnl_color = "#00FF00" if (st.session_state.total_balance_inr - 10000) >= 0 else "#FF1744"

st.markdown(f"""
    <div style="background: linear-gradient(135deg, #14181C 0%, #0B0E11 100%); border: 2px solid #2B3139; border-radius: 12px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 10px;">
        <div style="display:flex; justify-content:space-between; text-align:center;">
            <div style="flex: 1;"><div style="font-size:9px; color:#848E9C; font-weight:bold;">PORTFOLIO</div><div style="font-size:13px; font-weight:bold; color:{tot_color};">₹{st.session_state.total_balance_inr:,.1f}</div></div>
            <div style="flex: 1; border-left: 1px solid #2B3139;"><div style="font-size:9px; color:#848E9C; font-weight:bold;">NET PNL</div><div style="font-size:13px; font-weight:bold; color:{pnl_color};">₹{st.session_state.total_balance_inr - 10000:,.1f}</div></div>
            <div style="flex: 1; border-left: 1px solid #2B3139;"><div style="font-size:9px; color:#848E9C; font-weight:bold;">MARGIN</div><div style="font-size:13px; font-weight:bold; color:#FCD535;">₹{active_invested:,.1f}</div></div>
            <div style="flex: 1; border-left: 1px solid #2B3139;"><div style="font-size:9px; color:#848E9C; font-weight:bold;">FEES</div><div style="font-size:13px; font-weight:bold; color:#FF1744;">-₹{st.session_state.total_fees_paid:,.1f}</div></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ================= 📊 LIVE CHART MODULE =================
if radars and st.session_state.active_coin in radars and radars[st.session_state.active_coin] is not None:
    df = radars[st.session_state.active_coin]['df']
    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00FF00', decreasing_line_color='#FF1744')])
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_9'], mode='lines', line=dict(color='#FCD535', width=1), name='EMA 9'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_20'], mode='lines', line=dict(color='#00FF88', width=1), name='EMA 20'))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, rangeslider=dict(visible=False)), yaxis=dict(showgrid=True, gridcolor='#2B3139', side='right'), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ================= 🟢 LIVE POSITIONS & MANUAL CONTROLS =================
if st.session_state.bot_positions:
    for c in list(st.session_state.bot_positions.keys()):
        p = st.session_state.bot_positions[c]
        st.markdown(f"""
            <div class="pos-card {'pos-long' if p['dir'] == 'LONG' else 'pos-short'}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div><div><span style="font-size:18px; font-weight:bold;">{c}</span> <span style="background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; font-size:11px; color:{'#00FF00' if p['dir']=='LONG' else '#FF0000'};">{p['dir']} (10x)</span></div>
                    <div style="font-size:11px; color:#848E9C;">Margin: ₹{p['invested_inr']:,.2f}</div></div>
                    <div style="text-align:right;"><div style="font-size:18px; font-weight:bold; color:{'#00FF00' if p['live_pnl'] >= 0 else '#FF0000'};">₹{p['live_pnl']:,.2f}</div></div>
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

# ================= 👻 FIXED: HISTORY LOG UI =================
if st.session_state.trade_history:
    st.markdown("<hr><div style='color:#848E9C; font-size:11px; font-weight:bold; margin-bottom:5px;'>📜 RECENT TRADE HISTORY</div>", unsafe_allow_html=True)
    for hist in st.session_state.trade_history[:8]: # Showing last 8 trades
        h_color = "#00FF00" if hist['pnl'] > 0 else "#FF1744"
        st.markdown(f"""
            <div class="hist-row">
                <span style="color:#848E9C;">{hist['time']} | {hist['coin']}</span>
                <span style="color:#EAECEF; font-weight:bold;">{hist['reason']}</span>
                <span style="color:{h_color}; font-weight:bold;">₹{hist['pnl']:.2f}</span>
            </div>
        """, unsafe_allow_html=True)

# ================= 🔄 AUTO REFRESH LOOP =================
if not pause_radar:
    time.sleep(7)
    st.rerun()
