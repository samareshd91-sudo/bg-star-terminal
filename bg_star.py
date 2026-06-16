import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 
from datetime import datetime

# 👑 Premium Layout Config
st.set_page_config(page_title="BG STAR ULTIMATE HYBRID", layout="wide", initial_sidebar_state="collapsed")

# 🌟 Ultra-Premium CSS (Chunky Scrollbar & Mobile Lock)
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main, .block-container { 
        background-color: #0B0E11 !important; color: #EAECEF !important; 
        overscroll-behavior-y: none !important; overscroll-behavior-x: none !important;
        touch-action: pan-y !important; 
    }
    
    /* 📱 কাস্টম প্রো স্ক্রলবার (মোটা ক্যাপসুল সাইজ) */
    ::-webkit-scrollbar { width: 36px; }
    ::-webkit-scrollbar-track { background: #0B0E11; }
    ::-webkit-scrollbar-thumb { 
        background-color: #FCD535; border-radius: 18px; 
        border-style: solid; border-color: #0B0E11; border-width: 35px 6px; 
        background-clip: padding-box;
    }
    ::-webkit-scrollbar-thumb:hover { background-color: #F39C12; }

    /* Cards */
    .wallet-card { background: linear-gradient(135deg, #181A20 0%, #1E2329 100%); border: 1px solid #2B3139; border-radius: 12px; padding: 15px; text-align: center; }
    .wallet-val { font-size: 22px; font-weight: bold; margin-top: 5px; }
    .pos-card { background-color: #181A20; border-left: 4px solid #FCD535; border-radius: 8px; padding: 15px; margin-top: 10px; margin-bottom: 5px; }
    .pos-long { border-left-color: #00FF00; }
    .pos-short { border-left-color: #FF0000; }
    
    .feature-card { background: linear-gradient(135deg, #181A20 0%, #1E2329 100%); border: 1px solid #2B3139; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 10px;}
    .feature-title { color: #848E9C; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .feature-val { font-size: 18px; font-weight: bold; margin-top: 8px; }
    
    div.stButton > button { border-radius: 8px !important; font-weight: bold !important; width: 100% !important; margin-bottom: 2px; background-color: #181A20 !important; color: #EAECEF !important; border: 1px solid #2B3139 !important;}
    div.stButton > button:hover { border-color: #FCD535 !important; background-color: #2B3139 !important;}
    hr { border-color: #2B3139; margin: 15px 0; }
    </style>
""", unsafe_allow_html=True)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 
FEE_RATE = 0.0005 
VIRTUAL_LEVERAGE = 10 

SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "AVAX/USDT", "LINK/USDT", "DOGE/USDT"]

# ================= 🧠 Bot Memory Setup (10,000 INR) =================
if 'app_start_time' not in st.session_state: st.session_state.app_start_time = time.time() 
if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"
if 'total_balance_inr' not in st.session_state: st.session_state.total_balance_inr = 10000.0
if 'available_balance_inr' not in st.session_state: st.session_state.available_balance_inr = 10000.0
if 'total_fees_paid' not in st.session_state: st.session_state.total_fees_paid = 0.0 
if 'bot_positions' not in st.session_state: st.session_state.bot_positions = {} 
if 'bot_history' not in st.session_state: st.session_state.bot_history = [] 

# ================= 🎛️ TOP TOGGLE (টাইটেল মুছে শুধু টগল রাখা হলো) =================
col_toggle1, col_toggle2, col_toggle3 = st.columns([1, 2, 1])
with col_toggle2:
    auto_refresh = st.toggle("🟢 Auto-Refresh & AI Auto-Trade Active", value=True)

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
        curr_vol = df['volume'].iloc[-1]
        curr_price = df['close'].iloc[-1]
        
        local_support = df['low'].tail(15).min()
        local_resistance = df['high'].tail(15).max()
        
        # Candlestick Logic
        curr_O, curr_C, curr_H, curr_L = df['open'].iloc[-1], df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
        prev_O, prev_C = df['open'].iloc[-2], df['close'].iloc[-2]
        curr_body = abs(curr_C - curr_O)
        prev_body = abs(prev_C - prev_O)
        curr_upper_shadow = curr_H - max(curr_C, curr_O)
        curr_lower_shadow = min(curr_C, curr_O) - curr_L
        
        pattern_score = 5 
        if curr_lower_shadow >= 2 * curr_body and curr_upper_shadow <= 0.2 * curr_body: pattern_score = 15 
        elif curr_upper_shadow >= 2 * curr_body and curr_lower_shadow <= 0.2 * curr_body: pattern_score = 15 
        elif prev_C < prev_O and curr_C > curr_O and curr_body > prev_body: pattern_score = 20 
        elif prev_C > prev_O and curr_C < curr_O and curr_body > prev_body: pattern_score = 20 

        # Market Analysis Data (For Cards)
        price_spread = (local_resistance - local_support) / curr_price
        if price_spread < 0.0075:
            market_state, state_color = "↔️ SIDEWAYS (Ranging)", "#FCD535"
        elif curr_price > df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]:
            market_state, state_color = "📈 UP TREND (Bullish)", "#00FF00"
        elif curr_price < df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] < df['ema_20'].iloc[-1]:
            market_state, state_color = "📉 DOWN TREND (Bearish)", "#FF1744"
        else:
            market_state, state_color = "🔄 CHOPPY / SIDEWAYS", "#848E9C"
            
        activity = "🟢 BUYERS STRONG 🔥" if rsi > 55 else ("🔴 SELLERS STRONG 🩸" if rsi < 45 else "⚖️ EQUAL FIGHT (Neutral)")
        act_color = "#00FF00" if rsi > 55 else ("#FF1744" if rsi < 45 else "#848E9C")
            
        vol_ratio = (curr_vol / vol_sma) * 100
        vol_status = f"🔥 HIGH ({vol_ratio:.1f}%)" if curr_vol > vol_sma else f"❄️ LOW ({vol_ratio:.1f}%)"
        vol_color = "#00FF88" if curr_vol > vol_sma else "#848E9C"

        # AI Confidence Sizing & Entry Logic
        trend_50 = "BULLISH" if curr_price > df['ema_50'].iloc[-1] else "BEARISH"
        ema_bullish = df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]
        is_volume_high = curr_vol > vol_sma  
        macd_bullish = df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]
        
        signal_text, css_class, is_signal_active, signal_dir = "🎯 SCANNING...", "wait-glow", False, "NONE"
        ai_score = 0
        alloc_pct = 0.0
        
        if trend_50 == "BULLISH" and ema_bullish and is_volume_high and rsi < 65 and macd_bullish:
            ai_score = 50 + pattern_score
            if rsi < 45: ai_score += 15 
            ai_score = min(ai_score, 100)
            signal_text, css_class, is_signal_active, signal_dir = f"🚀 SNIPER BUY SETUP", "buy-glow", True, "LONG"
            
        elif trend_50 == "BEARISH" and not ema_bullish and is_volume_high and rsi > 35 and not macd_bullish:
            ai_score = 50 + pattern_score
            if rsi > 55: ai_score += 15 
            ai_score = min(ai_score, 100)
            signal_text, css_class, is_signal_active, signal_dir = f"🧨 SNIPER SELL SETUP", "sell-glow", True, "SHORT"
            
        if ai_score >= 90: alloc_pct = 10.0
        elif ai_score >= 80: alloc_pct = 7.0
        elif ai_score >= 70: alloc_pct = 5.0
        elif ai_score >= 60: alloc_pct = 3.0
        elif ai_score > 0: alloc_pct = 1.0
                
        return {
            'price': curr_price, 'signal': signal_text, 'css': css_class, 'dir': signal_dir,
            'df': df, 'sup': local_support, 'res': local_resistance, 'atr': df['atr'].iloc[-1], 
            'is_signal_active': is_signal_active, 'ai_score': ai_score, 'alloc_pct': alloc_pct,
            'state': market_state, 'state_color': state_color, 'activity': activity, 'act_color': act_color,
            'vol_status': vol_status, 'vol_color': vol_color, 'vol_raw': curr_vol
        }
    except Exception as e: return None

radars = {c.split("/")[0]: fetch_coin_radar(c) for c in SCALPING_COINS}

# ================= 🤖 TRADING ENGINE (SILENT BACKGROUND) =================
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
        if bot_is_warmed_up:
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

# ================= 📊 TOP: TRADING DASHBOARD =================
w_col1, w_col2, w_col3, w_col4 = st.columns(4)
with w_col1: st.markdown(f'<div class="wallet-card"><div style="color:#848E9C; font-size:11px;">TOTAL PORTFOLIO (INR)</div><div class="wallet-val" style="color:{"#00FF00" if st.session_state.total_balance_inr >= 10000 else "#FF0000"};">₹{st.session_state.total_balance_inr:,.2f}</div></div>', unsafe_allow_html=True)
with w_col2: st.markdown(f'<div class="wallet-card"><div style="color:#848E9C; font-size:11px;">NET PROFIT/LOSS</div><div class="wallet-val" style="color:{"#00FF00" if (st.session_state.total_balance_inr - 10000) >= 0 else "#FF0000"};">₹{st.session_state.total_balance_inr - 10000:,.2f}</div></div>', unsafe_allow_html=True)
with w_col3: st.markdown(f'<div class="wallet-card"><div style="color:#848E9C; font-size:11px;">ACTIVE MARGIN</div><div class="wallet-val" style="color:#FCD535;">₹{active_invested:,.2f}</div></div>', unsafe_allow_html=True)
with w_col4: st.markdown(f'<div class="wallet-card"><div style="color:#848E9C; font-size:11px;">FEES PAID</div><div class="wallet-val" style="color:#FF1744;">-₹{st.session_state.total_fees_paid:,.2f}</div></div>', unsafe_allow_html=True)

# 🟢 LIVE POSITIONS
if st.session_state.bot_positions:
    for c in list(st.session_state.bot_positions.keys()):
        p = st.session_state.bot_positions[c]
        card_class = "pos-long" if p['dir'] == "LONG" else "pos-short"
        st.markdown(f"""
            <div class="pos-card {card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div><span style="font-size:18px; font-weight:bold; color:#EAECEF;">{c}</span> <span style="background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; font-size:11px; color:{'#00FF00' if p['dir']=='LONG' else '#FF0000'};">{p['dir']}</span></div>
                    <div style="font-size:18px; font-weight:bold; color:{'#00FF00' if p['live_pnl'] >= 0 else '#FF0000'};">₹{p['live_pnl']:,.2f}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# ================= 🧭 MIDDLE: ANALYSIS RADAR (FOR SELECTED COIN) =================
active_symbol = st.session_state.active_coin.split("/")[0]
active_data = radars.get(active_symbol)

if active_data:
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.markdown(f'<div class="feature-card"><div class="feature-title">🧭 MARKET ({active_symbol})</div><div class="feature-val" style="color:{active_data["state_color"]};">{active_data["state"]}</div></div>', unsafe_allow_html=True)
    with f_col2:
        st.markdown(f'<div class="feature-card"><div class="feature-title">⚡ ORDERFLOW</div><div class="feature-val" style="color:{active_data["act_color"]};">{active_data["activity"]}</div></div>', unsafe_allow_html=True)
    with f_col3:
        st.markdown(f'<div class="feature-card"><div class="feature-title">📊 VOLUME PULSE</div><div class="feature-val" style="color:{active_data["vol_color"]};">{active_data["vol_status"]}</div></div>', unsafe_allow_html=True)

    # ================= ⚡ BOTTOM: CHARTS =================
    chart_col, info_col = st.columns([2.3, 1])
    with chart_col:
        fig = go.Figure(data=[go.Candlestick(x=active_data['df'].index, open=active_data['df']['open'], high=active_data['df']['high'], low=active_data['df']['low'], close=active_data['df']['close'])])
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_9'], name='EMA 9', line=dict(color='#00BFFF', width=2)))
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_50'], name='EMA 50', line=dict(color='#FCD535', width=3, dash='dot')))
        fig.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        
    with info_col:
        dec = 4 if "DOGE" in active_symbol or "XRP" in active_symbol else 2
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1E2329 0%, #14181C 100%); border-radius: 12px; padding: 15px; border: 1px solid #2B3139;">
                <div style="text-align:center; font-size:24px; font-weight:900; color:#FCD535;">{st.session_state.active_coin}</div>
                <div style="text-align:center; font-size:28px; font-weight:bold; color:#EAECEF; margin-bottom:10px;">${active_data['price']:,.{dec}f}</div>
                <div style="text-align:center; font-size:14px; font-weight:bold; background:rgba(0,0,0,0.4); padding:8px; border-radius:6px; border-bottom: 2px solid #FCD535;">{active_data['signal']}</div>
                <hr style="margin:10px 0;">
                <div style="font-size:12px; color:#848E9C; line-height:1.8;">
                    <b>🛡️ Support:</b> <span style="color:#00FF00; float:right;">${active_data['sup']:,.{dec}f}</span><br>
                    <b>🛑 Resist:</b> <span style="color:#FF1744; float:right;">${active_data['res']:,.{dec}f}</span><br>
                    <b>📉 ATR Vol:</b> <span style="color:#00BFFF; float:right;">{active_data['atr']:.4f}</span>
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

# 7s Auto Refresh
if auto_refresh: 
    time.sleep(7)
    st.rerun()
