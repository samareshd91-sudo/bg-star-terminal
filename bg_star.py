import streamlit as st
import ccxt
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

# ================= 👑 1. PAGE CONFIGURATION =================
st.set_page_config(page_title="TRADE MENTOR: PRO SCALPER MASTER", layout="wide", initial_sidebar_state="collapsed")

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
    
    .metric-card { background-color: #1E2329; border-radius: 8px; padding: 15px; text-align: center; height: 100%; border-bottom: 3px solid #2B3139; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;}
    .metric-title { font-size: 13px; color: #848E9C; font-weight: bold; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;}
    .metric-value { font-size: 16px; font-weight: bold; margin-bottom: 5px;}
    .metric-explanation { font-size: 12px; color: #B7BDC6; line-height: 1.4; }
    
    .reason-box { background: #14151A; border-left: 4px solid #FCD535; padding: 15px; border-radius: 6px; margin-bottom: 10px; font-size: 14px; color: #EAECEF; line-height: 1.6;}
    .learning-box { background: #0B0E11; border: 1px solid #2B3139; padding: 15px; border-radius: 6px; margin-bottom: 15px; line-height: 1.8;}
    
    div.stButton > button { border-radius: 6px !important; font-weight: bold !important; width: 100% !important; background-color: #1E2329 !important; color: #EAECEF !important; border: 1px solid #FCD535 !important; transition: 0.2s;}
    div.stButton > button:hover { background-color: #FCD535 !important; color: #000000 !important; transform: scale(1.02); }
    </style>
""", unsafe_allow_html=True)

# ================= 🧠 3. STATE & AUTO REFRESH LOGIC =================
if 'active_coin' not in st.session_state:
    st.session_state.active_coin = "BTC/USDT"
if 'live_mode' not in st.session_state:
    st.session_state.live_mode = False # ডিফল্টভাবে অফ থাকবে

def change_active_coin(new_coin):
    st.session_state.active_coin = new_coin

# 📌 10 Second Auto Refresh (শুধুমাত্র লাইভ মোড অন থাকলে কাজ করবে)
if st.session_state.live_mode:
    st_autorefresh(interval=10000, limit=None, key="live_data_refresh")

# ================= ⚡ 4. MASTER CORE ENGINE =================
def fetch_and_analyze(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=500)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        
        # 4.1 Master Feature: Multi-Timeframe (MTF) Data
        df_15m = df.set_index('timestamp').resample('15min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last'}).dropna()
        df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
        mtf_15m_trend_up = df_15m['close'].iloc[-1] > df_15m['ema_50'].iloc[-1]
        
        # 4.2 Master Feature: VWAP
        df['date'] = df['timestamp'].dt.date
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_v'] = df['typical_price'] * df['volume']
        df['vwap'] = df.groupby('date')['tp_v'].cumsum() / df.groupby('date')['volume'].cumsum()
        
        # 4.3 Master Feature: Auto Support & Resistance
        support_level = df['low'].rolling(window=100).min().iloc[-1]
        resistance_level = df['high'].rolling(window=100).max().iloc[-1]

        # Indicators Setup
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        rsi_live = df['rsi'].iloc[-1]
        rsi_closed = df['rsi'].iloc[-2] 
        
        # Normal Candlestick Pattern Logic
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
        
        is_bullish_engulfing = c3['is_red'] and c2['is_green'] and (c2['close'] >= c3['open']) and (c2['open'] <= c3['close']) and (c2['body'] > c3['body'])
        is_bearish_engulfing = c3['is_green'] and c2['is_red'] and (c2['close'] <= c3['open']) and (c2['open'] >= c3['close']) and (c2['body'] > c3['body'])
        
        c4_mid = (c4['open'] + c4['close']) / 2
        is_morning_star = c4['is_red'] and (c3['body'] <= (c3['high'] - c3['low']) * 0.3) and c2['is_green'] and (c2['close'] >= c4_mid)
        is_evening_star = c4['is_green'] and (c3['body'] <= (c3['high'] - c3['low']) * 0.3) and c2['is_red'] and (c2['close'] <= c4_mid)

        bullish_pattern = is_hammer or is_bullish_engulfing or is_morning_star
        bearish_pattern = is_shooting_star or is_bearish_engulfing or is_evening_star

        # ARTISTIC REVERSAL LOGIC
        df['is_peak'] = (df['high'].shift(2) > df['high'].shift(1)) & (df['high'].shift(2) > df['high']) & (df['high'].shift(2) > df['high'].shift(3)) & (df['high'].shift(2) > df['high'].shift(4))
        df['is_valley'] = (df['low'].shift(2) < df['low'].shift(1)) & (df['low'].shift(2) < df['low']) & (df['low'].shift(2) < df['low'].shift(3)) & (df['low'].shift(2) < df['low'].shift(4))
                          
        df['peak_price'] = np.where(df['is_peak'], df['high'].shift(2), np.nan)
        df['valley_price'] = np.where(df['is_valley'], df['low'].shift(2), np.nan)
        
        recent_df = df.tail(60)
        recent_peaks = recent_df['peak_price'].dropna().values
        recent_valleys = recent_df['valley_price'].dropna().values

        is_double_top = False
        is_double_bottom = False
        is_head_shoulders = False
        is_inv_head_shoulders = False
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
        
        if is_double_bottom: 
            p_name = "ডাবল বটম ✌️"
            p_color = "#00BFFF"
            p_desc = "চার্টে ডাবল বটম (W) প্যাটার্ন।"
        elif is_inv_head_shoulders: 
            p_name = "ইনভার্স হেড এন্ড শোল্ডার 👤"
            p_color = "#00BFFF"
            p_desc = "ইনভার্স হেড এন্ড শোল্ডার।"
        elif is_double_top: 
            p_name = "ডাবল টপ ⛰️"
            p_color = "#FF00FF"
            p_desc = "চার্টে ডাবল টপ (M) প্যাটার্ন।"
        elif is_head_shoulders: 
            p_name = "হেড এন্ড শোল্ডার 👤"
            p_color = "#FF00FF"
            p_desc = "হেড এন্ড শোল্ডার।"
        elif is_morning_star: 
            p_name = "মর্নিং স্টার 🌅"
            p_color = "#00FF00"
            p_desc = "স্ট্রং বুলিশ রিভার্সাল।"
        elif is_evening_star: 
            p_name = "ইভনিং স্টার 🌃"
            p_color = "#FF1744"
            p_desc = "স্ট্রং বিয়ারিশ রিভার্সাল।"
        elif is_bullish_engulfing: 
            p_name = "বুলিশ এনগালফিং 📈"
            p_color = "#00FF00"
            p_desc = "বায়াররা সেলারদের গিলেছে।"
        elif is_bearish_engulfing: 
            p_name = "বিয়ারিশ এনগালফিং 📉"
            p_color = "#FF1744"
            p_desc = "সেলাররা বায়ারদের গিলেছে।"
        elif is_hammer: 
            p_name = "হ্যামার 🔨"
            p_color = "#00FF00"
            p_desc = "নিচে নামার পর কড়া রিজেকশন।"
        elif is_shooting_star: 
            p_name = "শুটিং স্টার 🌠"
            p_color = "#FF1744"
            p_desc = "উপরে ওঠার পর কড়া রিজেকশন।"

        # LIVE DATA EXTRACTION
        curr_price = df['close'].iloc[-1]
        curr_open = df['open'].iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        
        curr_ema5 = df['ema_5'].iloc[-1]
        curr_ema13 = df['ema_13'].iloc[-1]
        curr_ema50 = df['ema_50'].iloc[-1]
        
        closed_price = df['close'].iloc[-2]
        closed_ema5 = df['ema_5'].iloc[-2]
        closed_ema13 = df['ema_13'].iloc[-2]
        closed_ema50 = df['ema_50'].iloc[-2]
        
        curr_vwap = df['vwap'].iloc[-1]
        
        is_green_candle = curr_price > curr_open 
        is_red_candle = curr_price < curr_open   
        is_high_volume = curr_vol > (vol_sma * 1.5) 
        
        buyer_vol_spike = is_high_volume and is_green_candle
        seller_vol_spike = is_high_volume and is_red_candle

        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]
        
        # 4.4 Master Feature: Market Choppiness Filter
        is_choppy = atr < (curr_price * 0.001) 
        
        swing_low = df['low'].tail(15).min()
        swing_high = df['high'].tail(15).max()

        trend_up = closed_price > closed_ema50
        momentum_bullish = closed_ema5 > closed_ema13
        
        # 4.6 MASTER SIGNAL LOGIC
        signal_type = "NORMAL"
        
        if is_choppy:
            signal_type = "CHOPPY MARKET"
        elif artistic_buy_pattern:
            signal_type = "ARTISTIC SIGNAL BUY"
        elif artistic_sell_pattern:
            signal_type = "ARTISTIC SIGNAL SELL"
        elif trend_up and mtf_15m_trend_up and curr_price > curr_vwap and momentum_bullish and (bullish_pattern or buyer_vol_spike) and rsi_closed < 70:
            signal_type = "STRONG BUY"
        elif not trend_up and not mtf_15m_trend_up and curr_price < curr_vwap and not momentum_bullish and (bearish_pattern or seller_vol_spike) and rsi_closed > 30:
            signal_type = "STRONG SELL"

        return {
            'df': df, 'price': curr_price, 'signal': signal_type, 
            'rsi': rsi_live, 'curr_vol': curr_vol, 'vol_sma': vol_sma,
            'ema5': curr_ema5, 'ema13': curr_ema13, 'ema50': curr_ema50,
            'vwap': curr_vwap, 'mtf_up': mtf_15m_trend_up, 'is_choppy': is_choppy,
            'support': support_level, 'resistance': resistance_level,
            'p_name': p_name, 'p_desc': p_desc, 'p_color': p_color,
            'buyer_vol_spike': buyer_vol_spike, 'seller_vol_spike': seller_vol_spike, 
            'trend_up': curr_price > curr_ema50, 'momentum_bullish': curr_ema5 > curr_ema13, 
            'atr': atr, 'swing_low': swing_low, 'swing_high': swing_high,
            'has_pattern': bullish_pattern or bearish_pattern or artistic_buy_pattern or artistic_sell_pattern,
        }
    except Exception as e: 
        return None

all_data = {}
for coin in SCALPING_COINS:
    res = fetch_and_analyze(coin)
    if res: 
        all_data[coin] = res

# ================= 🚨 5. GLOBAL SIGNAL RADAR UI =================
st.markdown("<h3 style='color:#FCD535; margin-bottom:5px;'>🚨 স্ক্যাল্পিং মাস্টার লাইভ রাডার (5m + 15m MTF + VWAP)</h3>", unsafe_allow_html=True)

# 📌 PRO FEATURE: LIVE MODE TOGGLE TO PREVENT UI FREEZE & API BAN
toggle_col1, toggle_col2 = st.columns([1, 4])
with toggle_col1:
    live_status = st.toggle("🔴 লাইভ স্ক্যানার অন/অফ", value=st.session_state.live_mode)
    if live_status != st.session_state.live_mode:
        st.session_state.live_mode = live_status
        st.rerun()

with toggle_col2:
    if st.session_state.live_mode:
        st.markdown("<p style='color:#00FF00; font-size:14px; margin-top:8px;'>✅ লাইভ মোড অ্যাক্টিভ! অটোমেটিক ১০ সেকেন্ড পর পর সিগন্যাল আপডেট হচ্ছে।</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='color:#848E9C; font-size:14px; margin-top:8px;'>⏸️ লাইভ মোড অফ করা আছে। (API ব্যানের হাত থেকে বাঁচতে ট্রেড না করলে অফ রাখুন)</p>", unsafe_allow_html=True)

active_signals = 0
for coin, data in all_data.items():
    if data['signal'] in ["STRONG BUY", "STRONG SELL", "ARTISTIC SIGNAL BUY", "ARTISTIC SIGNAL SELL"]:
        active_signals += 1
        is_buy = data['signal'] in ["STRONG BUY", "ARTISTIC SIGNAL BUY"]
        
        if data['signal'] == "ARTISTIC SIGNAL BUY": 
            card_class = "global-alert-artistic-buy"
            color_main = "#00BFFF"
            icon = "🎨 আর্টিস্টিক সিগন্যাল বাই"
        elif data['signal'] == "ARTISTIC SIGNAL SELL": 
            card_class = "global-alert-artistic-sell"
            color_main = "#FF00FF"
            icon = "🎨 আর্টিস্টিক সিগন্যাল সেল"
        elif data['signal'] == "STRONG BUY": 
            card_class = "global-alert-buy"
            color_main = "#00FF00"
            icon = "🚀 STRONG BUY"
        elif data['signal'] == "STRONG SELL": 
            card_class = "global-alert-sell"
            color_main = "#FF1744"
            icon = "🧨 STRONG SELL"
        
        fee_margin = data['price'] * 0.002 
        
        if is_buy:
            sl = data['swing_low'] if data['swing_low'] < data['price'] else data['price'] - (data['atr'] * 1.5)
            tp = data['price'] + ((data['price'] - sl) * 1.5) + fee_margin 
        else:
            sl = data['swing_high'] if data['swing_high'] > data['price'] else data['price'] + (data['atr'] * 1.5)
            tp = data['price'] - ((sl - data['price']) * 1.5) - fee_margin
        
        st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.markdown(f"<h3 style='color:{color_main}; margin:0;'>{icon}: {coin}</h3><div style='font-size:13px; color:#EAECEF; margin-top:3px;'>📍 এন্ট্রি: {data['price']:.4f} | 📊 VWAP: {data['vwap']:.4f}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='color:#00FF00; font-weight:bold; font-size:15px; margin-top:5px;'>🎯 টার্গেট (ফী বাদে): {tp:.4f}</div><div style='color:#FF1744; font-weight:bold; font-size:15px;'>🛑 স্টপ লস (SL): {sl:.4f}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            st.button(f"🔍 চার্ট দেখুন", key=f"btn_{coin}", on_click=change_active_coin, args=(coin,))
        st.markdown("</div>", unsafe_allow_html=True)

if active_signals == 0:
    st.markdown("<div class='global-alert-normal'>⏳ বর্তমানে কোনো কয়েনে <b>STRONG</b> বা <b>ARTISTIC</b> সিগন্যাল নেই। মাস্টার বট মার্কেট ফিল্টার করছে...</div>", unsafe_allow_html=True)

st.markdown("<hr style='border-color:#2B3139;'>", unsafe_allow_html=True)

# ================= 📚 6. DETAILED MASTER DASHBOARD =================
col_a, col_b = st.columns([3, 1])
with col_a:
    st.markdown(f"<h3 style='color:#EAECEF; margin:0;'>🔍 {st.session_state.active_coin} প্রো অ্যানালাইসিস</h3>", unsafe_allow_html=True)
with col_b:
    selected = st.selectbox("📊 ম্যানুয়াল সিলেকশন", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))
    if selected != st.session_state.active_coin:
        change_active_coin(selected)
        st.rerun()

if st.session_state.active_coin in all_data:
    data = all_data[st.session_state.active_coin]
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        t_val = "আপ-ট্রেন্ড (UP)" if data['trend_up'] else "ডাউন-ট্রেন্ড (DOWN)"
        t_color = "#00FF00" if data['trend_up'] else "#FF1744"
        st.markdown(f"<div class='metric-card' style='border-color:{t_color}'><div class='metric-title'>১. 5m ট্রেন্ড (EMA 50)</div><div class='metric-value' style='color:{t_color}'>{t_val}</div></div>", unsafe_allow_html=True)
    with c2:
        mtf_val = "আপ-ট্রেন্ড (UP)" if data['mtf_up'] else "ডাউন-ট্রেন্ড (DOWN)"
        mtf_color = "#00FF00" if data['mtf_up'] else "#FF1744"
        st.markdown(f"<div class='metric-card' style='border-color:{mtf_color}'><div class='metric-title'>২. 15m বড় ট্রেন্ড (MTF)</div><div class='metric-value' style='color:{mtf_color}'>{mtf_val}</div></div>", unsafe_allow_html=True)
    with c3:
        v_val = "VWAP এর উপরে 🟢" if data['price'] > data['vwap'] else "VWAP এর নিচে 🔴"
        v_color = "#00FF00" if data['price'] > data['vwap'] else "#FF1744"
        st.markdown(f"<div class='metric-card' style='border-color:{v_color}'><div class='metric-title'>৩. ভলিউম প্রাইস (VWAP)</div><div class='metric-value' style='color:{v_color}'>{v_val}</div></div>", unsafe_allow_html=True)
    with c4:
        p_val = data['p_name']
        p_color = data['p_color']
        st.markdown(f"<div class='metric-card' style='border-color:{p_color}'><div class='metric-title'>৪. প্যাটার্ন স্ক্যানার</div><div class='metric-value' style='color:{p_color}'>{p_val}</div></div>", unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        m_val = "বায়াররা শক্তিশালী 🟢" if data['momentum_bullish'] else "সেলাররা শক্তিশালী 🔴"
        m_color = "#00FF00" if data['momentum_bullish'] else
