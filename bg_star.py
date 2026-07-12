import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 

# 👑 Page Layout Config
st.set_page_config(page_title="TRADE MENTOR: 1M SCALPER", layout="wide", initial_sidebar_state="collapsed")

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "1m" 

SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

# ================= 🌟 DYNAMIC CSS =================
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #0B0E11 !important; color: #EAECEF !important; }
    ::-webkit-scrollbar { width: 10px !important; }
    ::-webkit-scrollbar-thumb { background: #FCD535 !important; border-radius: 10px; }
    [data-testid="stHeader"], header { display: none !important; }
    .block-container { padding-top: 20px !important; }
    
    .status-banner-normal { background: #181A20; border: 2px dashed #848E9C; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
    .status-banner-buy { background: linear-gradient(90deg, rgba(0,255,0,0.2) 0%, rgba(24,26,32,1) 100%); border: 2px solid #00FF00; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; box-shadow: 0 0 15px rgba(0,255,0,0.3); }
    .status-banner-sell { background: linear-gradient(90deg, rgba(255,23,68,0.2) 0%, rgba(24,26,32,1) 100%); border: 2px solid #FF1744; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; box-shadow: 0 0 15px rgba(255,23,68,0.3); }
    
    .metric-card { background-color: #1E2329; border-radius: 8px; padding: 15px; text-align: center; height: 100%; border-bottom: 3px solid #2B3139;}
    .metric-title { font-size: 13px; color: #848E9C; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }
    .metric-value { font-size: 18px; font-weight: bold; }
    .metric-explanation { font-size: 12px; color: #B7BDC6; margin-top: 8px; line-height: 1.4; }
    
    .reason-box { background: #14151A; border-left: 4px solid #FCD535; padding: 15px; border-radius: 6px; margin-bottom: 10px; font-size: 14px; color: #EAECEF; }
    </style>
""", unsafe_allow_html=True)

if 'active_coin' not in st.session_state:
    st.session_state.active_coin = "BTC/USDT"

# ================= 🎛️ HEADER =================
col_a, col_b = st.columns([3, 1])
with col_a:
    st.markdown("<h2 style='color:#FCD535; margin:0;'>🧠 লাইভ ট্রেডিং মেন্টর ও সিগন্যাল ড্যাশবোর্ড</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#848E9C; font-size:14px;'>মার্কেট এনালাইজ করুন এবং শিখুন কেন সিগন্যাল তৈরি হয়।</p>", unsafe_allow_html=True)
with col_b:
    st.session_state.active_coin = st.selectbox("📊 চার্ট সিলেক্ট করুন", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))

# ================= ⚡ DATA FETCH & LOGIC =================
def fetch_and_analyze(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        
        # Indicators
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean() + 1e-10
        rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        
        # Patterns
        df['body'] = abs(df['open'] - df['close'])
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        
        last_body, last_upper, last_lower = df['body'].iloc[-2], df['upper_shadow'].iloc[-2], df['lower_shadow'].iloc[-2]
        
        is_hammer = (last_lower >= (2 * last_body)) and (last_upper <= last_body) and last_body > 0
        is_shooting_star = (last_upper >= (2 * last_body)) and (last_lower <= last_body) and last_body > 0

        # Current Stats
        curr_price = df['close'].iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        vol_spike = curr_vol > (vol_sma * 1.5)
        
        # ATR for Target/SL
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]

        # Conditions
        trend_up = curr_price > df['ema_50'].iloc[-1]
        momentum_bullish = df['ema_5'].iloc[-1] > df['ema_13'].iloc[-1]
        
        # Signal Generation Logic
        signal_type = "NORMAL"
        if trend_up and momentum_bullish and (is_hammer or vol_spike) and rsi < 70:
            signal_type = "STRONG BUY"
        elif not trend_up and not momentum_bullish and (is_shooting_star or vol_spike) and rsi > 30:
            signal_type = "STRONG SELL"

        return {
            'df': df, 'price': curr_price, 'signal': signal_type, 
            'rsi': rsi, 'vol_ratio': (curr_vol / vol_sma) * 100 if vol_sma > 0 else 0,
            'is_hammer': is_hammer, 'is_shooting_star': is_shooting_star, 'vol_spike': vol_spike,
            'trend_up': trend_up, 'momentum_bullish': momentum_bullish, 'atr': atr
        }
    except Exception as e: return None

data = fetch_and_analyze(st.session_state.active_coin)

if data:
    # ================= 🎯 MAIN SIGNAL BANNER =================
    if data['signal'] == "STRONG BUY":
        tp = data['price'] + (data['atr'] * 2.5)
        sl = data['price'] - (data['atr'] * 1.5)
        st.markdown(f"""
            <div class="status-banner-buy">
                <h1 style="color:#00FF00; margin:0; font-size:40px;">🚀 STRONG BUY SIGNAL!</h1>
                <h3 style="color:#EAECEF; margin-top:5px;">{st.session_state.active_coin} @ {data['price']:.4f}</h3>
                <div style="font-size:18px; margin-top:10px;">
                    <span style="color:#00FF00; margin-right:20px;">🎯 <b>Target (TP):</b> {tp:.4f}</span>
                    <span style="color:#FF1744;">🛑 <b>Stop Loss (SL):</b> {sl:.4f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    elif data['signal'] == "STRONG SELL":
        tp = data['price'] - (data['atr'] * 2.5)
        sl = data['price'] + (data['atr'] * 1.5)
        st.markdown(f"""
            <div class="status-banner-sell">
                <h1 style="color:#FF1744; margin:0; font-size:40px;">🧨 STRONG SELL SIGNAL!</h1>
                <h3 style="color:#EAECEF; margin-top:5px;">{st.session_state.active_coin} @ {data['price']:.4f}</h3>
                <div style="font-size:18px; margin-top:10px;">
                    <span style="color:#00FF00; margin-right:20px;">🎯 <b>Target (TP):</b> {tp:.4f}</span>
                    <span style="color:#FF1744;">🛑 <b>Stop Loss (SL):</b> {sl:.4f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    else:
        st.markdown(f"""
            <div class="status-banner-normal">
                <h2 style="color:#FCD535; margin:0;">⏳ NORMAL MARKET (WAITING)</h2>
                <h4 style="color:#848E9C; margin-top:5px;">{st.session_state.active_coin} @ {data['price']:.4f}</h4>
                <p style="color:#B7BDC6; font-size:14px; margin-top:10px;">মার্কেট এখন সাধারণ মুভমেন্ট করছে। স্ট্রং সিগন্যাল পাওয়ার জন্য পারফেক্ট কন্ডিশন তৈরি হওয়া পর্যন্ত অপেক্ষা করুন।</p>
            </div>
        """, unsafe_allow_html=True)

    # ================= 📚 DETAILED LEARNING DASHBOARD =================
    st.markdown("<h4 style='color:#EAECEF; margin-bottom:15px;'>🔍 লাইভ মার্কেট অ্যানালাইসিস (১ মিনিটের চার্ট)</h4>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    
    # 1. TREND CARD
    with c1:
        t_val = "আপ-ট্রেন্ড (UP)" if data['trend_up'] else "ডাউন-ট্রেন্ড (DOWN)"
        t_color = "#00FF00" if data['trend_up'] else "#FF1744"
        t_desc = "বর্তমান প্রাইস EMA 50 লাইনের উপরে আছে। মানে লং-টার্মে বায়াররা কন্ট্রোলে।" if data['trend_up'] else "বর্তমান প্রাইস EMA 50 লাইনের নিচে আছে। মানে লং-টার্মে সেলাররা কন্ট্রোলে।"
        st.markdown(f"<div class='metric-card' style='border-color:{t_color}'><div class='metric-title'>১. মেইন ট্রেন্ড (EMA 50)</div><div class='metric-value' style='color:{t_color}'>{t_val}</div><div class='metric-explanation'>{t_desc}</div></div>", unsafe_allow_html=True)

    # 2. MOMENTUM CARD
    with c2:
        m_val = "বায়াররা শক্তিশালী" if data['momentum_bullish'] else "সেলাররা শক্তিশালী"
        m_color = "#00FF00" if data['momentum_bullish'] else "#FF1744"
        m_desc = "EMA 5, EMA 13 এর উপরে আছে। শর্ট-টাইমে মার্কেট পাম্প হওয়ার সম্ভাবনা বেশি।" if data['momentum_bullish'] else "EMA 5, EMA 13 এর নিচে আছে। শর্ট-টাইমে মার্কেট ডাম্প হওয়ার সম্ভাবনা বেশি।"
        st.markdown(f"<div class='metric-card' style='border-color:{m_color}'><div class='metric-title'>২. মার্কেট মোমেন্টাম</div><div class='metric-value' style='color:{m_color}'>{m_val}</div><div class='metric-explanation'>{m_desc}</div></div>", unsafe_allow_html=True)

    # 3. VOLUME CARD
    with c3:
        v_val = "বড় ভলিউম স্পাইক 💥" if data['vol_spike'] else "নরমাল ভলিউম ❄️"
        v_color = "#FCD535" if data['vol_spike'] else "#848E9C"
        v_desc = f"অ্যাভারেজের চেয়ে {data['vol_ratio']:.0f}% ভলিউম! বড় ট্রেডাররা মার্কেটে এন্ট্রি নিয়েছে।" if data['vol_spike'] else f"অ্যাভারেজ ভলিউমের মাত্র {data['vol_ratio']:.0f}% চলছে। মার্কেটে এখন বড় কোনো ট্রেডার নেই।"
        st.markdown(f"<div class='metric-card' style='border-color:{v_color}'><div class='metric-title'>৩. ট্রেড ভলিউম</div><div class='metric-value' style='color:{v_color}'>{v_val}</div><div class='metric-explanation'>{v_desc}</div></div>", unsafe_allow_html=True)

    # 4. PATTERN & RSI CARD
    with c4:
        p_val = "হ্যামার 🔨" if data['is_hammer'] else "শুটিং স্টার 🌠" if data['is_shooting_star'] else "প্যাটার্ন নেই ➖"
        p_color = "#FCD535" if data['is_hammer'] or data['is_shooting_star'] else "#848E9C"
        p_desc = f"RSI লেভেল: {data['rsi']:.1f}<br>"
        if data['is_hammer']: p_desc += "মার্কেট নিচে নামার পর রিজেকশন পেয়েছে, এবার উপরে উঠবে।"
        elif data['is_shooting_star']: p_desc += "মার্কেট উপরে ওঠার পর রিজেকশন পেয়েছে, এবার নিচে নামবে।"
        else: p_desc += "আগের ক্যান্ডেলে বিশেষ কোনো রিভার্সাল প্যাটার্ন তৈরি হয়নি।"
        st.markdown(f"<div class='metric-card' style='border-color:{p_color}'><div class='metric-title'>৪. ক্যান্ডেল ও RSI</div><div class='metric-value' style='color:{p_color}'>{p_val}</div><div class='metric-explanation'>{p_desc}</div></div>", unsafe_allow_html=True)

    # ================= 🧠 LOGIC BREAKDOWN (Why Signal?) =================
    st.markdown("<h4 style='color:#FCD535; margin-top:20px; border-bottom: 1px solid #2B3139; padding-bottom:10px;'>💡 কেন ড্যাশবোর্ড এখন এই রেজাল্ট দিচ্ছে? (লজিক ব্রেকডাউন)</h4>", unsafe_allow_html=True)
    
    if data['signal'] == "STRONG BUY":
        st.markdown("""
            <div class='reason-box'>
                <b>এই STRONG BUY সিগন্যালটি কেন আসলো?</b><br>
                ১. প্রাইস EMA 50 এর উপরে আছে, মানে বড় টাইমফ্রেমে মার্কেট <b>আপ-ট্রেন্ডে</b> আছে।<br>
                ২. শর্ট টাইমফ্রেমে বায়াররা অ্যাক্টিভ, কারণ ফাস্ট মুভিং এভারেজ (EMA 5) স্লো মুভিং এভারেজ (EMA 13) কে ক্রস করে উপরে উঠেছে।<br>
                ৩. মার্কেটে বড় ভলিউম বা হ্যামার প্যাটার্ন তৈরি হয়েছে, যা কনফার্ম করে যে নিচে থেকে কড়া বাউন্স এসেছে।<br>
                ৪. RSI 70 এর নিচে আছে, মানে মার্কেট এখনও ওভারবট (Overbought) হয়নি, আরও উপরে যাওয়ার জায়গা আছে।
            </div>
        """, unsafe_allow_html=True)
    elif data['signal'] == "STRONG SELL":
        st.markdown("""
            <div class='reason-box'>
                <b>এই STRONG SELL সিগন্যালটি কেন আসলো?</b><br>
                ১. প্রাইস EMA 50 এর নিচে আছে, মানে বড় টাইমফ্রেমে মার্কেট <b>ডাউন-ট্রেন্ডে</b> আছে।<br>
                ২. শর্ট টাইমফ্রেমে সেলাররা অ্যাক্টিভ, কারণ ফাস্ট মুভিং এভারেজ (EMA 5) স্লো মুভিং এভারেজ (EMA 13) কে ক্রস করে নিচে নেমেছে।<br>
                ৩. মার্কেটে বড় ভলিউম বা শুটিং স্টার প্যাটার্ন তৈরি হয়েছে, যা কনফার্ম করে যে উপর থেকে স্ট্রং রিজেকশন এসেছে।<br>
                ৪. RSI 30 এর উপরে আছে, মানে মার্কেট এখনও পুরোপুরি ওভারসোল্ড (Oversold) হয়নি, আরও নিচে নামার জায়গা আছে।
            </div>
        """, unsafe_allow_html=True)
    else:
         st.markdown("""
            <div class='reason-box' style='border-left-color: #848E9C;'>
                <b>এখন কেন কোনো সিগন্যাল নেই (NORMAL MARKET)?</b><br>
                একটি একুরেট সিগন্যালের জন্য ট্রেন্ড, মোমেন্টাম, ভলিউম এবং ক্যান্ডেলস্টিক প্যাটার্ন— এই চারটির সংমিশ্রণ (Confluence) থাকতে হয়।<br>
                বর্তমানে উপরের ৪টি মেট্রিক্সের মধ্যে সবগুলো শর্ত একসাথে মিলছে না। হয়তো ট্রেন্ড আপে আছে কিন্তু ভলিউম নেই, অথবা মোমেন্টাম ভালো কিন্তু RSI ওভারবট হয়ে গেছে। 
                তাই ভুল ট্রেড এড়ানোর জন্য মার্কেট এখন আপনাকে <b>অপেক্ষা করতে</b> বলছে।
            </div>
        """, unsafe_allow_html=True)

    # ================= 📉 INTERACTIVE CHART =================
    st.markdown("<br>", unsafe_allow_html=True)
    df = data['df']
    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00FF00', decreasing_line_color='#FF1744')])
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_5'], mode='lines', line=dict(color='#00BFFF', width=1.5), name='EMA 5 (Fast)'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_13'], mode='lines', line=dict(color='#FF00FF', width=1.5), name='EMA 13 (Slow)'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_50'], mode='lines', line=dict(color='#FFD700', width=2, dash='dot'), name='EMA 50 (Trend)'))
    fig.update_layout(height=400, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, rangeslider=dict(visible=False)), yaxis=dict(showgrid=True, gridcolor='#2B3139', side='right'))
    st.plotly_chart(fig, use_container_width=True)

# Loop Refresh
time.sleep(3)
st.rerun()
