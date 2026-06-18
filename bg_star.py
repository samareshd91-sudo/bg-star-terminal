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

# ================= 🔑 AI API SETTINGS (REAL AI) =================
# আপনার দেওয়া আসল Hugging Face API Key এখানে বসানো হয়েছে
HF_API_KEY = "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"  

# 👑 Premium Layout Config
st.set_page_config(page_title="BG STAR SENTINEL (AI)", layout="wide", initial_sidebar_state="collapsed")

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
        'auto_trade_active': st.session_state.auto_trade_active
    }
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# ================= 🧠 Bot Memory Setup =================
if 'app_start_time' not in st.session_state: 
    st.session_state.app_start_time = time.time()
    st.session_state.active_coin = "BTC/USDT"
    
    saved_data = load_saved_data()
    if saved_data:
        st.session_state.total_balance_inr = saved_data.get('total_balance_inr', 10000.0)
        st.session_state.available_balance_inr = saved_data.get('available_balance_inr', 10000.0)
        st.session_state.total_fees_paid = saved_data.get('total_fees_paid', 0.0)
        st.session_state.bot_positions = saved_data.get('bot_positions', {})
        st.session_state.trade_history = saved_data.get('trade_history', [])
        st.session_state.cooldowns = saved_data.get('cooldowns', {})
        st.session_state.auto_trade_active = saved_data.get('auto_trade_active', True)
    else:
        st.session_state.total_balance_inr = 10000.0
        st.session_state.available_balance_inr = 10000.0
        st.session_state.total_fees_paid = 0.0
        st.session_state.bot_positions = {}
        st.session_state.trade_history = []
        st.session_state.cooldowns = {}
        st.session_state.auto_trade_active = True
        save_trading_data()

# ================= 🤖 100% REAL AI SENTIMENT ENGINE =================
@st.cache_data(ttl=300) 
def get_real_ai_sentiment(coin_symbol):
    if HF_API_KEY == "":
        return {"label": "neutral", "news": "⚠️ API KEY MISSING! AI IS OFFLINE."}
        
    try:
        # 1. Fetching Real Live Crypto News from RSS
        resp = requests.get('https://cointelegraph.com/rss', timeout=5)
        root = ET.fromstring(resp.content)
        
        latest_news = ""
        for item in root.findall('./channel/item/title'):
            if coin_symbol.lower() in item.text.lower() or 'crypto' in item.text.lower():
                latest_news = item.text
                break
                
        if not latest_news:
            return {"label": "neutral", "news": f"No immediate news impact found for {coin_symbol}."}

        # 2. Analyzing News with Hugging Face FinBERT
        API_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        
        response = requests.post(API_URL, headers=headers, json={"inputs": latest_news}, timeout=10)
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            sentiment = result[0][0]['label'] 
            return {"label": sentiment, "news": latest_news}
        else:
            return {"label": "neutral", "news": f"AI Parsing: Standard Market."}
            
    except Exception as e:
        return {"label": "neutral", "news": "AI Server Connection Timeout."}

# Fetch Real AI Data
active_sym = st.session_state.active_coin.split("/")[0]
ai_data = get_real_ai_sentiment(active_sym)
is_critical_danger = ai_data['label'] == "negative"

