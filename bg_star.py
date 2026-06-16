import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 
from datetime import datetime

# 👑 Premium Layout Config
st.set_page_config(page_title="BG STAR MARKET RADAR", layout="wide", initial_sidebar_state="collapsed")

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
        width: 36px; 
    }
    ::-webkit-scrollbar-track { 
        background: #0B0E11; 
    }
    ::-webkit-scrollbar-thumb { 
        background-color: #FCD535; 
        border-radius: 18px; 
        border-style: solid;
        border-color: #0B0E11;
        border-width: 35px 6px; 
        background-clip: padding-box;
    }
    ::-webkit-scrollbar-thumb:hover { 
        background-color: #F39C12; 
    }

    .brand-title { font-size: 32px; font-weight: 900; background: -webkit-linear-gradient(45deg, #00BFFF, #00FF88); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 0px; }
    .sub-title { text-align: center; color: #848E9C; font-size: 13px; margin-bottom: 15px; text-transform: uppercase; }
    
    /* নতুন ফিচার কার্ড স্টাইল */
    .feature-card { background: linear-gradient(135deg, #181A20 0%, #1E2329 100%); border: 1px solid #2B3139; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .feature-title { color: #848E9C; font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .feature-val { font-size: 20px; font-weight: bold; margin-top: 8px; }
    
    div.stButton > button { border-radius: 8px !important; font-weight: bold !important; width: 100% !important; margin-bottom: 2px; background-color: #181A20 !important; color: #EAECEF !important; border: 1px solid #2B3139 !important;}
    div.stButton > button:hover { border-color: #FCD535 !important; background-color: #2B3139 !important;}
    hr { border-color: #2B3139; margin: 15px 0; }
    </style>
""", unsafe_allow_html=True)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 

SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "AVAX/USDT", "LINK/USDT", "DOGE/USDT"]

if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"

st.markdown('<div class="brand-title">BG STAR PRO MARKET RADAR</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">📡 LIVE ALGORITHMIC SCANNER | MARKET STRUCTURE & ORDERFLOW PULSE</div>', unsafe_allow_html=True)

col_toggle1, col_toggle2, col_toggle3 = st.columns([1, 2, 1])
with col_toggle2:
    auto_refresh = st.toggle("🟢 Live 7s Auto-Refresh Scanner Active", value=True)

def fetch_coin_radar(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Indicators
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        # RSI & MACD
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
        
        # 1. 📈 MARKET CONDITION LOGIC (UP, DOWN, SIDEWAYS)
        price_spread = (local_resistance - local_support) / curr_price
        if price_spread < 0.0075: # যদি শেষ ১৫ ক্যান্ডেলের মুভমেন্ট ০.৭৫% এর নিচে হয়, তবে মার্কেট ফ্ল্যাট
            market_state = "↔️ SIDEWAYS (Ranging)"
            state_color = "#FCD535"
        elif curr_price > df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]:
            market_state = "📈 UP TREND (Bullish)"
            state_color = "#00FF00"
        elif curr_price < df['ema_50'].iloc[-1] and df['ema_9'].iloc[-1] < df['ema_20'].iloc[-1]:
            market_state = "📉 DOWN TREND (Bearish)"
            state_color = "#FF1744"
        else:
            market_state = "🔄 CHOPPY / SIDEWAYS"
            state_color = "#848E9C"
            
        # 2. 🟢 BUYERS VS SELLERS ACTIVE LOGIC
        if rsi > 55:
            activity = "🟢 BUYERS STRONG 🔥"
            act_color = "#00FF00"
        elif rsi < 45:
            activity = "🔴 SELLERS STRONG 🩸"
            act_color = "#FF1744"
        else:
            activity = "⚖️ EQUAL FIGHT (Neutral)"
            act_color = "#848E9C"
            
        # 3. 📊 VOLUME ANALYTICS LOGIC
        vol_ratio = (curr_vol / vol_sma) * 100
        if curr_vol > vol_sma:
            vol_status = f"🔥 HIGH ({vol_ratio:.1f}%)"
            vol_color = "#00FF88"
        else:
            vol_status = f"❄️ LOW ({vol_ratio:.1f}%)"
            vol_color = "#848E9C"
            
        # Sniper Signal
        trend_50 = "BULLISH" if curr_price > df['ema_50'].iloc[-1] else "BEARISH"
        ema_bullish = df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]
        is_volume_high = curr_vol > vol_sma  
        macd_bullish = df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]
        
        signal_text, css_class = "SCANNING...", "wait-glow"
        if trend_50 == "BULLISH" and p_spread := ema_bullish and is_volume_high and rsi < 65 and macd_bullish:
            signal_text, css_class = "🚀 SNIPER BUY SETUP", "buy-glow"
        elif trend_50 == "BEARISH" and not ema_bullish and is_volume_high and rsi > 35 and not macd_bullish:
            signal_text, css_class = "🧨 SNIPER SELL SETUP", "sell-glow"
            
        return {
            'price': curr_price, 'signal': signal_text, 'css': css_class, 'df': df,
            'sup': local_support, 'res': local_resistance, 'atr': df['atr'].iloc[-1],
            'state': market_state, 'state_color': state_color,
            'activity': activity, 'act_color': act_color,
            'vol_status': vol_status, 'vol_color': vol_color, 'vol_raw': curr_vol
        }
    except Exception as e: return None

# Fetch Data for All 8 Coins
radars = {c.split("/")[0]: fetch_coin_radar(c) for c in SCALPING_COINS}

active_symbol = st.session_state.active_coin.split("/")[0]
active_data = radars.get(active_symbol)

if active_data:
    # ================= 📊 LIVE DETECTOR DASHBOARD =================
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.markdown(f"""
            <div class="feature-card">
                <div class="feature-title">🧭 Market Condition ({active_symbol})</div>
                <div class="feature-val" style="color:{active_data['state_color']};">{active_data['state']}</div>
            </div>
        """, unsafe_allow_html=True)
    with f_col2:
        st.markdown(f"""
            <div class="feature-card">
                <div class="feature-title">⚡ Active Force (Orderflow)</div>
                <div class="feature-val" style="color:{active_data['act_color']};">{active_data['activity']}</div>
            </div>
        """, unsafe_allow_html=True)
    with f_col3:
        st.markdown(f"""
            <div class="feature-card">
                <div class="feature-title">📊 Volume Pulse (vs 20 SMA)</div>
                <div class="feature-val" style="color:{active_data['vol_color']};">{active_data['vol_status']}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ================= ⚡ CHARTS & DETAILED SIDEBAR =================
    chart_col, info_col = st.columns([2.3, 1])
    
    with chart_col:
        fig = go.Figure(data=[go.Candlestick(x=active_data['df'].index, open=active_data['df']['open'], high=active_data['df']['high'], low=active_data['df']['low'], close=active_data['df']['close'], name="Candle")])
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_9'], name='EMA 9', line=dict(color='#00BFFF', width=2)))
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_50'], name='EMA 50', line=dict(color='#FCD535', width=3, dash='dot')))
        fig.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        
    with info_col:
        dec = 4 if "DOGE" in active_symbol or "XRP" in active_symbol else 2
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1E2329 0%, #14181C 100%); border-radius: 12px; padding: 20px; border: 1px solid #2B3139; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
                <div style="text-align:center; font-size:14px; color:#848E9C; font-weight:bold;">SELECTED ASSET</div>
                <div style="text-align:center; font-size:28px; font-weight:900; color:#FCD535; margin-bottom:5px;">{st.session_state.active_coin}</div>
                <div style="text-align:center; font-size:32px; font-weight:bold; color:#EAECEF; margin-bottom:15px;">${active_data['price']:,.{dec}f}</div>
                <div style="text-align:center; font-size:16px; font-weight:bold; background:rgba(0,0,0,0.4); padding:10px; border-radius:6px; border-bottom: 3px solid #FCD535;">🎯 {active_data['signal']}</div>
                <hr style="margin:12px 0;">
                <div style="font-size:14px; color:#848E9C; line-height:2;">
                    <b>🛡️ Dynamic Support:</b> <span style="color:#00FF00; float:right;">${active_data['sup']:,.{dec}f}</span><br>
                    <b>🛑 Dynamic Resistance:</b> <span style="color:#FF1744; float:right;">${active_data['res']:,.{dec}f}</span><br>
                    <b>📉 ATR Volatility:</b> <span style="color:#00BFFF; float:right;">{active_data['atr']:.4f}</span><br>
                    <b>📊 Live Vol Units:</b> <span style="color:#EAECEF; float:right;">{active_data['vol_raw']:,.0f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ================= 📡 8-COIN NAVIGATION RADAR PANEL =================
st.markdown("<h4 style='text-align:center; color:#848E9C; letter-spacing:1px; font-size:15px;'>📡 LIVE COIN SELECTOR</h4>", unsafe_allow_html=True)
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

# ৭ সেকেন্ডের সুপার ফাস্ট রিফ্রেশ রেট
if auto_refresh: 
    time.sleep(7)
    st.rerun()
