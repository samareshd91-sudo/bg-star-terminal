import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 

# 👑 Premium Layout Config
st.set_page_config(page_title="BG STAR ADVANCED TERMINAL", layout="wide", initial_sidebar_state="collapsed")

# 🌟 Ultra-Premium CSS
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0B0E11 !important;
        color: #EAECEF !important;
        overscroll-behavior: none !important; 
    }
    .brand-title {
        font-size: 36px;
        font-weight: 900;
        background: -webkit-linear-gradient(45deg, #FCD535, #F39C12);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 3px;
        margin-bottom: 0px;
    }
    .sub-title { text-align: center; color: #848E9C; font-size: 14px; margin-bottom: 15px; }
    
    .buy-glow { color: #00FF00; font-weight: 900; text-shadow: 0px 0px 10px rgba(0,255,0,0.5); }
    .sell-glow { color: #FF0000; font-weight: 900; text-shadow: 0px 0px 10px rgba(255,0,0,0.5); }
    .wait-glow { color: #848E9C; font-weight: bold; }
    
    .main-detail-card {
        background: linear-gradient(135deg, #1E2329 0%, #14181C 100%);
        border-radius: 16px;
        padding: 25px;
        border: 1px solid #FCD535;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    div.stButton > button {
        background-color: #1E2329 !important;
        color: #EAECEF !important;
        border: 1px solid #2B3139 !important;
        border-radius: 12px !important;
        width: 100% !important;
        padding: 10px !important;
        transition: all 0.3s ease !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }
    div.stButton > button:hover {
        border-color: #FCD535 !important;
        background-color: #2B3139 !important;
        transform: translateY(-2px);
    }
    hr { border-color: #2B3139; margin: 15px 0; }
    
    .streamlit-expanderContent { color: #EAECEF !important; }
    </style>
""", unsafe_allow_html=True)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 

# ================= 🧠 Permanent Memory Setup =================
if 'active_coin' not in st.session_state:
    st.session_state.active_coin = "BTC/USDT"
if 'user_capital' not in st.session_state:
    st.session_state['user_capital'] = 100.0
if 'user_risk' not in st.session_state:
    st.session_state['user_risk'] = 2.0

st.markdown('<div class="brand-title">BG STAR PRO TERMINAL</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">🔴 LIVE ALGORITHMIC RADAR | AI CANDLE & RISK MANAGER ACTIVE</div>', unsafe_allow_html=True)

# 🛑 অটো-রিফ্রেশ কন্ট্রোল বাটন
col_toggle1, col_toggle2, col_toggle3 = st.columns([1, 2, 1])
with col_toggle2:
    auto_refresh = st.toggle("🟢 Live Auto-Refresh (ফান্ড লেখার সময় এটি অফ করে নিতে পারেন)", value=True)

def fetch_coin_radar(coin):
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
        
        # 🕯️ AI Candlestick Engine
        curr_O, curr_C, curr_H, curr_L = df['open'].iloc[-1], df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
        prev_O, prev_C = df['open'].iloc[-2], df['close'].iloc[-2]
        
        curr_body = abs(curr_C - curr_O)
        curr_upper_shadow = curr_H - max(curr_C, curr_O)
        curr_lower_shadow = min(curr_C, curr_O) - curr_L
        curr_range = curr_H - curr_L if (curr_H - curr_L) > 0 else 0.0001 
        prev_body = abs(prev_C - prev_O)
        
        pattern_text = "সাধারণ ক্যান্ডেল (Normal)"
        pattern_type = "NEUTRAL"
        
        if curr_body <= 0.1 * curr_range:
            pattern_text = "ডোজি (Doji) - কনফিউজড"
            pattern_type = "NEUTRAL"
        elif curr_lower_shadow >= 2 * curr_body and curr_upper_shadow <= 0.2 * curr_body:
            pattern_text = "হ্যামার (Hammer) - বায়ার প্রেসার"
            pattern_type = "BULLISH"
        elif curr_upper_shadow >= 2 * curr_body and curr_lower_shadow <= 0.2 * curr_body:
            pattern_text = "শুটিং স্টার (Shooting Star) - সেলার প্রেসার"
            pattern_type = "BEARISH"
        elif prev_C < prev_O and curr_C > curr_O and curr_C >= prev_O and curr_O <= prev_C and curr_body > prev_body:
            pattern_text = "বুলিশ এনগাল্ফিং (Strong UP)"
            pattern_type = "BULLISH"
        elif prev_C > prev_O and curr_C < curr_O and curr_C <= prev_O and curr_O >= prev_C and curr_body > prev_body:
            pattern_text = "বেয়ারিশ এনগাল্ফিং (Strong DOWN)"
            pattern_type = "BEARISH"
        
        # 🚦 Signals
        signal_text = "WAITING..."
        css_class = "wait-glow"
        color_code = "#848E9C"
        is_signal_active = False
        
        if trend_50 == "BULLISH" and ema_bullish and macd_bullish and rsi < 65:
            if is_volume_high:
                if pattern_type == "BULLISH":
                    signal_text = "🚀 SUPER BUY" 
                else:
                    signal_text = "🟢 BUY SETUP"
                css_class = "buy-glow"
                color_code = "#00FF00"
                is_signal_active = True
            else:
                signal_text = "LOW VOL"
                
        elif trend_50 == "BEARISH" and not ema_bullish and not macd_bullish and rsi > 35:
            if is_volume_high:
                if pattern_type == "BEARISH":
                    signal_text = "🧨 SUPER SELL" 
                else:
                    signal_text = "🔴 SELL SETUP"
                css_class = "sell-glow"
                color_code = "#FF0000"
                is_signal_active = True
            else:
                signal_text = "LOW VOL"
                
        return {
            'price': curr_price, 'signal': signal_text, 'css': css_class, 'color': color_code,
            'df': df, 'sup': local_support, 'res': local_resistance, 'trend': trend_50, 'rsi': rsi,
            'is_signal_active': is_signal_active, 'ema_bullish': ema_bullish, 
            'is_volume_high': is_volume_high, 'pattern': pattern_text
        }
    except Exception as e:
        return None

btc_radar = fetch_coin_radar("BTC/USDT")
eth_radar = fetch_coin_radar("ETH/USDT")
sol_radar = fetch_coin_radar("SOL/USDT")
doge_radar = fetch_coin_radar("DOGE/USDT")

radars = {"BTC": btc_radar, "ETH": eth_radar, "SOL": sol_radar, "DOGE": doge_radar}
play_alarm_sound = False

for coin_symbol, data in radars.items():
    if data and data['is_signal_active']:
        st.toast(f"🔥 {coin_symbol} SIGNAL DETECTED: {data['signal']}!", icon="🔔")
        play_alarm_sound = True

if play_alarm_sound:
    st.markdown("""
        <audio autoplay loop>
            <source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg">
        </audio>
    """, unsafe_allow_html=True)

def get_button_label(emoji, name, radar, decimals=2):
    if not radar: return f"{emoji} {name}\nError"
    price_str = f"${radar['price']:,.{decimals}f}"
    if radar['is_signal_active']:
        return f"{emoji} {name}\n{price_str}\n🔥 {radar['signal']}"
    else:
        return f"{emoji} {name}\n{price_str}"

m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    if st.button(get_button_label("👑", "BTC/USDT", btc_radar)): st.session_state.active_coin = "BTC/USDT"
with m_col2:
    if st.button(get_button_label("💠", "ETH/USDT", eth_radar)): st.session_state.active_coin = "ETH/USDT"
with m_col3:
    if st.button(get_button_label("🚀", "SOL/USDT", sol_radar)): st.session_state.active_coin = "SOL/USDT"
with m_col4:
    if st.button(get_button_label("🐕", "DOGE/USDT", doge_radar, decimals=4)): st.session_state.active_coin = "DOGE/USDT"

st.markdown("<br>", unsafe_allow_html=True)

active_data = radars[st.session_state.active_coin.split("/")[0]]
active_name = st.session_state.active_coin

if active_data:
    col_panel, col_chart = st.columns([1, 2.5])
    dec = 4 if "DOGE" in active_name else 2
    
    with col_panel:
        # ================= ⚡ Main Info Card =================
        st.markdown(f"""
        <div class="main-detail-card">
            <div style="font-size:14px; color:#848E9C; font-weight:bold; text-transform:uppercase;">SELECTED ASSET</div>
            <div class="coin-name" style="font-size:32px; color:#FCD535; font-weight:900;">{active_name}</div>
            <div class="price-text" style="color:{active_data['color']}; font-size:38px; font-weight:bold; margin-bottom:5px;">${active_data['price']:,.{dec}f}</div>
            <div class="signal-text {active_data['css']}" style="text-align:center; font-size:24px; margin-bottom:20px; background: rgba(0,0,0,0.3); padding:10px; border-radius:8px;">{active_data['signal']}</div>
            <hr>
            <div style="text-align:left; font-size:15px; line-height:2.2; color:#848E9C;">
                <b>🕯️ ক্যান্ডেল স্ক্যান:</b> <span style="color:#FCD535; float:right; font-weight:bold;">{active_data['pattern']}</span><br>
                <b>🛡️ 50 EMA Trend:</b> <span style="color:#EAECEF; float:right;">{active_data['trend']}</span><br>
                <hr style="margin:10px 0;">
                <b style="color:#00E676;">🎯 TARGET (TP):</b> <span style="color:#00E676; float:right; font-weight:bold; font-size:18px;">${active_data['res']:,.{dec}f}</span><br>
                <b style="color:#FF1744;">🛑 STOP LOSS:</b> <span style="color:#FF1744; float:right; font-weight:bold; font-size:18px;">${active_data['sup']:,.{dec}f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ================= 💰 Risk Manager Native UI =================
        st.markdown("""
            <div style="margin-top: 15px; padding: 10px; background-color: #1E2329; border-left: 4px solid #00BFFF; border-radius: 8px;">
                <h4 style="margin:0; color:#00BFFF;">💰 মানি ম্যানেজমেন্ট</h4>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Streamlit Native Inputs with Session Keys
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            st.number_input("মোট ফান্ড ($)", min_value=1.0, step=5.0, key="user_capital")
        with r_col2:
            st.slider("রিস্ক (%)", min_value=0.5, max_value=10.0, step=0.5, key="user_risk")
            
        user_cap = st.session_state.user_capital
        user_risk = st.session_state.user_risk
        
        # Risk Math Logic
        entry_price = active_data['price']
        sl_price = active_data['sup'] if "BUY" in active_data['signal'] else active_data['res']
        
        risk_amount_usd = user_cap * (user_risk / 100.0)
        position_size_usd = 0
        
        if active_data['is_signal_active'] and entry_price != sl_price:
            sl_distance_pct = abs(entry_price - sl_price) / entry_price
            if sl_distance_pct > 0:
                position_size_usd = risk_amount_usd / sl_distance_pct
        
        # Display Math Result
        if active_data['is_signal_active']:
            st.markdown(f"""
                <div style="background-color:rgba(0,0,0,0.5); padding:15px; border-radius:8px; margin-top:10px; border: 1px solid #2B3139;">
                    <div style="color:#848E9C; font-size:13px;">সেফ ট্রেডের জন্য এই সিগন্যালে আপনার লাগানো উচিত:</div>
                    <div style="color:#FCD535; font-size:28px; font-weight:bold; margin: 5px 0;">${position_size_usd:,.2f}</div>
                    <div style="color:#FF1744; font-size:12px;">(স্টপ লস হিট করলে আপনার মাত্র ${risk_amount_usd:,.2f} লস হবে)</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="background-color:rgba(0,0,0,0.5); padding:15px; border-radius:8px; margin-top:10px; border: 1px solid #2B3139;">
                    <div style="color:#848E9C; font-size:13px; text-align:center;">সিগন্যাল এলে এখানে অটোমেটিক সাইজ ক্যালকুলেট হবে।</div>
                </div>
            """, unsafe_allow_html=True)
        
    with col_chart:
        fig = go.Figure(data=[go.Candlestick(x=active_data['df'].index, open=active_data['df']['open'], high=active_data['df']['high'], low=active_data['df']['low'], close=active_data['df']['close'], name='Price')])
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_9'], name='EMA 9', line=dict(color='#00BFFF', width=2)))
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_20'], name='EMA 20', line=dict(color='#FF8C00', width=2)))
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_50'], name='EMA 50', line=dict(color='#FCD535', width=3, dash='dot')))
        fig.add_hline(y=active_data['sup'], line_dash="dash", line_color="#00ff00", opacity=0.5)
        fig.add_hline(y=active_data['res'], line_dash="dash", line_color="#ff0000", opacity=0.5)
        
        fig.update_layout(
            template="plotly_dark", 
            height=500, 
            margin=dict(l=10, r=10, t=10, b=10), 
            xaxis_rangeslider_visible=True, 
            xaxis_rangeslider_thickness=0.1, 
            yaxis=dict(side='right', fixedrange=False), 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='#848E9C'),
            dragmode='pan', 
            hovermode=False 
        )
        fig.update_xaxes(fixedrange=False)
        st.plotly_chart(
            fig, 
            use_container_width=True, 
            config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': 'reset'}
        )

    st.markdown("---")

    # ================= 📖 ক্যান্ডেল আপডেট সহ বাংলা রিপোর্ট =================
    with st.expander(f"🔍 এখানে টিপুন: {active_name} এর সহজ বাংলায় এনালাইসিস রিপোর্ট"):
        st.markdown(f"### 🧠 বটের লাইভ মার্কেট রিডিং (Candle + AI)")
        smc_analysis = []
        smc_analysis.append(f"**১. ক্যান্ডেলস্টিক স্ক্যান:** চার্টের শেষ ক্যান্ডেলটিতে **{active_data['pattern']}**।")
        smc_analysis.append(f"**২. সেফটি শিল্ড (50 EMA):** {active_data['trend']}।")
        cross_status = "BULLISH 🟢 (9 EMA ওপরে)" if active_data['ema_bullish'] else "BEARISH 🔴 (9 EMA নিচে)"
        smc_analysis.append(f"**৩. অ্যাকশন লাইন (9/20):** {cross_status}।")
        rsi_val = active_data['rsi']
        rsi_status = "OVERSOLD 🟢 (দাম সস্তা)" if rsi_val < 45 else "OVERBOUGHT 🔴 (দাম চড়া)" if rsi_val > 60 else "NEUTRAL ⚪ (মাঝামাঝি)"
        smc_analysis.append(f"**৪. RSI পজিশন:** {rsi_val:.1f} ({rsi_status})।")
        vol_status = "🟢 হাই ভলিউম (বড় ট্রেডাররা আছে)" if active_data['is_volume_high'] else "🔴 লো ভলিউম (মার্কেট আটকে আছে)"
        smc_analysis.append(f"**৫. ভলিউম:** {vol_status}।")
        
        st.info(f"**📊 লাইভ ডাটা:** {' '.join(smc_analysis)}")

        if "SUPER BUY" in active_data['signal'] or "BUY" in active_data['signal']:
            st.success(f"**🟢 বটের নির্দেশ:** কেনার (BUY) জন্য সব লজিক মিলে গেছে। টার্গেট: ${active_data['res']:,.{dec}f}, স্টপ লস: ${active_data['sup']:,.{dec}f}। **(আপনার ফান্ড অনুযায়ী এই ট্রেডে ${position_size_usd:,.2f} এর বেশি এন্ট্রি নেবেন না)**")
        elif "SUPER SELL" in active_data['signal'] or "SELL" in active_data['signal']:
            st.error(f"**🔴 বটের নির্দেশ:** বিক্রির (SELL) জন্য সব লজিক মিলে গেছে। টার্গেট: ${active_data['sup']:,.{dec}f}, স্টপ লস: ${active_data['res']:,.{dec}f}। **(আপনার ফান্ড অনুযায়ী এই ট্রেডে ${position_size_usd:,.2f} এর বেশি এন্ট্রি নেবেন না)**")
        elif "LOW VOL" in active_data['signal']:
            st.warning("⚠️ **বটের নির্দেশ:** প্রাইস ঠিক জায়গায় আছে, কিন্তু বড় ট্রেডারদের টাকা এখনো ঢোকেনি (Volume কম)। তাই ফেক ব্রেকআউট এড়াতে চুপচাপ বসে থাকুন।")
        else:
            st.write("⚪ **বটের নির্দেশ:** নো-ট্রেড জোন। এখনো সব ইন্ডিকেটর একসাথে সিগন্যাল দেয়নি। সঠিক সুযোগের জন্য অপেক্ষা করুন।")

if auto_refresh:
    time.sleep(15)
    st.rerun()
