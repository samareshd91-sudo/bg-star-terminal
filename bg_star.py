import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 
import numpy as np

# ================= 👑 1. PAGE CONFIGURATION =================
st.set_page_config(page_title="TRADE MENTOR: PRO SCALPER", layout="wide", initial_sidebar_state="collapsed")

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "5m" 

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
    .global-alert-artistic-buy { background: linear-gradient(90deg, rgba(0,191,255,0.1) 0%, rgba(24,26,32,1) 100%); border-left: 5px solid #00BFFF; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-right: 1px solid #2B3139; border-top: 1px solid #2B3139; border-bottom: 1px solid #2B3139;}
    .global-alert-artistic-sell { background: linear-gradient(90deg, rgba(255,0,255,0.1) 0%, rgba(24,26,32,1) 100%); border-left: 5px solid #FF00FF; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-right: 1px solid #2B3139; border-top: 1px solid #2B3139; border-bottom: 1px solid #2B3139;}
    .global-alert-normal { background: #181A20; border: 1px dashed #2B3139; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px; color: #848E9C;}
    
    .metric-card { background-color: #1E2329; border-radius: 8px; padding: 15px; text-align: center; height: 100%; border-bottom: 3px solid #2B3139; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    .metric-title { font-size: 13px; color: #848E9C; font-weight: bold; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;}
    .metric-value { font-size: 17px; font-weight: bold; margin-bottom: 5px;}
    .metric-explanation { font-size: 12px; color: #B7BDC6; line-height: 1.4; }
    
    .reason-box { background: #14151A; border-left: 4px solid #FCD535; padding: 15px; border-radius: 6px; margin-bottom: 10px; font-size: 14px; color: #EAECEF; line-height: 1.6;}
    .learning-box { background: #0B0E11; border: 1px solid #2B3139; padding: 15px; border-radius: 6px; margin-bottom: 15px;}
    
    div.stButton > button { border-radius: 6px !important; font-weight: bold !important; width: 100% !important; background-color: #1E2329 !important; color: #EAECEF !important; border: 1px solid #FCD535 !important; transition: 0.2s;}
    div.stButton > button:hover { background-color: #FCD535 !important; color: #000000 !important; transform: scale(1.02); }
    </style>
""", unsafe_allow_html=True)

# ================= 🧠 3. STATE MANAGEMENT =================
if 'active_coin' not in st.session_state:
    st.session_state.active_coin = "BTC/USDT"

def change_active_coin(new_coin):
    st.session_state.active_coin = new_coin

# ================= ⚡ 4. CORE ENGINE =================
def fetch_and_analyze(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=500)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        
        # 4.1 Indicators Setup
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        
        # 4.2 Normal Candlestick Pattern Logic
        df['body'] = abs(df['open'] - df['close'])
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_green'] = df['close'] > df['open']
        df['is_red'] = df['close'] < df['open']
        
        c2 = df.iloc[-2]
        c3 = df.iloc[-3]
        c4 = df.iloc[-4]
        
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

        # 4.2.1 ARTISTIC REVERSAL LOGIC
        df['is_peak'] = (df['high'].shift(2) > df['high'].shift(1)) & (df['high'].shift(2) > df['high']) & \
                        (df['high'].shift(2) > df['high'].shift(3)) & (df['high'].shift(2) > df['high'].shift(4))
        
        df['is_valley'] = (df['low'].shift(2) < df['low'].shift(1)) & (df['low'].shift(2) < df['low']) & \
                          (df['low'].shift(2) < df['low'].shift(3)) & (df['low'].shift(2) < df['low'].shift(4))
                          
        df['peak_price'] = np.where(df['is_peak'], df['high'].shift(2), np.nan)
        df['valley_price'] = np.where(df['is_valley'], df['low'].shift(2), np.nan)
        
        recent_peaks = df['peak_price'].dropna().values
        recent_valleys = df['valley_price'].dropna().values

        is_double_top, is_double_bottom, is_head_shoulders, is_inv_head_shoulders = False, False, False, False
        tol = 0.003

        if len(recent_peaks) >= 2:
            if abs(recent_peaks[-1] - recent_peaks[-2]) / recent_peaks[-2] < tol:
                is_double_top = True
        
        if len(recent_peaks) >= 3:
            if recent_peaks[-2] > recent_peaks[-1] and recent_peaks[-2] > recent_peaks[-3]:
                is_head_shoulders = True
                
        if len(recent_valleys) >= 2:
            if abs(recent_valleys[-1] - recent_valleys[-2]) / recent_valleys[-2] < tol:
                is_double_bottom = True
                
        if len(recent_valleys) >= 3:
             if recent_valleys[-2] < recent_valleys[-1] and recent_valleys[-2] < recent_valleys[-3]:
                 is_inv_head_shoulders = True

        artistic_buy_pattern = is_double_bottom or is_inv_head_shoulders
        artistic_sell_pattern = is_double_top or is_head_shoulders

        p_name = "প্যাটার্ন নেই ➖"
        p_desc = "বিশেষ কোনো রিভার্সাল বা স্ট্রং প্যাটার্ন নেই।"
        p_color = "#848E9C"
        
        if is_double_bottom: p_name, p_color, p_desc = "ডাবল বটম ✌️", "#00BFFF", "চার্টে ডাবল বটম (W) প্যাটার্ন।"
        elif is_inv_head_shoulders: p_name, p_color, p_desc = "ইনভার্স হেড এন্ড শোল্ডার 👤", "#00BFFF", "ইনভার্স হেড এন্ড শোল্ডার।"
        elif is_double_top: p_name, p_color, p_desc = "ডাবল টপ ⛰️", "#FF00FF", "চার্টে ডাবল টপ (M) প্যাটার্ন।"
        elif is_head_shoulders: p_name, p_color, p_desc = "হেড এন্ড শোল্ডার 👤", "#FF00FF", "হেড এন্ড শোল্ডার।"
        elif is_morning_star: p_name, p_color, p_desc = "মর্নিং স্টার 🌅", "#00FF00", "স্ট্রং বুলিশ রিভার্সাল।"
        elif is_evening_star: p_name, p_color, p_desc = "ইভনিং স্টার 🌃", "#FF1744", "স্ট্রং বিয়ারিশ রিভার্সাল।"
        elif is_bullish_engulfing: p_name, p_color, p_desc = "বুলিশ এনগালফিং 📈", "#00FF00", "বায়াররা সেলারদের গিলেছে।"
        elif is_bearish_engulfing: p_name, p_color, p_desc = "বিয়ারিশ এনগালফিং 📉", "#FF1744", "সেলাররা বায়ারদের গিলেছে।"
        elif is_hammer: p_name, p_color, p_desc = "হ্যামার 🔨", "#00FF00", "নিচে নামার পর কড়া রিজেকশন।"
        elif is_shooting_star: p_name, p_color, p_desc = "শুটিং স্টার 🌠", "#FF1744", "উপরে ওঠার পর কড়া রিজেকশন।"

        # 4.3 LIVE DATA EXTRACTION
        curr_price = df['close'].iloc[-1]
        curr_open = df['open'].iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        
        curr_ema5 = df['ema_5'].iloc[-1]
        curr_ema13 = df['ema_13'].iloc[-1]
        curr_ema50 = df['ema_50'].iloc[-1]
        
        is_green_candle = curr_price > curr_open 
        is_red_candle = curr_price < curr_open   
        
        is_high_volume = curr_vol > (vol_sma * 3.0) 
        
        buyer_vol_spike = is_high_volume and is_green_candle
        seller_vol_spike = is_high_volume and is_red_candle

        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]

        trend_up = curr_price > curr_ema50
        momentum_bullish = curr_ema5 > curr_ema13
        
        # 4.6 SIGNAL LOGIC
        signal_type = "NORMAL"
        if artistic_buy_pattern:
            signal_type = "ARTISTIC SIGNAL BUY"
        elif artistic_sell_pattern:
            signal_type = "ARTISTIC SIGNAL SELL"
        elif trend_up and momentum_bullish and (bullish_pattern or buyer_vol_spike) and rsi < 70:
            signal_type = "STRONG BUY"
        elif not trend_up and not momentum_bullish and (bearish_pattern or seller_vol_spike) and rsi > 30:
            signal_type = "STRONG SELL"

        return {
            'df': df, 'price': curr_price, 'signal': signal_type, 
            'rsi': rsi, 'curr_vol': curr_vol, 'vol_sma': vol_sma,
            'ema5': curr_ema5, 'ema13': curr_ema13, 'ema50': curr_ema50,
            'p_name': p_name, 'p_desc': p_desc, 'p_color': p_color,
            'buyer_vol_spike': buyer_vol_spike, 'seller_vol_spike': seller_vol_spike, 
            'trend_up': trend_up, 'momentum_bullish': momentum_bullish, 'atr': atr,
            'has_pattern': bullish_pattern or bearish_pattern or artistic_buy_pattern or artistic_sell_pattern,
            'bullish_pattern': bullish_pattern, 'bearish_pattern': bearish_pattern
        }
    except Exception as e: return None

all_data = {}
for coin in SCALPING_COINS:
    res = fetch_and_analyze(coin)
    if res:
        all_data[coin] = res

# ================= 🚨 5. GLOBAL SIGNAL RADAR UI =================
st.markdown("<h3 style='color:#FCD535; margin-bottom:5px;'>🚨 গ্লোবাল লাইভ সিগন্যাল রাডার (5m Timeframe)</h3>", unsafe_allow_html=True)
st.markdown("<p style='color:#848E9C; font-size:12px; margin-top:-5px;'>সঠিক ডেটার জন্য অটোমেটিক প্রতি ১০ সেকেন্ড পর পর রিফ্রেশ হচ্ছে।</p>", unsafe_allow_html=True)

active_signals = 0
for coin, data in all_data.items():
    if data['signal'] in ["STRONG BUY", "STRONG SELL", "ARTISTIC SIGNAL BUY", "ARTISTIC SIGNAL SELL"]:
        active_signals += 1
        is_buy = data['signal'] in ["STRONG BUY", "ARTISTIC SIGNAL BUY"]
        
        if data['signal'] == "ARTISTIC SIGNAL BUY":
            card_class, color_main, icon = "global-alert-artistic-buy", "#00BFFF", "🎨 আর্টিস্টিক সিগন্যাল বাই"
        elif data['signal'] == "ARTISTIC SIGNAL SELL":
            card_class, color_main, icon = "global-alert-artistic-sell", "#FF00FF", "🎨 আর্টিস্টিক সিগন্যাল সেল"
        elif data['signal'] == "STRONG BUY":
            card_class, color_main, icon = "global-alert-buy", "#00FF00", "🚀 STRONG BUY"
        elif data['signal'] == "STRONG SELL":
            card_class, color_main, icon = "global-alert-sell", "#FF1744", "🧨 STRONG SELL"
        
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
            st.button(f"🔍 চার্ট দেখুন", key=f"btn_{coin}", on_click=change_active_coin, args=(coin,))
        st.markdown("</div>", unsafe_allow_html=True)

if active_signals == 0:
    st.markdown("<div class='global-alert-normal'>⏳ বর্তমানে কোনো কয়েনে <b>STRONG</b> বা <b>ARTISTIC</b> সিগন্যাল নেই। অপেক্ষা করুন...</div>", unsafe_allow_html=True)

st.markdown("<hr style='border-color:#2B3139;'>", unsafe_allow_html=True)

# ================= 📚 6. DETAILED DASHBOARD =================
col_a, col_b = st.columns([3, 1])
with col_a:
    st.markdown(f"<h3 style='color:#EAECEF; margin:0;'>🔍 {st.session_state.active_coin} অ্যানালাইসিস</h3>", unsafe_allow_html=True)
with col_b:
    selected = st.selectbox("📊 ম্যানুয়াল সিলেকশন", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))
    if selected != st.session_state.active_coin:
        change_active_coin(selected)
        st.rerun()

if st.session_state.active_coin in all_data:
    data = all_data[st.session_state.active_coin]
    
    # 6.1 METRIC CARDS (RESTORED)
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        t_val = "আপ-ট্রেন্ড (UP)" if data['trend_up'] else "ডাউন-ট্রেন্ড (DOWN)"
        t_color = "#00FF00" if data['trend_up'] else "#FF1744"
        st.markdown(f"<div class='metric-card' style='border-color:{t_color}'><div class='metric-title'>১. მেইন ট্রেন্ড (EMA 50)</div><div class='metric-value' style='color:{t_color}'>{t_val}</div></div>", unsafe_allow_html=True)

    with c2:
        m_val = "বায়াররা শক্তিশালী 🟢" if data['momentum_bullish'] else "সেলাররা শক্তিশালী 🔴"
        m_color = "#00FF00" if data['momentum_bullish'] else "#FF1744"
        st.markdown(f"<div class='metric-card' style='border-color:{m_color}'><div class='metric-title'>২. শর্ট মোমেন্টাম</div><div class='metric-value' style='color:{m_color}'>{m_val}</div></div>", unsafe_allow_html=True)

    with c3:
        if data['buyer_vol_spike']:
            v_val, v_color = "বড় বায়ার অ্যাক্টিভ 🟢", "#00FF00"
        elif data['seller_vol_spike']:
            v_val, v_color = "বড় সেলার অ্যাক্টিভ 🔴", "#FF1744"
        else:
            v_val, v_color = "নরমাল ভলিউম ❄️", "#848E9C"
            
        st.markdown(f"<div class='metric-card' style='border-color:{v_color}'><div class='metric-title'>৩. ট্রেড ভলিউম</div><div class='metric-value' style='color:{v_color}'>{v_val}</div></div>", unsafe_allow_html=True)

    with c4:
        p_val = data['p_name']
        p_color = data['p_color']
        p_desc = f"RSI (14): {data['rsi']:.1f}"
        st.markdown(f"<div class='metric-card' style='border-color:{p_color}'><div class='metric-title'>৪. প্যাটার্ন ও RSI</div><div class='metric-value' style='color:{p_color}'>{p_val}</div><div class='metric-explanation'>{p_desc}</div></div>", unsafe_allow_html=True)

    # 6.2 Logic Breakdown (Mentor Section)
    st.markdown(f"<h4 style='color:#FCD535; margin-top:15px; border-bottom: 1px solid #2B3139; padding-bottom:10px;'>💡 {st.session_state.active_coin} চার্টে এখন কী চলছে? (লজিক ব্রেকডাউন)</h4>", unsafe_allow_html=True)
    
    pattern_text = f"<b>{data['p_name']}</b> প্যাটার্ন" if data['has_pattern'] else "বড় বায়ারদের ভলিউম"
    
    if data['signal'] == "ARTISTIC SIGNAL BUY":
         st.markdown(f"<div class='reason-box' style='border-left-color: #00BFFF;'><b>এই ARTISTIC SIGNAL BUY কেন আসলো?</b><br>চার্টে <b>{data['p_name']}</b> এর মতো একটি শক্তিশালী রিভার্সাল আর্ট-প্যাটার্ন তৈরি হয়েছে। এটি সাধারণ ক্যান্ডেল বা ট্রেন্ডের চেয়ে বেশি নির্ভরযোগ্য।</div>", unsafe_allow_html=True)
    elif data['signal'] == "ARTISTIC SIGNAL SELL":
         st.markdown(f"<div class='reason-box' style='border-left-color: #FF00FF;'><b>এই ARTISTIC SIGNAL SELL কেন আসলো?</b><br>চার্টে <b>{data['p_name']}</b> এর মতো একটি শক্তিশালী রিভার্সাল আর্ট-প্যাটার্ন তৈরি হয়েছে। এটি সাধারণ ক্যান্ডেল বা ট্রেন্ডের চেয়ে বেশি নির্ভরযোগ্য।</div>", unsafe_allow_html=True)
    elif data['signal'] == "STRONG BUY":
        st.markdown(f"<div class='reason-box'><b>এই STRONG BUY সিগন্যালটি কেন আসলো?</b><br>১. প্রাইস EMA 50 এর উপরে (আপ-ট্রেন্ড)।<br>২. EMA 5, EMA 13 কে ক্রস করে উপরে উঠেছে (বুলিশ মোমেন্টাম)।<br>৩. {pattern_text} কনফার্মেশন।<br>৪. RSI 70 এর নিচে আছে।</div>", unsafe_allow_html=True)
    elif data['signal'] == "STRONG SELL":
        st.markdown(f"<div class='reason-box'><b>এই STRONG SELL সিগন্যালটি কেন আসলো?</b><br>১. প্রাইস EMA 50 এর নিচে (ডাউন-ট্রেন্ড)।<br>২. EMA 5, EMA 13 কে ক্রস করে নিচে নেমেছে (বিয়ারিশ মোমেন্টাম)।<br>৩. {pattern_text} কনফার্মেশন।<br>৪. RSI 30 এর উপরে আছে।</div>", unsafe_allow_html=True)
    else:
         st.markdown(f"<div class='reason-box' style='border-left-color: #848E9C;'><b>{st.session_state.active_coin} কয়েনে এখন কেন কোনো সিগন্যাল নেই?</b><br>ট্রেন্ড, মোমেন্টাম, ভলিউম এবং ক্যান্ডেলস্টিক প্যাটার্ন— এই সব কন্ডিশন একসাথে মিলেনি। তাই ভুল ট্রেড এড়ানোর জন্য এখন অপেক্ষা করতে বলা হচ্ছে। নিচে লাইভ ভ্যালুগুলো চেক করুন।</div>", unsafe_allow_html=True)

    # 6.3 LIVE LEARNING & PARAMETER DASHBOARD
    st.markdown(f"<h4 style='color:#00BFFF; margin-top:20px;'>📊 লাইভ প্যারামিটার ও লার্নিং ড্যাশবোর্ড</h4>", unsafe_allow_html=True)
    st.markdown("<p style='color:#848E9C; font-size:13px; margin-top:-5px;'>সঠিক নাম্বারের ভিত্তিতে কন্ডিশনগুলো কীভাবে কাজ করছে, তা নিচে থেকে শিখুন:</p>", unsafe_allow_html=True)
    
    col_l1, col_l2 = st.columns(2)
    
    with col_l1:
        st.markdown("<div class='learning-box'>", unsafe_allow_html=True)
        st.markdown(f"<b style='color:#FCD535;'>📌 বর্তমান টেকনিক্যাল নাম্বার (Live Values)</b><br>", unsafe_allow_html=True)
        st.markdown(f"🔹 <b>বর্তমান প্রাইস:</b> {data['price']:.4f}", unsafe_allow_html=True)
        st.markdown(f"🔹 <b>EMA 50 (ট্রেন্ড লাইন):</b> {data['ema50']:.4f}", unsafe_allow_html=True)
        st.markdown(f"🔹 <b>EMA 5 (ফাস্ট):</b> {data['ema5']:.4f}", unsafe_allow_html=True)
        st.m