# ================= 🌟 DYNAMIC CSS (RED ALERT MODE) =================
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
        overscroll-behavior-y: none !important; overscroll-behavior-x: none !important;
        touch-action: pan-y !important; 
    }
    .block-container { padding-top: 15px !important; padding-right: 15px !important; padding-left: 10px !important; }
    ::-webkit-scrollbar { width: 16px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background-color: #FCD535; border-radius: 12px; border-style: solid; border-color: #0B0E11; border-width: 25px 4px; background-clip: padding-box; }
    .pos-card { background-color: #181A20; border-left: 4px solid #FCD535; border-radius: 8px; padding: 15px 15px 5px 15px; margin-top: 5px; margin-bottom: 5px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .pos-long { border-left-color: #00FF00; }
    .pos-short { border-left-color: #FF0000; }
    .history-box { background-color: #14181C; border: 1px solid #2B3139; border-radius: 8px; padding: 10px; margin-bottom: 15px; font-size: 12px; }
    .hist-row { display: flex; justify-content: space-between; border-bottom: 1px solid #1E2329; padding: 5px 0; }
    .feature-card { background: linear-gradient(135deg, #181A20 0%, #1E2329 100%); border: 1px solid #2B3139; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 10px;}
    .feature-title { color: #848E9C; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .feature-val { font-size: 18px; font-weight: bold; margin-top: 8px; }
    div.stButton > button { border-radius: 8px !important; font-weight: bold !important; width: 100% !important; margin-bottom: 2px; background-color: #181A20 !important; color: #EAECEF !important; border: 1px solid #2B3139 !important;}
    div.stButton > button:hover { border-color: #FCD535 !important; background-color: #2B3139 !important;}
    hr { border-color: #2B3139; margin: 15px 0; }
    </style>
""", unsafe_allow_html=True)

# 🚨 RED ALERT BANNER 
if is_critical_danger:
    st.markdown(f'<div class="alert-box">🚨 AI WARNING: MARKET DANGER ON {active_sym}! 🚨<br><span style="font-size:11px; font-weight:normal;">Live News: {ai_data["news"]}</span></div>', unsafe_allow_html=True)

def fetch_coin_radar(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        curr_vol, curr_price = df['volume'].iloc[-1], df['close'].iloc[-1]
        
        local_support, local_resistance = df['low'].tail(15).min(), df['high'].tail(15).max()
        
        price_spread = (local_resistance - local_support) / curr_price
        if price_spread < 0.0075: market_state, state_color = "↔️ SIDEWAYS", "#FCD535"
        elif curr_price > df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]: market_state, state_color = "📈 UP TREND", "#00FF00"
        elif curr_price < df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] < df['ema_20'].iloc[-1]: market_state, state_color = "📉 DOWN TREND", "#FF1744"
        else: market_state, state_color = "🔄 CHOPPY", "#848E9C"
            
        activity = "🟢 BUYERS 🔥" if rsi > 55 else ("🔴 SELLERS 🩸" if rsi < 45 else "⚖️ EQUAL")
        act_color = "#00FF00" if rsi > 55 else ("#FF1744" if rsi < 45 else "#848E9C")
            
        vol_ratio = (curr_vol / vol_sma) * 100
        vol_status = f"🔥 HIGH ({vol_ratio:.0f}%)" if curr_vol > vol_sma else f"❄️ LOW ({vol_ratio:.0f}%)"
        vol_color = "#00FF88" if curr_vol > vol_sma else "#848E9C"

        trend_50 = "BULLISH" if curr_price > df['ema_50'].iloc[-1] else "BEARISH"
        ema_bullish = df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]
        is_volume_high = curr_vol > vol_sma  
        macd_bullish = df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]
        
        signal_text, is_signal_active, signal_dir, alloc_pct = "🎯 SCANNING...", False, "NONE", 0.0
        
        # 🧠 AI SENTIMENT LOCK
        if trend_50 == "BULLISH" and ema_bullish and is_volume_high and rsi < 65 and macd_bullish:
            if is_critical_danger and coin.split("/")[0] == active_sym:
                signal_text = "🚫 BUY BLOCKED BY AI (REAL NEWS)"
            else:
                ai_score = min(50 + 20 + (15 if rsi < 45 else 0), 100)
                signal_text, is_signal_active, signal_dir = f"🚀 SNIPER BUY", True, "LONG"
                alloc_pct = 7.0 if ai_score >= 80 else 3.0
            
        elif trend_50 == "BEARISH" and not ema_bullish and is_volume_high and rsi > 35 and not macd_bullish:
            ai_score = min(50 + 20 + (15 if rsi > 55 else 0), 100)
            signal_text, is_signal_active, signal_dir = f"🧨 SNIPER SELL", True, "SHORT"
            alloc_pct = 7.0 if ai_score >= 80 else 3.0
                
        return {
            'price': curr_price, 'signal': signal_text, 'dir': signal_dir,
            'df': df, 'sup': local_support, 'res': local_resistance, 'atr': df['atr'].iloc[-1], 
            'is_signal_active': is_signal_active, 'alloc_pct': alloc_pct,
            'state': market_state, 'state_color': state_color, 'activity': activity, 'act_color': act_color,
            'vol_status': vol_status, 'vol_color': vol_color, 'vol_raw': curr_vol
        }
    except Exception as e: return None

radars = {c.split("/")[0]: fetch_coin_radar(c) for c in SCALPING_COINS}

# ================= 🤖 AUTO PAPER-TRADING ENGINE =================
time_since_app_opened = time.time() - st.session_state.app_start_time
bot_is_warmed_up = time_since_app_opened > 15 
data_changed = False 

current_time = time.time()
keys_to_del = [k for k, v in st.session_state.cooldowns.items() if current_time > v]
for k in keys_to_del: del st.session_state.cooldowns[k]

for symbol, data in radars.items():
    if not data: continue
    current_price = data['price']
    
    if symbol in st.session_state.bot_positions:
        pos = st.session_state.bot_positions[symbol]
        close_trade = False
        reason = ""
        if pos['dir'] == "LONG":
            pnl_pct = ((current_price - pos['entry']) / pos['entry']) * VIRTUAL_LEVERAGE
            if current_price >= pos['tp']: close_trade, reason = True, "🎯 Auto TP"
            elif current_price <= pos['sl']: close_trade, reason = True, "🛑 Auto SL"
            elif is_critical_danger and symbol == active_sym: 
                close_trade, reason = True, "🚨 AI EMERGENCY EXIT"
        else:
            pnl_pct = ((pos['entry'] - current_price) / pos['entry']) * VIRTUAL_LEVERAGE
            if current_price <= pos['tp']: close_trade, reason = True, "🎯 Auto TP"
            elif current_price >= pos['sl']: close_trade, reason = True, "🛑 Auto SL"
            
        pos['live_pnl'] = pos['invested_inr'] * pnl_pct
            
        if close_trade:
            fee_inr = pos['invested_inr'] * FEE_RATE * 2 
            net_pnl_inr = pos['live_pnl'] - fee_inr
            st.session_state.total_fees_paid += fee_inr
            st.session_state.available_balance_inr += pos['invested_inr'] + net_pnl_inr
            st.session_state.trade_history.insert(0, {'time': datetime.now().strftime("%H:%M"), 'coin': symbol, 'dir': pos['dir'], 'pnl': net_pnl_inr, 'reason': reason})
            st.session_state.cooldowns[symbol] = time.time() + 300
            del st.session_state.bot_positions[symbol]
            data_changed = True

    if st.session_state.auto_trade_active:
        if symbol not in st.session_state.bot_positions and data['is_signal_active'] and bot_is_warmed_up:
            if symbol not in st.session_state.cooldowns:
                invest_amount = st.session_state.total_balance_inr * (data['alloc_pct'] / 100.0)
                if st.session_state.available_balance_inr >= invest_amount and invest_amount > 10:
                    st.session_state.available_balance_inr -= invest_amount
                    atr_buffer = data['atr'] * 1.5 
                    if data['dir'] == "LONG":
                        sl = data['sup'] - atr_buffer
                        tp = current_price + ((current_price - sl) * 1.5) 
                    else:
                        sl = data['res'] + atr_buffer
                        tp = current_price - ((sl - current_price) * 1.5)
                    
                    st.session_state.bot_positions[symbol] = {
                        'dir': data['dir'], 'entry': current_price, 'invested_inr': invest_amount, 
                        'tp': tp, 'sl': sl, 'live_pnl': 0.0
                    }
                    st.toast(f"⚡ Sniper Auto-Trade: {symbol}", icon="🚀")
                    data_changed = True

active_invested = sum(p['invested_inr'] for p in st.session_state.bot_positions.values())
st.session_state.total_balance_inr = st.session_state.available_balance_inr + active_invested + sum(p['live_pnl'] for p in st.session_state.bot_positions.values())

if data_changed: save_trading_data()

# ================= 💼 TOP: MASTER PAPER TRADING BOX =================
tot_color = "#00FF00" if st.session_state.total_balance_inr >= 10000 else "#FF1744"
pnl_color = "#00FF00" if (st.session_state.total_balance_inr - 10000) >= 0 else "#FF1744"

st.markdown(f"""
    <div style="background: linear-gradient(135deg, #14181C 0%, #0B0E11 100%); border: 2px solid #2B3139; border-radius: 12px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 10px;">
        <div style="display:flex; justify-content:space-between; text-align:center; flex-wrap: nowrap;">
            <div style="flex: 1; padding: 0 2px;">
                <div style="font-size:9px; color:#848E9C; font-weight:bold; white-space:nowrap;">PORTFOLIO</div>
                <div style="font-size:13px; font-weight:bold; color:{tot_color}; white-space:nowrap;">₹{st.session_state.total_balance_inr:,.1f}</div>
            </div>
            <div style="flex: 1; border-left: 1px solid #2B3139; padding: 0 2px;">
                <div style="font-size:9px; color:#848E9C; font-weight:bold; white-space:nowrap;">NET PNL</div>
                <div style="font-size:13px; font-weight:bold; color:{pnl_color}; white-space:nowrap;">₹{st.session_state.total_balance_inr - 10000:,.1f}</div>
            </div>
            <div style="flex: 1; border-left: 1px solid #2B3139; padding: 0 2px;">
                <div style="font-size:9px; color:#848E9C; font-weight:bold; white-space:nowrap;">MARGIN</div>
                <div style="font-size:13px; font-weight:bold; color:#FCD535; white-space:nowrap;">₹{active_invested:,.1f}</div>
            </div>
            <div style="flex: 1; border-left: 1px solid #2B3139; padding: 0 2px;">
                <div style="font-size:9px; color:#848E9C; font-weight:bold; white-space:nowrap;">COINDCX FEE</div>
                <div style="font-size:13px; font-weight:bold; color:#FF1744; white-space:nowrap;">-₹{st.session_state.total_fees_paid:,.1f}</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 🎛️ CONTROL PANEL ROW: SWITCHES
switch_col1, switch_col2 = st.columns(2)
with switch_col1:
    bot_switch = st.toggle("🤖 AUTO-TRADING ENGINE ACTIVE", value=st.session_state.auto_trade_active)
    if bot_switch != st.session_state.auto_trade_active:
        st.session_state.auto_trade_active = bot_switch
        save_trading_data()
        st.rerun()

with switch_col2:
    pause_radar = False
    if st.session_state.bot_positions:
        pause_radar = st.checkbox("⏸️ PAUSE RADAR (Edit SL/Close)", value=False)

# 🟢 LIVE POSITIONS & MANUAL CONTROLS
if st.session_state.bot_positions:
    for c in list(st.session_state.bot_positions.keys()):
        p = st.session_state.bot_positions[c]
        card_class = "pos-long" if p['dir'] == "LONG" else "pos-short"
        
        st.markdown(f"""
            <div class="pos-card {card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div>
                        <div><span style="font-size:18px; font-weight:bold; color:#EAECEF;">{c}</span> <span style="background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; font-size:11px; color:{'#00FF00' if p['dir']=='LONG' else '#FF0000'};">{p['dir']}</span></div>
                        <div style="font-size:11px; color:#848E9C; margin-top:2px;">💰 Margin Used: ₹{p['invested_inr']:,.2f}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:18px; font-weight:bold; color:{'#00FF00' if p['live_pnl'] >= 0 else '#FF0000'};">₹{p['live_pnl']:,.2f}</div>
                    </div>
                </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1.5, 1.5, 1])
        with col1:
            if st.button(f"💰 Close (Take ₹{p['live_pnl']:.2f})", key=f"close_{c}"):
                fee_inr = p['invested_inr'] * FEE_RATE * 2
                net_pnl = p['live_pnl'] - fee_inr
                st.session_state.total_fees_paid += fee_inr
                st.session_state.available_balance_inr += p['invested_inr'] + net_pnl
                
                st.session_state.trade_history.insert(0, {'time': datetime.now().strftime("%H:%M"), 'coin': c, 'dir': p['dir'], 'pnl': net_pnl, 'reason': '👤 Manual Close'})
                st.session_state.cooldowns[c] = time.time() + 300
                del st.session_state.bot_positions[c]
                save_trading_data() 
                st.toast(f"✅ {c} Closed! Sent to History.", icon="💰")
                st.rerun()
        with col2:
            new_sl = st.number_input("New SL", value=float(p['sl']), format="%.4f", step=0.0001, key=f"sl_in_{c}", label_visibility="collapsed")
        with col3:
            if st.button("🔄 Set SL", key=f"upd_sl_{c}"):
                st.session_state.bot_positions[c]['sl'] = new_sl
                save_trading_data() 
                st.toast(f"🎯 Stop-Loss Updated for {c}", icon="✅")
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)

# 📜 TRADE HISTORY SECTION
if st.session_state.trade_history:
    with st.expander("📜 TRADE HISTORY (Last 10 Trades)", expanded=False):
        st.markdown('<div class="history-box">', unsafe_allow_html=True)
        for t in st.session_state.trade_history[:10]: 
            p_color = "#00FF00" if t['pnl'] >= 0 else "#FF1744"
            st.markdown(f"""
                <div class="hist-row">
                    <span style="color:#848E9C;">{t['time']}</span>
                    <span><b>{t['coin']}</b> ({t['dir']})</span>
                    <span style="color:#848E9C; font-size:10px;">{t['reason']}</span>
                    <span style="color:{p_color}; font-weight:bold;">₹{t['pnl']:.2f}</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ================= 🧭 MIDDLE: MARKET ANALYSIS =================
active_data = radars.get(active_sym)

if active_data:
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.markdown(f'<div class="feature-card"><div class="feature-title">🧭 MARKET ({active_sym})</div><div class="feature-val" style="color:{active_data["state_color"]};">{active_data["state"]}</div></div>', unsafe_allow_html=True)
    with f_col2:
        st.markdown(f'<div class="feature-card"><div class="feature-title">⚡ ORDERFLOW</div><div class="feature-val" style="color:{active_data["act_color"]};">{active_data["activity"]}</div></div>', unsafe_allow_html=True)
    with f_col3:
        st.markdown(f'<div class="feature-card"><div class="feature-title">📊 VOLUME</div><div class="feature-val" style="color:{active_data["vol_color"]};">{active_data["vol_status"]}</div></div>', unsafe_allow_html=True)

    # ================= ⚡ BOTTOM: CHART & FULL DETAILS =================
    chart_col, info_col = st.columns([2.3, 1])
    with chart_col:
        fig = go.Figure(data=[go.Candlestick(x=active_data['df'].index, open=active_data['df']['open'], high=active_data['df']['high'], low=active_data['df']['low'], close=active_data['df']['close'])])
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_9'], name='EMA 9', line=dict(color='#00BFFF', width=2)))
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_50'], name='EMA 50', line=dict(color='#FCD535', width=3, dash='dot')))
        
        fig.update_layout(
            template="plotly_dark", height=380, margin=dict(l=5, r=5, t=30, b=5), 
            xaxis_rangeslider_visible=False, 
            paper_bgcolor='#14181C', plot_bgcolor='#14181C',
            title=dict(text=f"📊 {active_sym} Live Chart", font=dict(size=14, color="#848E9C"), x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with info_col:
        dec = 4 if "DOGE" in active_sym or "XRP" in active_sym else 2
        sentiment_display = f"<div style='font-size:11px; margin-bottom:5px; color:#848E9C;'>🧠 AI Sentiment: <span style='color:{'#FF1744' if ai_data['label']=='negative' else '#00FF00' if ai_data['label']=='positive' else '#FCD535'}; text-transform:uppercase;'>{ai_data['label']}</span></div>"
        
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1E2329 0%, #14181C 100%); border-radius: 12px; padding: 15px; border: 1px solid #2B3139;">
                {sentiment_display}
                <div style="text-align:center; font-size:20px; font-weight:900; color:#FCD535;">{st.session_state.active_coin}</div>
                <div style="text-align:center; font-size:24px; font-weight:bold; color:#EAECEF; margin-bottom:10px;">${active_data['price']:,.{dec}f}</div>
                <div style="text-align:center; font-size:13px; font-weight:bold; background:rgba(0,0,0,0.4); padding:8px; border-radius:6px; border-bottom: 2px solid #FCD535;">{active_data['signal']}</div>
                <hr style="margin:10px 0; border-color:#2B3139;">
                <div style="font-size:12px; color:#848E9C; line-height:1.8;">
                    <b>🛡️ Support:</b> <span style="color:#00FF00; float:right;">${active_data['sup']:,.{dec}f}</span><br>
                    <b>🛑 Resist:</b> <span style="color:#FF1744; float:right;">${active_data['res']:,.{dec}f}</span><br>
                    <b>📉 ATR Vol:</b> <span style="color:#00BFFF; float:right;">{active_data['atr']:.4f}</span><br>
                    <b>📊 Live Vol:</b> <span style="color:#EAECEF; float:right;">{active_data['vol_raw']:,.0f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# 📡 COIN SELECTOR BUTTONS
def get_btn_label(name, data): 
    return f"⚡ {name} | ${data['price']:,.2f}" if data else f"{name} Error"

row1, row2 = st.columns(4), st.columns(4)
coin_keys = list(radars.keys())
for i, col_box in enumerate(row1 + row2):
    if i < len(coin_keys):
        c_sym = coin_keys[i]
        with col_box:
            if st.button(get_btn_label(c_sym, radars[c_sym]), key=f"nav_{c_sym}"): 
                st.session_state.active_coin = f"{c_sym}/USDT"
                st.rerun()

# 🗑️ RESET DATA BUTTON
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 Reset Demo Account (Delete Data)"):
    if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
    st.session_state.clear()
    st.toast("✅ Account Reset to ₹10,000!", icon="🔄")
    time.sleep(1)
    st.rerun()

# ⏱️ 7s BACKGROUND AUTO-REFRESH
if not pause_radar:
    time.sleep(7)
    st.rerun()
