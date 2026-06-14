import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 

# পেজ কনফিগারেশন (Premium Wide Layout)
st.set_page_config(page_title="BG STAR PRO SCALPER", layout="wide", initial_sidebar_state="collapsed")

# 🌟 Premium CSS Styling (Binance & BG Star Gold Theme)
st.markdown("""
    <style>
    /* Main Background */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0B0E11 !important;
        color: #EAECEF !important;
    }
    
    /* Header & Branding */
    .brand-title {
        font-size: 42px;
        font-weight: 900;
        background: -webkit-linear-gradient(45deg, #FCD535, #F39C12);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .sub-title { text-align: center; color: #848E9C; font-size: 16px; margin-bottom: 30px; letter-spacing: 1px; }
    .live-badge { background: rgba(0, 255, 0, 0.15); color: #00E676; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: bold; border: 1px solid #00E676; }
    
    /* Premium Cards */
    .pro-card {
        background-color: #1E2329;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #2B3139;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        text-align: center;
        transition: transform 0.3s ease;
    }
    .pro-card:hover { border-color: #FCD535; transform: translateY(-5px); }
    
    /* Signal Colors */
    .buy-signal { color: #00E676; text-shadow: 0px 0px 10px rgba(0,230,118,0.4); }
    .sell-signal { color: #FF1744; text-shadow: 0px 0px 10px rgba(255,23,68,0.4); }
    .wait-signal { color: #848E9C; }
    
    /* Data Text */
    .coin-name { font-size: 24px; font-weight: 800; color: #EAECEF; margin-bottom: 5px; }
    .price-text { font-size: 36px; font-weight: bold; margin-bottom: 15px; }
    .signal-text { font-size: 20px; font-weight: 900; letter-spacing: 1.5px; padding: 10px; border-radius: 8px; background: rgba(0,0,0,0.2); }
    
    /* Metrics */
    [data-testid="stMetricValue"] { color: #FCD535 !important; font-size: 24px !important; }
    [data-testid="stMetricLabel"] { color: #848E9C !important; font-weight: bold !important; }
    hr { border-color: #2B3139; }
    </style>
""", unsafe_allow_html=True)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m"  # প্রোফেশনাল লুকের জন্য ফিক্সড টাইমফ্রেম (ডিফল্ট)

# 🌟 Header Section
st.markdown('<div class="brand-title">BG STAR PRO TERMINAL</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title"><span class="live-badge">🟢 LIVE MARKET</span> | ALGORITHMIC SCALPING ENGINE V6</div>', unsafe_allow_html=True)

def get_scalp_signal(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        curr_price = df['close'].iloc[-1]
        curr_ema_50 = df['ema_50'].iloc[-1]
        trend_50 = "BULLISH" if curr_price > curr_ema_50 else "BEARISH"
        ema_bullish = df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]
        
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
        is_volume_high = curr_vol > vol_sma  
        macd_bullish = df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]
        
        local_support = df['low'].tail(15).min()
        local_resistance = df['high'].tail(15).max()
        
        signal_text = "WAITING FOR SETUP"
        css_class = "wait-signal"
        color_code = "#848E9C"
        
        if trend_50 == "BULLISH" and ema_bullish and macd_bullish and rsi < 65:
            if is_volume_high:
                signal_text = "🟢 STRONG BUY"
                css_class = "buy-signal"
                color_code = "#00E676"
            else:
                signal_text = "LOW VOL - WAIT"
        elif trend_50 == "BEARISH" and not ema_bullish and not macd_bullish and rsi > 35:
            if is_volume_high:
                signal_text = "🔴 STRONG SELL"
                css_class = "sell-signal"
                color_code = "#FF1744"
            else:
                signal_text = "LOW VOL - WAIT"
                
        return {
            'price': curr_price, 'signal': signal_text, 'css': css_class, 'color': color_code,
            'df': df, 'sup': local_support, 'res': local_resistance
        }
    except Exception as e:
        return None

# ================= 👑 THE FATHER: BITCOIN (MAIN TERMINAL) =================
btc_data = get_scalp_signal("BTC/USDT")

if btc_data:
    st.markdown("### 📊 MASTER ASSET: BITCOIN")
    c1, c2 = st.columns([1, 2.5])
    
    with c1:
        st.markdown(f"""
        <div class="pro-card">
            <div class="coin-name">BTC/USDT</div>
            <div class="price-text" style="color:{btc_data['color']}">${btc_data['price']:,.2f}</div>
            <div class="signal-text {btc_data['css']}">{btc_data['signal']}</div>
            <hr>
            <div style="text-align:left; color:#848E9C; font-size:14px;">
                <b>🎯 Target (TP):</b> <span style="color:#EAECEF; float:right;">${btc_data['res']:,.2f}</span><br>
                <b>🛡️ Stop Loss (SL):</b> <span style="color:#EAECEF; float:right;">${btc_data['sup']:,.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        fig = go.Figure(data=[go.Candlestick(x=btc_data['df'].index, open=btc_data['df']['open'], high=btc_data['df']['high'], low=btc_data['df']['low'], close=btc_data['df']['close'], name='Price')])
        fig.add_trace(go.Scatter(x=btc_data['df'].index, y=btc_data['df']['ema_9'], name='EMA 9', line=dict(color='#00BFFF', width=2)))
        fig.add_trace(go.Scatter(x=btc_data['df'].index, y=btc_data['df']['ema_20'], name='EMA 20', line=dict(color='#FF8C00', width=2)))
        fig.add_trace(go.Scatter(x=btc_data['df'].index, y=btc_data['df']['ema_50'], name='EMA 50 (Shield)', line=dict(color='#FCD535', width=3, dash='dot')))
        fig.update_layout(
            template="plotly_dark", height=320, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#848E9C')
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown("<br><hr>", unsafe_allow_html=True)

# ================= ⚡ FAST SCALPING RADAR (ALTCOINS) =================
st.markdown("### ⚡ ALTCOIN RADAR")

col_eth, col_sol, col_doge = st.columns(3)

def render_altcoin_card(coin_name, display_name, col_obj, decimals=2):
    data = get_scalp_signal(coin_name)
    if data:
        price_fmt = f"${data['price']:,.{decimals}f}"
        tp_fmt = f"${data['res']:,.{decimals}f}"
        sl_fmt = f"${data['sup']:,.{decimals}f}"
        
        with col_obj:
            st.markdown(f"""
            <div class="pro-card">
                <div class="coin-name">{display_name}</div>
                <div class="price-text" style="color:{data['color']}">{price_fmt}</div>
                <div class="signal-text {data['css']}">{data['signal']}</div>
                <hr style="margin: 15px 0;">
                <div style="display:flex; justify-content:space-between; font-size:13px;">
                    <span style="color:#00E676;">🎯 TP: {tp_fmt}</span>
                    <span style="color:#FF1744;">🛡️ SL: {sl_fmt}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

render_altcoin_card("ETH/USDT", "💠 ETHEREUM", col_eth, decimals=2)
render_altcoin_card("SOL/USDT", "🚀 SOLANA", col_sol, decimals=2)
render_altcoin_card("DOGE/USDT", "🐕 DOGECOIN", col_doge, decimals=4)

# Auto Refresh Hidden Engine
time.sleep(15)
st.rerun()
