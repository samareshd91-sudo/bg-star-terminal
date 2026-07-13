import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 

# ================= 👑 1. PAGE CONFIGURATION =================
st.set_page_config(page_title="TRADE MENTOR: 1M SCALPER", layout="wide", initial_sidebar_state="collapsed")

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "1m" 

SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

# ================= 🎨 2. PREMIUM DYNAMIC CSS =================
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #0B0E11 !important; color: #EAECEF !important; }
    ::-webkit-scrollbar { width: 10px !important; }
    ::-webkit-scrollbar-thumb { background: #FCD535 !important; border-radius: 10px; }
    [data-testid="stHeader"], header { display: none !important; }
    .block-container { padding-top: 20px !important; }
    
    .global-alert-buy { background: linear-gradient(90deg, rgba(0,255,0,0.1) 0%, rgba(24,26,32,1) 100%); border-left: 5px solid #00FF00; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-right: 1px solid #2B3139; border-top: 1px solid #2B3139; border-bottom: 1px solid #2B3139;}
    .global-alert-sell { background: linear-gradient(90deg, rgba(255,23,68,0.1) 0%, rgba(24,26,32,1) 100%); border-left: 5px solid #FF1744; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-right: 1px solid #2B3139; border-top: 1px solid #2B3139; border-bottom: 1px solid #2B3139;}
    .global-alert-normal { background: #181A20; border: 1px dashed #2B3139; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px; color: #848E9C;}
    
    .metric-card { background-color: #1E2329; border-radius: 8px; padding: 15px; text-align: center; height: 100%; border-bottom: 3px solid #2B3139; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    .metric-title { font-size: 13px; color: #848E9C; font-weight: bold; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;}
    .metric-value { font-size: 17px; font-weight: bold; margin-bottom: 5px;}
    .metric-explanation { font-size: 12px; color: #B7BDC6; line-height: 1.4; }
    
    .reason-box { background: #14151A; border-left: 4px solid #FCD535; padding: 15px; border-radius: 6px; margin-bottom: 10px; font-size: 14px; color: #EAECEF; line-height: 1.6;}
    
    div.stButton > button { border-radius: 6px !important; font-weight: bold !important; width: 100% !important; background-color: #1E2329 !important; color: #EAECEF !important; border: 1px solid #FCD535 !important; transition: 0.2s;}
    div.stButton > button:hover { background-color: #FCD535 !important; color: #000000 !important; transform: scale(1.02); }
    </style>
""", unsafe_allow_html=True)

# ================= 🧠 3. STATE MANAGEMENT =================
if 'active_coin' not in st.session_state:
    st.session_state.active_coin = "BTC/USDT"

def change_active_coin(new_coin):
    st.session_state.active_coin = new_coin

# ================= ⚡ 4. CORE ENGINE (DATA & 7 PATTERNS) =================
def fetch_and_analyze(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        
        # 4.1 Indicators Setup
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean() + 1e-10
        rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        
        # 4.2 Advanced Candlestick Pattern Logic (7 Patterns)
        df['body'] = abs(df['open'] - df['close'])
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_green'] = df['close'] > df['open']
        df['is_red'] = df['close'] < df['open']
        
        c2 = df.iloc[-2] # Last closed candle
        c3 = df.iloc[-3] # 2nd last closed candle
        c4 = df.iloc[-4] # 3rd last closed candle
        
        is_hammer = (c2['lower_shadow'] >= (2 * c2['body'])) and (c2['upper_shadow'] <= c2['body']) and c2['body'] > 0
        is_shooting_star = (c2['upper_shadow'] >= (2 * c2['body'])) and (c2['lower_shadow'] <= c2['body']) and c2['body'] > 0
        is_doji = c2['body'] <= ((c2['high'] - c2['low']) * 0.1)
        
        is_bullish_engulfing = c3['is_red'] and c2['is_green'] and (c2['close'] >= c3['open']) and (c2['open'] <= c3['close']) and (c2['body'] > c3['body'])
        is_bearish_engulfing = c3['is_green'] and c2['is_red'] and (c2['close'] <= c3['open']) and (c2['open'] >= c3['close']) and (c2['body'] > c3['body'])
        
        is_bullish_marubozu = c2['is_green'] and (c2['upper_shadow'] <= c2['body']*0.05) and (c2['lower_shadow'] <= c2['body']*0.05) and c2['body'] > 0
        is_bearish_marubozu = c2['is_red'] and (c2['upper_shadow'] <= c2['body']*0.05) and (c2['lower_shadow'] <= c2['body']*0.05) and c2['body'] > 0
        
        c4_mid = (c4['open'] + c4['close']) / 2
        is_morning_star = c4['is_red'] and (c3['body'] <= (c3['high'] - c3['low']) * 0.3) and c2['is_green'] and (c2['close'] >= c4_mid)
        is_evening_star = c4['is_green'] and (c3['body'] <= (c3['high'] - c3['low']) * 0.3) and c2['is_red'] and (c2['close'] <= c4_mid)

        bullish_pattern = is_hammer or is_bullish_engulfing or is_bullish_marubozu or is_morning_star
        bearish_pattern = is_shooting_star or is_bearish_engulfing or is_bearish_marubozu or is_evening_star

        p_name = "প্যাটার্ন নেই ➖"
        p_desc = "বিশেষ কোনো রিভার্সাল বা স্ট্রং প্যাটার্ন নেই।"
        p_color = "#848E9C"
        
        if is_morning_star: p_name, p_color, p_desc = "মর্নিং স্টার 🌅", "#00FF00", "৩ ক্যান্ডেল মিলে স্ট্রং বুলিশ রিভার্সাল। মার্কেট পাম্প হতে পারে।"
        elif is_evening_star: p_name, p_color, p_desc = "ইভনিং স্টার 🌃", "#FF1744", "৩ ক্যান্ডেল মিলে স্ট্রং বিয়ারিশ রিভার্সাল। মার্কেট ডাম্প হতে পারে।"
        elif is_bullish_engulfing: p_name, p_color, p_desc = "বুলিশ এনগালফিং 📈", "#00FF00", "বায়াররা সেলারদের গিলে ফেলেছে। শক্তিশালী আপট্রেন্ডের সম্ভাবনা।"
        elif is_bearish_engulfing: p_name, p_color, p_desc = "বিয়ারিশ এনগালফিং 📉", "#FF1744", "সেলাররা বায়ারদের গিলে ফেলেছে। শক্তিশালী ডাউনট্রেন্ডের সম্ভাবনা।"
        elif is_bullish_marubozu: p_name, p_color, p_desc = "বুলিশ ম্যারুবোজু 🟩", "#00FF00", "বায়ারদের চরম এগ্রেসিভ মুড। কোনো শ্যাডো নেই।"
        elif is_bearish_marubozu: p_name, p_color, p_desc = "বিয়ারিশ ম্যারুবোজু 🟥", "#FF1744", "সেলারদের চরম এগ্রেসিভ মুড। কোনো শ্যাডো নেই।"
        elif is_hammer: p_name, p_color, p_desc = "হ্যামার 🔨", "#00FF00", "মার্কেট নিচে নামার পর কড়া রিজেকশন পেয়েছে।"
        elif is_shooting_star: p_name, p_color, p_desc = "শুটিং স্টার 🌠", "#FF1744", "মার্কেট উপরে ওঠার পর কড়া রিজেকশন পেয়েছে।"
        elif is_doji: p_name, p_color, p_desc = "ডোজি (Doji) ⚖️", "#FCD535", "বায়ার ও সেলারদের শক্তি সমান। মার্কেট সিদ্ধান্তহীনতায় আছে।"

        # 4.3 STRICT Volume & Candle Direction (বায়ার নাকি সেলার?)
        curr_price = df['close'].iloc[-1]
        curr_open = df['open'].iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        
        is_green_candle = curr_price > curr_open 
        is_red_candle = curr_price < curr_open   
        is_high_volume = curr_vol > (vol_sma * 1.5)
        
        buyer_vol_spike = is_high_volume and is_green_candle
        seller_vol_spike = is_high_volume and is_red_candle

        # 4.4 ATR for Stop Loss / Take Profit
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]

        # 4.5 Conditions Check
        trend_up = curr_price > df['ema_50'].iloc[-1]
        momentum_bullish = df['ema_5'].iloc[-1] > df['ema_13'].iloc[-1]
        
        # 4.6 Strict Signal Logic (বায়ার/সেলার ডিরেকশন + ৭টি প্যাটার্ন অনুযায়ী)
        signal_type = "NORMAL"
        if trend_up and momentum_bullish and (bullish_pattern or buyer_vol_spike) and rsi < 70:
            signal_type = "STRONG BUY"
        elif not trend_up and not momentum_bullish and (bearish_pattern or seller_vol_spike) and rsi > 30:
            signal_type = "STRONG SELL"

        return {
            'df': df, 'price': curr_price, 'signal': signal_type, 
            'rsi': rsi, 'vol_ratio': (curr_vol / vol_sma) * 100 if vol_sma > 0 else 0,
            'p_name': p_name, 'p_desc': p_desc, 'p_color': p_color,
            'buyer_vol_spike': buyer_vol_spike, 'seller_vol_spike': seller_vol_spike, 
            'trend_up': trend_up, 'momentum_bullish': momentum_bullish, 'atr': atr,
            'has_pattern': bullish_pattern or bearish_pattern
        }
    except Exception as e: return None

# Background Scan for all coins
all_data = {}
for coin in SCALPING_COINS:
    res = fetch_and_analyze(coin)
    if res:
        all_data[coin] = res

# ================= 🚨 5. GLOBAL SIGNAL RADAR UI =================
st.markdown("<h3 style='color:#FCD535; margin-bottom:5px;'>🚨 গ্লোবাল লাইভ সিগন্যাল রাডার</h3>", unsafe_allow_html=True)
st.markdown("<p style='color:#848E9C; font-size:12px; margin-top:-5px;'>মার্কেটের সবগুলো কয়েন স্ক্যান হচ্ছে। সিগন্যাল আসলেই নিচে শো করবে।</p>", unsafe_allow_html=True)

active_signals = 0
for coin, data in all_data.items():
    if data['signal'] == "STRONG BUY" or data['signal'] == "STRONG SELL":
        active_signals += 1
        is_buy = data['signal'] == "STRONG BUY"
        
        card_class = "global-alert-buy" if is_buy else "global-alert-sell"
        color_main = "#00FF00" if is_buy else "#FF1744"
        icon = "🚀 STRONG BUY" if is_buy else "🧨 STRONG SELL"
        
        tp = data['price'] + (data['atr'] * 2.5) if is_buy else data['price'] - (data['atr'] * 2.5)
        sl = data['price'] - (data['atr'] * 1.5) if is_buy else data['price'] + (data['atr'] * 1.5)
        
        st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.markdown(f"<h3 style='color:{color_main}; margin:0;'>{icon}: {coin}</h3><div style='font-size:13px; color:#EAECEF; margin-top:3px;'>📍 এন্ট্রি প্রাইস: {data['price']:.4f}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='color:#00FF00; font-weight:bold; font-size:15px; margin-top:5px;'>🎯 টার্গেট (TP): {tp:.4f}</div><div style='color:#FF1744; font-weight:bold; font-size:15px;'>🛑 স্টপ লস (SL): {sl:.4f}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            st.button(f"🔍 অ্যানালাইসিস দেখুন", key=f"btn_{coin}", on_click=change_active_coin, args=(coin,))
            
        st.markdown("</div>", unsafe_allow_html=True)

if active_signals == 0:
    st.markdown("""
        <div class="global-alert-normal">
            ⏳ বর্তমানে কোনো কয়েনে স্ট্রং সিগন্যাল নেই। <b>BTC, ETH, SOL, BNB</b> ব্যাকগ্রাউন্ডে স্ক্যান হচ্ছে... সিগন্যাল আসলেই এখানে শো করবে।
        </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border-color:#2B3139;'>", unsafe_allow_html=True)

# ================= 📚 6. DETAILED EDUCATIONAL DASHBOARD =================
col_a, col_b = st.columns([3, 1])
with col_a:
    st.markdown(f"<h3 style='color:#EAECEF; margin:0;'>🔍 {st.session_state.active_coin} চার্ট অ্যানালাইসিস</h3>", unsafe_allow_html=True)
with col_b:
    selected = st.selectbox("📊 ম্যানুয়াল চার্ট সিলেকশন", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))
    if selected != st.session_state.active_coin:
        change_active_coin(selected)
        st.rerun()

if st.session_state.active_coin in all_data:
    data = all_data[st.session_state.active_coin]
    
    # --- 6.1 Metric Cards ---
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        t_val = "আপ-ট্রেন্ড (UP)" if data['trend_up'] else "ডাউন-ট্রেন্ড (DOWN)"
        t_color = "#00FF00" if data['trend_up'] else "#FF1744"
        t_desc = "প্রাইস EMA 50 এর উপরে। লং-টার্মে বায়াররা কন্ট্রোলে।" if data['trend_up'] else "প্রাইস EMA 50 এর নিচে। লং-টার্মে সেলাররা কন্ট্রোলে।"
        st.markdown(f"<div class='metric-card' style='border-color:{t_color}'><div class='metric-title'>১. মেইন ট্রেন্ড (EMA 50)</div><div class='metric-value' style='color:{t_color}'>{t_val}</div><div class='metric-explanation'>{t_desc}</div></div>", unsafe_allow_html=True)

    with c2:
        m_val = "বায়াররা শক্তিশালী 🟢" if data['momentum_bullish'] else "সেলাররা শক্তিশালী 🔴"
        m_color = "#00FF00" if data['momentum_bullish'] else "#FF1744"
        m_desc = "EMA 5, EMA 13 এর উপরে। মার্কেট পাম্প হতে পারে।" if data['momentum_bullish'] else "EMA 5, EMA 13 এর নিচে। মার্কেট ডাম্প হতে পারে।"
        st.markdown(f"<div class='metric-card' style='border-color:{m_color}'><div class='metric-title'>২. শর্ট মোমেন্টাম</div><div class='metric-value' style='color:{m_color}'>{m_val}</div><div class='metric-explanation'>{m_desc}</div></div>", unsafe_allow_html=True)

    with c3:
        if data['buyer_vol_spike']:
            v_val, v_color, v_desc = "হেভি বায়ার ভলিউম 🟢", "#00FF00", "মার্কেটে বড় বায়ার (তিমি) ঢুকেছে, প্রাইস উপরে যাবে।"
        elif data['seller_vol_spike']:
            v_val, v_color, v_desc = "হেভি সেলার ভলিউম 🔴", "#FF1744", "মার্কেটে বড় সেলার (তিমি) ঢুকেছে, প্রাইস নিচে নামবে।"
        else:
            v_val, v_color, v_desc = "নরমাল ভলিউম ❄️", "#848E9C", "এখন সাধারণ ভলিউম চলছে। বড় কোনো মুভমেন্ট নেই।"
            
        st.markdown(f"<div class='metric-card' style='border-color:{v_color}'><div class='metric-title'>৩. ট্রেড ভলিউম</div><div class='metric-value' style='color:{v_color}'>{v_val}</div><div class='metric-explanation'>{v_desc}</div></div>", unsafe_allow_html=True)

    with c4:
        p_val = data['p_name']
        p_color = data['p_color']
        p_desc = f"RSI লেভেল: {data['rsi']:.1f}<br>{data['p_desc']}"
        st.markdown(f"<div class='metric-card' style='border-color:{p_color}'><div class='metric-title'>৪. ক্যান্ডেল ও RSI</div><div class='metric-value' style='color:{p_color}'>{p_val}</div><div class='metric-explanation'>{p_desc}</div></div>", unsafe_allow_html=True)

    # --- 6.2 Logic Breakdown (Mentor Section) ---
    st.markdown(f"<h4 style='color:#FCD535; margin-top:25px; border-bottom: 1px solid #2B3139; padding-bottom:10px;'>💡 {st.session_state.active_coin} চার্টে এখন কী চলছে? (লজিক ব্রেকডাউন)</h4>", unsafe_allow_html=True)
    
    # ডায়নামিক প্যাটার্ন টেক্সট
    pattern_text = f"<b>{data['p_name']}</b> প্যাটার্ন" if data['has_pattern'] else "বড় বায়ারদের ভলিউম"
    pattern_text_sell = f"<b>{data['p_name']}</b> প্যাটার্ন" if data['has_pattern'] else "বড় সেলারদের ভলিউম"

    if data['signal'] == "STRONG BUY":
        st.markdown(f"""
            <div class='reason-box'>
                <b>এই STRONG BUY সিগন্যালটি কেন আসলো?</b><br>
                ১. প্রাইস EMA 50 এর উপরে আছে, মানে বড় টাইমফ্রেমে মার্কেট <b>আপ-ট্রেন্ডে</b> আছে।<br>
                ২. শর্ট টাইমফ্রেমে বায়াররা অ্যাক্টিভ, কারণ ফাস্ট মুভিং এভারেজ (EMA 5) স্লো মুভিং এভারেজ (EMA 13) কে ক্রস করে উপরে উঠেছে।<br>
                ৩. মার্কেটে {pattern_text} তৈরি হয়েছে, যা প্রাইস উপরে যাওয়ার বড় কনফার্মেশন।<br>
                ৪. RSI 70 এর নিচে আছে, মানে মার্কেট এখনও ওভারবট হয়নি, আরও উপরে যাওয়ার জায়গা আছে।
            </div>
        """, unsafe_allow_html=True)
    elif data['signal'] == "STRONG SELL":
        st.markdown(f"""
            <div class='reason-box'>
                <b>এই STRONG SELL সিগন্যালটি কেন আসলো?</b><br>
                ১. প্রাইস EMA 50 এর নিচে আছে, মানে বড় টাইমফ্রেমে মার্কেট <b>ডাউন-ট্রেন্ডে</b> আছে।<br>
                ২. শর্ট টাইমফ্রেমে সেলাররা অ্যাক্টিভ, কারণ ফাস্ট মুভিং এভারেজ (EMA 5) স্লো মুভিং এভারেজ (EMA 13) কে ক্রস করে নিচে নেমেছে।<br>
                ৩. মার্কেটে {pattern_text_sell} তৈরি হয়েছে, যা প্রাইস নিচে নামার বড় কনফার্মেশন।<br>
                ৪. RSI 30 এর উপরে আছে, মানে মার্কেট এখনও পুরোপুরি ওভারসোল্ড হয়নি, আরও নিচে নামার জায়গা আছে।
            </div>
        """, unsafe_allow_html=True)
    else:
         st.markdown(f"""
            <div class='reason-box' style='border-left-color: #848E9C;'>
                <b>{st.session_state.active_coin} কয়েনে এখন কেন কোনো সিগন্যাল নেই?</b><br>
                একটি একুরেট সিগন্যালের জন্য ট্রেন্ড, মোমেন্টাম, বায়ার/সেলার ভলিউম এবং ক্যান্ডেলস্টিক প্যাটার্ন— এই চারটির সংমিশ্রণ থাকতে হয়।<br>
                বর্তমানে হয়তো ট্রেন্ড আপে আছে কিন্তু <b>ভলিউম নেই</b>, অথবা মোমেন্টাম ভালো কিন্তু <b>ক্যান্ডেল প্যাটার্ন মিলেনি</b>। 
                তাই ভুল ট্রেড (Loss) এড়ানোর জন্য এই চার্টে এখন আপনাকে <b>অপেক্ষা করতে</b> বলা হচ্ছে।
            </div>
        """, unsafe_allow_html=True)

    # --- 6.3 Interactive Chart ---
    st.markdown("<br>", unsafe_allow_html=True)
    df = data['df']
    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00FF00', decreasing_line_color='#FF1744')])
    
    # Adding EMAs to chart
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_5'], mode='lines', line=dict(color='#00BFFF', width=1.5), name='EMA 5 (Fast)'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_13'], mode='lines', line=dict(color='#FF00FF', width=1.5), name='EMA 13 (Slow)'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_50'], mode='lines', line=dict(color='#FFD700', width=2, dash='dot'), name='EMA 50 (Trend)'))
    
    # Chart Styling
    fig.update_layout(height=450, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, rangeslider=dict(visible=False)), yaxis=dict(showgrid=True, gridcolor='#2B3139', side='right'))
    st.plotly_chart(fig, use_container_width=True)

# ================= 🔄 7. AUTO REFRESH LOOP =================
time.sleep(3)
st.rerun()
        
