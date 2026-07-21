import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import traceback
from streamlit_autorefresh import st_autorefresh

# ================= 👑 1. PAGE CONFIGURATION =================
st.set_page_config(
    page_title="TRADE MENTOR: INSTITUTIONAL SCALPER (v9.6)", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "5m"
SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

# ================= 🎨 2. PREMIUM CSS (HONEST UI) =================
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #0B0E11 !important; color: #EAECEF !important; }
    ::-webkit-scrollbar { width: 10px !important; }
    ::-webkit-scrollbar-thumb { background: #FCD535 !important; border-radius: 10px; }
    [data-testid="stHeader"], header { display: none !important; }
    .block-container { padding-top: 20px !important; }
    .global-alert-buy { background: linear-gradient(90deg, rgba(0,255,0,0.1) 0%, #181A20 100%); border-left: 5px solid #00FF00; padding: 15px; border-radius: 8px; margin-bottom: 10px;}
    .global-alert-sell { background: linear-gradient(90deg, rgba(255,23,68,0.1) 0%, #181A20 100%); border-left: 5px solid #FF1744; padding: 15px; border-radius: 8px; margin-bottom: 10px;}
    .global-alert-normal { background: #181A20; border: 1px dashed #2B3139; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px; color: #848E9C;}
    .metric-card { background-color: #1E2329; border-radius: 8px; padding: 15px; text-align: center; height: 100%; border-bottom: 3px solid #2B3139; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;}
    .metric-title { font-size: 13px; color: #848E9C; font-weight: bold; margin-bottom: 8px; text-transform: uppercase;}
    .metric-value { font-size: 16px; font-weight: bold; margin-bottom: 5px;}
    .reason-box { background: #14151A; border-left: 4px solid #FCD535; padding: 15px; border-radius: 6px; margin-bottom: 10px; font-size: 14px; color: #EAECEF; line-height: 1.6;}
    .learning-box { background: #0B0E11; border: 1px solid #2B3139; padding: 15px; border-radius: 6px; margin-bottom: 15px; line-height: 1.8;}
    div.stButton > button { border-radius: 6px !important; font-weight: bold !important; width: 100% !important; background-color: #1E2329 !important; color: #EAECEF !important; border: 1px solid #FCD535 !important; margin-bottom: 20px;}
    div.stButton > button:hover { background-color: #FCD535 !important; color: #000000 !important;}
    </style>
""", unsafe_allow_html=True)

# ================= 🧠 3. STATE & AUTO REFRESH =================
if 'active_coin' not in st.session_state:
    st.session_state.active_coin = "BTC/USDT"
if 'live_mode' not in st.session_state:
    st.session_state.live_mode = False 

def change_active_coin(new_coin):
    st.session_state.active_coin = new_coin

if st.session_state.live_mode:
    st_autorefresh(interval=10000, limit=None, key="live_data_refresh")

# ================= ⚡ 4. INSTITUTIONAL CORE ENGINE =================
def fetch_and_analyze(coin):
    try:
        # MTF (No-Repaint: iloc[-2])
        bars_15m = exchange.fetch_ohlcv(coin, timeframe='15m', limit=100)
        df_15m = pd.DataFrame(bars_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
        mtf_15m_trend_up = df_15m['close'].iloc[-2] > df_15m['ema_50'].iloc[-2]

        # 5m
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=500)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # VWAP
        df['utc_date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        df['tp_v'] = ((df['high'] + df['low'] + df['close']) / 3) * df['volume']
        df['vwap'] = df.groupby('utc_date')['tp_v'].cumsum() / df.groupby('utc_date')['volume'].cumsum()
        
        # Indicators
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # RSI & ATR (with NaN safety)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        df['rsi'] = (100 - (100 / (1 + (gain / loss)))).fillna(50)
        
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        df['atr'] = df['tr'].rolling(14).mean().fillna(0)
        
        # ADX CALCULATION (with NaN safety)
        up_move = df['high'] - df['high'].shift(1)
        down_move = df['low'].shift(1) - df['low']
        df['+dm'] = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        df['-dm'] = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        df['+di'] = 100 * (df['+dm'].ewm(alpha=1/14, adjust=False).mean() / df['tr'].ewm(alpha=1/14, adjust=False).mean())
        df['-di'] = 100 * (df['-dm'].ewm(alpha=1/14, adjust=False).mean() / df['tr'].ewm(alpha=1/14, adjust=False).mean())
        df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'] + 1e-10)
        df['adx'] = df['dx'].ewm(alpha=1/14, adjust=False).mean().fillna(0)

        # NO-REPAINT ENGINE: Closed Candle (iloc[-2])
        c2 = df.iloc[-2]
        c3 = df.iloc[-3]
        
        c2_body = abs(c2['open'] - c2['close'])
        c3_body = abs(c3['open'] - c3['close'])
        c2_upper = c2['high'] - max(c2['open'], c2['close'])
        c2_lower = min(c2['open'], c2['close']) - c2['low']
        
        c2_is_green = c2['close'] > c2['open']
        c2_is_red = c2['close'] < c2['open']
        c3_is_green = c3['close'] > c3['open']
        c3_is_red = c3['close'] < c3['open']
        
        # Crypto Realistic Patterns
        is_hammer = (c2_lower >= (1.5 * c2_body)) and (c2_upper <= c2_body) and (c2_body > 0)
        is_shooting_star = (c2_upper >= (1.5 * c2_body)) and (c2_lower <= c2_body) and (c2_body > 0)
        
        is_be = c3_is_red and c2_is_green and (c2['close'] > c3['open'] - (c3_body * 0.3)) and (c2_body >= c3_body * 0.7)
        is_bere = c3_is_green and c2_is_red and (c2['close'] < c3['open'] + (c3_body * 0.3)) and (c2_body >= c3_body * 0.7)
        
        bullish_pattern = is_hammer or is_be
        bearish_pattern = is_shooting_star or is_bere

        closed_price = c2['close']
        live_price = df['close'].iloc[-1] 
        
        closed_vwap = df['vwap'].iloc[-2]
        closed_rsi = df['rsi'].iloc[-2]
        closed_vol = c2['volume'] if not pd.isna(c2['volume']) else 0
        closed_adx = df['adx'].iloc[-2]
        closed_atr = df['atr'].iloc[-2]
        
        # VOLUME REGIME: 8h session volume (96 candles)
        avg_vol_8h = df['volume'].rolling(96).mean().fillna(0).iloc[-2]
        vol_sma = df['volume'].rolling(20).mean().fillna(0).iloc[-2]
        
        trend_up = closed_price > df['ema_50'].iloc[-2]
        momentum_bullish = df['ema_5'].iloc[-2] > df['ema_13'].iloc[-2]
        buyer_vol_spike = (closed_vol > vol_sma * 1.5) and c2_is_green
        seller_vol_spike = (closed_vol > vol_sma * 1.5) and c2_is_red

        # NO REPAINT SWING (iloc[-16:-1])
        swing_low = df['low'].iloc[-16:-1].min()
        swing_high = df['high'].iloc[-16:-1].max()
        
        # FINAL CHOPPY MARKET FILTER (Logical 'AND' + NaN Check)
        is_choppy = False
        if pd.isna(closed_adx) or pd.isna(avg_vol_8h) or pd.isna(closed_vol):
            is_choppy = True 
        else:
            is_choppy = (closed_adx < 15) and (closed_vol < (avg_vol_8h * 0.5))

        # SCORE-BASED SYSTEM
        buy_score, sell_score = 0, 0
        if trend_up: buy_score += 1
        else: sell_score += 1
        
        if mtf_15m_trend_up: buy_score += 1
        else: sell_score += 1
        
        if closed_price > closed_vwap: buy_score += 1
        else: sell_score += 1
        
        if momentum_bullish: buy_score += 1
        else: sell_score += 1
        
        if buyer_vol_spike: buy_score += 1
        if seller_vol_spike: sell_score += 1
        if bullish_pattern: buy_score += 2
        if bearish_pattern: sell_score += 2

        signal_type = "NORMAL"
        if is_choppy:
            signal_type = "DEAD MARKET"
        elif buy_score >= 5 and closed_rsi < 75:
            signal_type = "HIGH PROBABILITY BUY"
        elif sell_score >= 4 and closed_rsi > 30: 
            signal_type = "HIGH PROBABILITY SELL"
            
        p_name = "প্যাটার্ন কনফার্ম 🟢" if bullish_pattern else "প্যাটার্ন কনফার্ম 🔴" if bearish_pattern else "প্যাটার্ন নেই ➖"
        p_color = "#00FF00" if bullish_pattern else "#FF1744" if bearish_pattern else "#848E9C"

        return {
            'signal_price': closed_price, 'live_price': live_price, 'signal': signal_type, 
            'buy_score': buy_score, 'sell_score': sell_score, 'rsi': closed_rsi, 
            'vwap': closed_vwap, 'atr': closed_atr, 'mtf_up': mtf_15m_trend_up, 
            'trend_up': trend_up, 'momentum_bullish': momentum_bullish,
            'is_choppy': is_choppy, 'adx': closed_adx, 'p_name': p_name, 'p_color': p_color, 
            'swing_low': swing_low, 'swing_high': swing_high
        }
    
    # 🔥 v9.6 FINAL FIX: UI-BASED STREAMLIT ERROR HANDLING
    except Exception as e: 
        st.error(f"🚨 Error processing {coin}: {str(e)}")
        return None

all_data = {coin: fetch_and_analyze(coin) for coin in SCALPING_COINS}

# ================= 🚨 5. GLOBAL SIGNAL RADAR UI =================
st.markdown("<h3 style='color:#FCD535;'>🚨 প্রপ-ফার্ম লাইভ রাডার (v9.6 - Institutional Scalper)</h3>", unsafe_allow_html=True)

tc1, tc2 = st.columns([1, 4])
with tc1:
    live_status = st.toggle("🔴 লাইভ স্ক্যানার অন/অফ", value=st.session_state.live_mode)
    if live_status != st.session_state.live_mode:
        st.session_state.live_mode = live_status
        st.rerun()
with tc2:
    if st.session_state.live_mode:
        st.markdown("<p style='color:#00FF00; font-size:14px; margin-top:8px;'>✅ লাইভ মোড অ্যাক্টিভ! অটোমেটিক ১০ সেকেন্ড পর পর আপডেট হচ্ছে।</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='color:#848E9C; font-size:14px; margin-top:8px;'>⏸️ লাইভ মোড অফ করা আছে।</p>", unsafe_allow_html=True)

active_signals = 0
for coin, data in all_data.items():
    if data and data['signal'] in ["HIGH PROBABILITY BUY", "HIGH PROBABILITY SELL"]:
        active_signals += 1
        is_buy = "BUY" in data['signal']
        
        cc = "global-alert-buy" if is_buy else "global-alert-sell"
        cm = "#00FF00" if is_buy else "#FF1744"
        ic = "✅ HIGH PROBABILITY BUY" if is_buy else "⚠️ HIGH PROBABILITY SELL"
        score = data['buy_score'] if is_buy else data['sell_score']
        
        entry = data['signal_price'] 
        live_p = data['live_price']
        atr = data['atr']
        
        # DYNAMIC SL & 1.8R MATH APPLIED
        rr = 1.8
        max_risk_cap = 0.01 
        taker_fee = 0.002   
        slippage = 0.0005   
        total_cost_percent = taker_fee + slippage
        
        if is_buy:
            tech_sl_dist = abs(entry - data['swing_low'])
            atr_sl_dist = atr * 1.5
            stop_distance = max(atr_sl_dist, tech_sl_dist)
            final_sl_dist = min(stop_distance, entry * max_risk_cap) 
            sl = entry - final_sl_dist
            tp = entry + (final_sl_dist * rr) + (entry * total_cost_percent)
        else:
            tech_sl_dist = abs(data['swing_high'] - entry)
            atr_sl_dist = atr * 1.5
            stop_distance = max(atr_sl_dist, tech_sl_dist)
            final_sl_dist = min(stop_distance, entry * max_risk_cap) 
            sl = entry + final_sl_dist
            tp = entry - (final_sl_dist * rr) - (entry * total_cost_percent)
        
        html_card = (
            f"<div class='{cc}'>"
            f"<h3 style='color:{cm}; margin:0 0 10px 0;'>{ic}: {coin}</h3>"
            f"<div style='display: flex; justify-content: space-between; flex-wrap: wrap; margin-bottom: 8px;'>"
            f"<span style='font-size:14px; color:#EAECEF;'>📍 সিগন্যাল এন্ট্রি: <b>{entry:.4f}</b> | ⚡ লাইভ প্রাইস: <b>{live_p:.4f}</b></span>"
            f"<span style='font-size:14px; color:#EAECEF;'>🎯 বট স্কোর: <b>{score}/7</b></span>"
            f"</div>"
            f"<div style='display: flex; justify-content: space-between; flex-wrap: wrap;'>"
            f"<span style='color:#00FF00; font-weight:bold; font-size:15px;'>🚀 টার্গেট (1.8R): {tp:.4f}</span>"
            f"<span style='color:#FF1744; font-weight:bold; font-size:15px;'>🛑 ডায়নামিক SL: {sl:.4f}</span>"
            f"</div>"
            f"</div>"
        )
        st.markdown(html_card, unsafe_allow_html=True)
        st.button(f"🔍 {coin} চার্ট দেখুন", key=f"btn_{coin}", on_click=change_active_coin, args=(coin,))

if active_signals == 0:
    st.markdown("<div class='global-alert-normal'>⏳ বর্তমানে কোনো কয়েনে প্রো-সিগন্যাল নেই। সঠিক সেটআপ পেলেই এখানে শো করবে...</div>", unsafe_allow_html=True)
    
st.markdown("<hr style='border-color:#2B3139;'>", unsafe_allow_html=True)

# ================= 📚 6. DETAILED MASTER DASHBOARD =================
ca, cb = st.columns([3, 1])
with ca:
    st.markdown(f"<h3 style='color:#EAECEF; margin:0;'>🔍 {st.session_state.active_coin} প্রো অ্যানালাইসিস</h3>", unsafe_allow_html=True)
with cb:
    selected = st.selectbox("📊 ম্যানুয়াল সিলেকশন", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))
    if selected != st.session_state.active_coin:
        change_active_coin(selected)
        st.rerun()

if st.session_state.active_coin in all_data and all_data[st.session_state.active_coin] is not None:
    d = all_data[st.session_state.active_coin]
    
    mc1, mc2, mc3, mc4 = st.columns(4)
    if d['trend_up']: tv, tc = "আপ-ট্রেন্ড", "#00FF00"
    else: tv, tc = "ডাউন-ট্রেন্ড", "#FF1744"
    with mc1: st.markdown(f"<div class='metric-card' style='border-color:{tc}'><div class='metric-title'>১. 5m ট্রেন্ড</div><div class='metric-value' style='color:{tc}'>{tv}</div></div>", unsafe_allow_html=True)
    
    if d['mtf_up']: mtv, mtc = "আপ-ট্রেন্ড", "#00FF00"
    else: mtv, mtc = "ডাউন-ট্রেন্ড", "#FF1744"
    with mc2: st.markdown(f"<div class='metric-card' style='border-color:{mtc}'><div class='metric-title'>২. 15m বড় ট্রেন্ড</div><div class='metric-value' style='color:{mtc}'>{mtv}</div></div>", unsafe_allow_html=True)
    
    if d['is_choppy']: 
        adx_v, adx_c = f"DEAD 🔴", "#FF1744"
    else: 
        adx_v, adx_c = f"ACTIVE 🟢", "#00FF00"
    with mc3: st.markdown(f"<div class='metric-card' style='border-color:{adx_c}'><div class='metric-title'>৩. ADX + Vol ফিল্টার</div><div class='metric-value' style='color:{adx_c}'>{adx_v}</div></div>", unsafe_allow_html=True)
    
    with mc4: st.markdown(f"<div class='metric-card' style='border-color:{d['p_color']}'><div class='metric-title'>৪. ক্যান্ডেলস্টিক</div><div class='metric-value' style='color:{d['p_color']}'>{d['p_name']}</div></div>", unsafe_allow_html=True)
    
    header_msg = f"<h4 style='color:#FCD535; margin-top:15px; border-bottom: 1px solid #2B3139; padding-bottom:10px;'>💡 {st.session_state.active_coin} মাস্টার ব্রেকডাউন</h4>"
    st.markdown(header_msg, unsafe_allow_html=True)
    
    if d['signal'] == "DEAD MARKET":
        st.markdown("<div class='reason-box' style='border-left-color: #FF1744;'><b>🚨 ডেড মার্কেট মুড অ্যাক্টিভ!</b><br>বট ট্রেড অফ রেখেছে কারণ ADX ১৫ এর নিচে এবং মার্কেটে ভলিউম নেই। এটি ফেক সিগন্যাল ফিল্টার করছে।</div>", unsafe_allow_html=True)
    elif "BUY" in d['signal']:
        st.markdown(f"<div class='reason-box' style='border-left-color: #00FF00;'><b>HIGH PROBABILITY BUY 🚀</b><br>বট <b>{d['buy_score']} পয়েন্ট</b> পেয়েছে। ট্রেন্ড আপ, এবং ভলিউম কনফার্মড।</div>", unsafe_allow_html=True)
    elif "SELL" in d['signal']:
        st.markdown(f"<div class='reason-box' style='border-left-color: #FF1744;'><b>HIGH PROBABILITY SELL 🧨</b><br>বট <b>{d['sell_score']} পয়েন্ট</b> পেয়েছে। ডাউন-ট্রেন্ড কনফার্মড, এবং প্রপার বিয়ারিশ মুভমেন্ট পাওয়া গেছে।</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='reason-box' style='border-left-color: #848E9C;'><b>{st.session_state.active_coin} এ কোনো প্রো-সিগন্যাল নেই।</b><br>সঠিক স্কোরের জন্য অপেক্ষা করা হচ্ছে।</div>", unsafe_allow_html=True)

    header_dash = "<h4 style='color:#00BFFF; margin-top:20px;'>📊 লাইভ প্যারামিটার ও ড্যাশবোর্ড</h4>"
    st.markdown(header_dash, unsafe_allow_html=True)
    
    lc1, lc2 = st.columns(2)
    with lc1:
        st.markdown((
            "<div class='learning-box'>"
            "<b style='color:#FCD535;'>📌 বর্তমান টেকনিক্যাল নাম্বার</b><br>"
            f"🔹 সিগন্যাল প্রাইস (Closed): {d['signal_price']:.4f}<br>"
            f"🔹 লাইভ প্রাইস (Running): {d['live_price']:.4f}<br>"
            f"🔹 ADX (Trend Strength): {d['adx']:.2f}<br>"
            f"🔹 বাই স্কোর: {d['buy_score']}/7 | সেল স্কোর: {d['sell_score']}/7"
            "</div>"
        ), unsafe_allow_html=True)
        
    with lc2:
        vwap_status = 'উপরে 🟢' if d['signal_price'] > d['vwap'] else 'নিচে 🔴'
        mom_status = 'Bullish 🟢' if d['momentum_bullish'] else 'Bearish 🔴'
        st.markdown((
            "<div class='learning-box'>"
            "<b style='color:#00FF00;'>💡 মাস্টার কন্ডিশন স্ট্যাটাস</b><br>"
            f"✅ VWAP পজিশন: {vwap_status}<br>"
            f"✅ 5m মোমেন্টাম: {mom_status}<br>"
            f"✅ ADX স্ট্যাটাস: {'ডেড মার্কেট 🔴' if d['is_choppy'] else 'রানিং মার্কেট 🟢'}<br>"
            f"✅ ডায়নামিক স্লিপেজ বাফার: অ্যাক্টিভ 🟢<br>"
            "</div>"
        ), unsafe_allow_html=True)
