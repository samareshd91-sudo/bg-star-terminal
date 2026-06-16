import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 
from datetime import datetime

# 👑 Premium Layout Config
st.set_page_config(page_title="BG STAR HYBRID BOT", layout="wide", initial_sidebar_state="collapsed")

# 🌟 Ultra-Premium CSS (Mobile Optimized & Super Chunky Short Scrollbar)
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main, .block-container { 
        background-color: #0B0E11 !important; color: #EAECEF !important; 
        overscroll-behavior-y: none !important; overscroll-behavior-x: none !important;
        touch-action: pan-y !important; 
    }
    
    /* 📱 কাস্টম প্রো স্ক্রলবার (চওড়াতে দ্বিগুণ এবং লম্বাতে ছোট ক্যাপসুল সাইজ) */
    ::-webkit-scrollbar { 
        width: 36px; /* আগের ১৮px থেকে বাড়িয়ে একদম দ্বিগুণ (৩৬px) চওড়া করা হলো */
    }
    ::-webkit-scrollbar-track { 
        background: #0B0E11; 
    }
    ::-webkit-scrollbar-thumb { 
        background-color: #FCD535; 
        border-radius: 18px; 
        border-style: solid;
        border-color: #0B0E11;
        border-width: 35px 6px; /* ওপর-নিচে ৩৫px বর্ডার প্যাডিং দিয়ে লম্বাতে একদম ছোট (Short) করা হলো */
        background-clip: padding-box;
    }
    ::-webkit-scrollbar-thumb:hover { 
        background-color: #F39C12; 
    }

    .brand-title { font-size: 32px; font-weight: 900; background: -webkit-linear-gradient(45deg, #00BFFF, #00FF88); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 0px; }
    .sub-title { text-align: center; color: #848E9C; font-size: 13px; margin-bottom: 15px; text-transform: uppercase; }
    .wallet-card { background: linear-gradient(135deg, #181A20 0%, #1E2329 100%); border: 1px solid #2B3139; border-radius: 12px; padding: 15px; text-align: center; }
    .wallet-val { font-size: 24px; font-weight: bold; margin-top: 5px; }
    .pos-card { background-color: #181A20; border-left: 4px solid #FCD535; border-radius: 8px; padding: 15px; margin-top: 10px; margin-bottom: 5px; }
    .pos-long { border-left-color: #00FF00; }
    .pos-short { border-left-color: #FF0000; }
    div.stButton > button { border-radius: 6px !important; font-weight: bold !important; width: 100% !important; margin-top: 2px; }
    hr { border-color: #2B3139; margin: 15px 0; }
    </style>
""", unsafe_allow_html=True)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 
FEE_RATE = 0.0005 
VIRTUAL_LEVERAGE = 10 

SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "AVAX/USDT", "LINK/USDT", "DOGE/USDT"]

# ================= 🧠 Bot Memory Setup =================
if 'app_start_time' not in st.session_state: st.session_state.app_start_time = time.time() 
if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"
if 'total_balance_inr' not in st.session_state: st.session_state.total_balance_inr = 10000.0
if 'available_balance_inr' not in st.session_state: st.session_state.available_balance_inr = 10000.0
if 'total_fees_paid' not in st.session_state: st.session_state.total_fees_paid = 0.0 
if 'bot_positions' not in st.session_state: st.session_state.bot_positions = {} 
if 'bot_history' not in st.session_state: st.session_state.bot_history = [] 

st.markdown('<div class="brand-title">BG STAR PRO HYBRID-SCALPER</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">🛡️ SMART INITIAL WARM-UP | ⚡ INSTANT SNIPER ENTRY</div>', unsafe_allow_html=True)

col_toggle1, col_toggle2, col_toggle3 = st.columns([1, 2, 1])
with col_toggle2:
    auto_refresh = st.toggle("🟢 Auto-Refresh & Bot Active (SL এডিট করার সময় অফ রাখুন)", value=True)

def fetch_coin_radar(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        
        curr_price = df['close'].iloc[-1]
        trend_50 = "BULLISH" if curr_price > df['ema_50'].iloc[-1] else "BEARISH"
        ema_bullish = df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]
        is_volume_high = df['volume'].iloc[-1] > vol_sma  
        macd_bullish = df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]
        
        local_support = df['low'].tail(15).min()
        local_resistance = df['high'].tail(15).max()
        
        curr_O, curr_C, curr_H, curr_L = df['open'].iloc[-1], df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
        prev_O, prev_C = df['open'].iloc[-2], df['close'].iloc[-2]
        curr_body = abs(curr_C - curr_O)
        prev_body = abs(prev_C - prev_O)
        curr_upper_shadow = curr_H - max(curr_C, curr_O)
        curr_lower_shadow = min(curr_C, curr_O) - curr_L
        
        pattern_score = 5 
        if curr_lower_shadow >= 2 * curr_body and curr_upper_shadow <= 0.2 * curr_body: pattern_score = 15 
        elif curr_upper_shadow >= 2 * curr_body && curr_lower_shadow <= 0.2 * curr_body: pattern_score = 15 
        elif prev_C < prev_O and curr_C > curr_O and curr_body > prev_body: pattern_score = 20 
        elif prev_C > prev_O and curr_C < curr_O and curr_body > prev_body: pattern_score = 20 

        signal_text, css_class, is_signal_active, signal_dir = "WAITING...", "wait-glow", False, "NONE"
        ai_score = 0
        alloc_pct = 0.0
        
        if trend_50 == "BULLISH" and ema_bullish and is_volume_high and rsi < 65:
            ai_score = 50 + pattern_score
            if macd_bullish: ai_score += 20 
            if rsi < 45: ai_score += 15 
            ai_score = min(ai_score, 100)
            signal_text, css_class, is_signal_active, signal_dir = f"🟢 BUY ({ai_score}/100)", "buy-glow", True, "LONG"
            
        elif trend_50 == "BEARISH" and not ema_bullish and is_volume_high and rsi > 35:
            ai_score = 50 + pattern_score
            if not macd_bullish: ai_score += 20 
            if rsi > 55: ai_score += 15 
            ai_score = min(ai_score, 100)
            signal_text, css_class, is_signal_active, signal_dir = f"🔴 SELL ({ai_score}/100)", "sell-glow", True, "SHORT"
            
        if ai_score >= 90: alloc_pct = 10.0
        elif ai_score >= 80: alloc_pct = 7.0
        elif ai_score >= 70: alloc_pct = 5.0
        elif ai_score >= 60: alloc_pct = 3.0
        elif ai_score > 0: alloc_pct = 1.0
                
        return {
            'price': curr_price, 'signal': signal_text, 'css': css_class, 'dir': signal_dir,
            'df': df, 'sup': local_support, 'res': local_resistance, 'atr': df['atr'].iloc[-1], 
            'is_signal_active': is_signal_active, 'ai_score': ai_score, 'alloc_pct': alloc_pct
        }
    except Exception as e: return None

radars = {c.split("/")[0]: fetch_coin_radar(c) for c in SCALPING_COINS}

# ================= 🤖 TRADING ENGINE & LIVE PNL =================
time_since_app_opened = time.time() - st.session_state.app_start_time
bot_is_warmed_up = time_since_app_opened > 15 

for symbol, data in radars.items():
    if not data: continue
    current_price = data['price']
    
    # 1. Manage Active Positions
    if symbol in st.session_state.bot_positions:
        pos = st.session_state.bot_positions[symbol]
        close_trade, reason = False, ""
        
        if pos['dir'] == "LONG":
            pnl_pct = ((current_price - pos['entry']) / pos['entry']) * VIRTUAL_LEVERAGE
            if current_price >= pos['tp']: close_trade, reason = True, "🎯 Auto TP Hit"
            elif current_price <= pos['sl']: close_trade, reason = True, "🛑 SL Hit"
        else:
            pnl_pct = ((pos['entry'] - current_price) / pos['entry']) * VIRTUAL_LEVERAGE
            if current_price <= pos['tp']: close_trade, reason = True, "🎯 Auto TP Hit"
            elif current_price >= pos['sl']: close_trade, reason = True, "🛑 SL Hit"
            
        pos['live_pnl'] = pos['invested_inr'] * pnl_pct
            
        if close_trade:
            fee_inr = pos['invested_inr'] * FEE_RATE * 2 
            net_pnl_inr = pos['live_pnl'] - fee_inr
            st.session_state.total_fees_paid += fee_inr
            st.session_state.available_balance_inr += pos['invested_inr'] + net_pnl_inr
            st.session_state.bot_history.insert(0, {'time': datetime.now().strftime("%H:%M:%S"), 'coin': symbol, 'dir': pos['dir'], 'entry': pos['entry'], 'exit': current_price, 'reason': reason, 'pnl': net_pnl_inr, 'fee': fee_inr})
            del st.session_state.bot_positions[symbol]

    # 2. ⚡ INSTANT SNIPER ENTRY
    if symbol not in st.session_state.bot_positions and data['is_signal_active']:
        if not bot_is_warmed_up:
            st.toast(f"🛡️ App Initializing... Scanning {symbol} without trading.", icon="🔍")
        else:
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
                    'tp': tp, 'sl': sl, 'live_pnl': 0.0, 'score': data['ai_score'], 'pct': data['alloc_pct']
                }
                st.toast(f"⚡ Instant Sniper Entry: {symbol} | Confidence {data['ai_score']}", icon="🚀")

active_invested = sum(p['invested_inr'] for p in st.session_state.bot_positions.values())
unrealized_pnl = sum(p['live_pnl'] for p in st.session_state.bot_positions.values())
st.session_state.total_balance_inr = st.session_state.available_balance_inr + active_invested + unrealized_pnl

# ================= 📊 10,000 INR DASHBOARD =================
w_col1, w_col2, w_col3, w_col4 = st.columns(4)
with w_col1: st.markdown(f'<div class="wallet-card"><div style="color:#848E9C; font-size:12px;">Total Portfolio (INR)</div><div class="wallet-val" style="color:{"#00FF00" if st.session_state.total_balance_inr >= 10000 else "#FF0000"};">₹{st.session_state.total_balance_inr:,.2f}</div></div>', unsafe_allow_html=True)
with w_col2: st.markdown(f'<div class="wallet-card"><div style="color:#848E9C; font-size:12px;">Net Profit/Loss</div><div class="wallet-val" style="color:{"#00FF00" if (st.session_state.total_balance_inr - 10000) >= 0 else "#FF0000"};">₹{st.session_state.total_balance_inr - 10000:,.2f}</div></div>', unsafe_allow_html=True)
with w_col3: st.markdown(f'<div class="wallet-card"><div style="color:#848E9C; font-size:12px;">Active Margin (Locked)</div><div class="wallet-val" style="color:#FCD535;">₹{active_invested:,.2f}</div></div>', unsafe_allow_html=True)
with w_col4: st.markdown(f'<div class="wallet-card"><div style="color:#848E9C; font-size:12px;">Total Exchange Fees Paid</div><div class="wallet-val" style="color:#FF1744;">-₹{st.session_state.total_fees_paid:,.2f}</div></div>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ================= 🔴 LIVE POSITIONS & MANUAL CONTROLS =================
col_pos, col_hist = st.columns([1.3, 1])

with col_pos:
    st.markdown("<h4 style='color:#EAECEF;'>🟢 Live Positions (AI Controlled)</h4>", unsafe_allow_html=True)
    if not st.session_state.bot_positions: st.markdown("<div style='color:#848E9C; text-align:center; padding:20px; background:#181A20; border-radius:8px;'>No active trades. Scanning 8 coins...</div>", unsafe_allow_html=True)
    else:
        for c in list(st.session_state.bot_positions.keys()):
            p = st.session_state.bot_positions[c]
            curr_p = radars[c]['price']
            card_class = "pos-long" if p['dir'] == "LONG" else "pos-short"
            ai_tag = f"🧠 Score: {p.get('score', 'Manual')} ({p.get('pct', 'Manual')}%)"
            
            st.markdown(f"""
                <div class="pos-card {card_class}">
                    <div style="display:flex; justify-content:space-between;">
                        <div><span style="font-size:20px; font-weight:bold; color:#EAECEF;">{c}</span> <span style="background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; font-size:12px; color:{'#00FF00' if p['dir']=='LONG' else '#FF0000'};">{p['dir']} | {ai_tag}</span></div>
                        <div style="text-align:right;"><div style="font-size:20px; font-weight:bold; color:{'#00FF00' if p['live_pnl'] >= 0 else '#FF0000'};">₹{p['live_pnl']:,.2f}</div></div>
                    </div>
                    <div style="font-size:13px; color:#848E9C; margin-bottom: 10px;">Entry: ${p['entry']:,.4f} | Margin: ₹{p['invested_inr']:,.2f} | Target: <span style="color:#00FF00;">${p['tp']:,.4f}</span></div>
                </div>
            """, unsafe_allow_html=True)
            
            act_col1, act_col2, act_col3 = st.columns([1.2, 1.5, 1])
            with act_col1:
                if st.button(f"💰 Close & Take ₹{p['live_pnl']:.2f}", key=f"close_{c}"):
                    fee = p['invested_inr'] * FEE_RATE * 2
                    net_pnl = p['live_pnl'] - fee
                    st.session_state.total_fees_paid += fee
                    st.session_state.available_balance_inr += p['invested_inr'] + net_pnl
                    st.session_state.bot_history.insert(0, {'time': datetime.now().strftime("%H:%M:%S"), 'coin': c, 'dir': p['dir'], 'entry': p['entry'], 'exit': curr_p, 'reason': "✋ Manual Exit", 'pnl': net_pnl, 'fee': fee})
                    del st.session_state.bot_positions[c]
                    st.rerun()
            with act_col2:
                new_sl = st.number_input("Modify Stop-Loss", value=float(p['sl']), format="%.4f", step=0.0001, key=f"sl_in_{c}", label_visibility="collapsed")
            with act_col3:
                if st.button("🔄 Set SL", key=f"upd_sl_{c}"):
                    st.session_state.bot_positions[c]['sl'] = new_sl
                    st.toast(f"Stop-Loss updated for {c}", icon="✅")
                    st.rerun()

with col_hist:
    st.markdown("<h4 style='color:#EAECEF;'>📜 Trade History</h4>", unsafe_allow_html=True)
    if not st.session_state.bot_history: st.markdown("<div style='color:#848E9C; text-align:center; padding:20px; background:#181A20; border-radius:8px;'>No closed trades.</div>", unsafe_allow_html=True)
    else:
        for h in st.session_state.bot_history[:5]: 
            st.markdown(f'<div style="background:#181A20; border: 1px solid #2B3139; border-radius: 8px; padding: 10px; margin-bottom: 10px;"><div style="display:flex; justify-content:space-between;"><span style="font-weight:bold; color:#EAECEF;">{h["coin"]} <span style="font-size:12px; color:#848E9C;">{h["dir"]}</span></span><span style="font-weight:bold; color:{"#00FF00" if h["pnl"] > 0 else "#FF0000"};">₹{h["pnl"]:,.2f}</span></div><div style="font-size:12px; color:#848E9C; margin-top:5px;">{h["time"]} | <b>{h["reason"]}</b> (Fee: ₹{h["fee"]:.2f})<br>En: ${h["entry"]:,.4f} → Ex: ${h["exit"]:,.4f}</div></div>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ================= ⚡ CHARTS & FORCE ENTRY =================
st.markdown("<h4 style='text-align:center; color:#848E9C;'>📡 AI COIN RADAR & CHARTS</h4>", unsafe_allow_html=True)
def get_btn(name, radar): return f"⚡ {name}\n${radar['price']:,.4f}" if radar else f"{name} Error"
row1, row2 = st.columns(4), st.columns(4)
coin_keys = list(radars.keys())
for i, col_box in enumerate(row1 + row2):
    if i < len(coin_keys):
        c_sym = coin_keys[i]
        with col_box:
            if st.button(get_btn(c_sym, radars[c_sym]), key=f"nav_{c_sym}"): st.session_state.active_coin = f"{c_sym}/USDT"

active_data = radars.get(st.session_state.active_coin.split("/")[0])
if active_data:
    chart_col, info_col = st.columns([2.5, 1])
    with chart_col:
        fig = go.Figure(data=[go.Candlestick(x=active_data['df'].index, open=active_data['df']['open'], high=active_data['df'].high, low=active_data['df'].low, close=active_data['df'].close)])
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_9'], name='EMA 9', line=dict(color='#00BFFF', width=2)))
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_50'], name='EMA 50', line=dict(color='#FCD535', width=3, dash='dot')))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    with info_col:
        st.markdown(f'<div style="background: linear-gradient(135deg, #1E2329 0%, #14181C 100%); border-radius: 12px; padding: 15px; border: 1px solid #2B3139;"><div style="text-align:center; font-size:20px; font-weight:bold; color:#FCD535; margin-bottom:10px;">{st.session_state.active_coin}</div><div class="{active_data["css"]}" style="text-align:center; font-size:18px; margin-bottom:15px; background: rgba(0,0,0,0.3); padding:8px; border-radius:6px;">{active_data["signal"]}</div></div>', unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; font-size:13px; color:#848E9C; margin: 10px 0;'>🎮 Force Trade Override (Fixed 5% Margin)</div>", unsafe_allow_html=True)
        btn_col1, btn_col2 = st.columns(2)
        c_name = st.session_state.active_coin.split("/")[0]
        with btn_col1:
            if st.button("🟢 BUY", key=f"fb_{c_name}"):
                if c_name not in st.session_state.bot_positions:
                    st.session_state.bot_positions[c_name] = {'dir': "LONG", 'entry': active_data['price'], 'invested_inr': st.session_state.total_balance_inr * 0.05, 'tp': active_data['price']*1.02, 'sl': active_data['price']*0.99, 'live_pnl': 0.0}; st.rerun()
        with btn_col2:
            if st.button("🔴 SELL", key=f"fs_{c_name}"):
                if c_name not in st.session_state.bot_positions:
                    st.session_state.bot_positions[c_name] = {'dir': "SHORT", 'entry': active_data['price'], 'invested_inr': st.session_state.total_balance_inr * 0.05, 'tp': active_data['price']*0.98, 'sl': active_data['price']*1.01, 'live_pnl': 0.0}; st.rerun()

# ৭ সেকেন্ডের ফাস্ট রিফ্রেশ রেট
if auto_refresh: time.sleep(7); st.rerun()
