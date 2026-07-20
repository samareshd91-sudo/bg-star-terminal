import streamlit as st
import ccxt
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

# ================= 👑 1. PAGE CONFIGURATION =================
st.set_page_config(
    page_title="TRADE MENTOR: PRO SCALPER MASTER", 
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

# ================= ⚡ 4. HARDCORE CORE ENGINE (NO-REPAINT & SCORE-BASED) =================
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
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        
        # Indicators
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        # NO-REPAINT ENGINE: সমস্ত লজিক Closed Candle (iloc[-2]) থেকে নেওয়া
        c2 = df.iloc[-2]  # Last Closed Candle
        c3 = df.iloc[-3]
        c4 = df.iloc[-4]
        
        # Candle Patterns
        c2_body = abs(c2['open'] - c2['close'])
        c2_upper = c2['high'] - max(c2['open'], c2['close'])
        c2_lower = min(c2['open'], c2['close']) - c2['low']
        c2_is_green = c2['close'] > c2['open']
        c2_is_red = c2['close'] < c2['open']
        c3_body = abs(c3['open'] - c3['close'])
        c3_is_green = c3['close'] > c3['open']
        c3_is_red = c3['close'] < c3['open']

        is_hammer = (c2_lower >= (2 * c2_body)) and (c2_upper <= c2_body) and (c2_body > 0)
        is_shooting_star = (c2_upper >= (2 * c2_body)) and (c2_lower <= c2_body) and (c2_body > 0)
        is_be = c3_is_red and c2_is_green and (c2['close'] >= c3['open']) and (c2['open'] <= c3['close']) and (c2_body > c3_body)
        is_bere = c3_is_green and c2_is_red and (c2['close'] <= c3['open']) and (c2['open'] >= c3['close']) and (c2_body > c3_body)
        
        bullish_pattern = is_hammer or is_be
        bearish_pattern = is_shooting_star or is_bere

        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-2]

        # No-Repaint Variables
        closed_price = c2['close']
        closed_vwap = df['vwap'].iloc[-2]
        closed_rsi = df['rsi'].iloc[-2]
        closed_vol = c2['volume']
        vol_sma = df['volume'].rolling(20).mean().iloc[-2]
        
        trend_up = closed_price > df['ema_50'].iloc[-2]
        momentum_bullish = df['ema_5'].iloc[-2] > df['ema_13'].iloc[-2]
        
        buyer_vol_spike = (closed_vol > vol_sma * 1.5) and c2_is_green
        seller_vol_spike = (closed_vol > vol_sma * 1.5) and c2_is_red

        # SCORE-BASED SYSTEM (Total 7 Points)
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

        # Final Signal Check
        signal_type = "NORMAL"
        if buy_score >= 5 and closed_rsi < 75:
            signal_type = "HIGH PROBABILITY BUY"
        elif sell_score >= 5 and closed_rsi > 25:
            signal_type = "HIGH PROBABILITY SELL"
            
        p_name = "প্যাটার্ন কনফার্ম 🟢" if bullish_pattern else "প্যাটার্ন কনফার্ম 🔴" if bearish_pattern else "প্যাটার্ন নেই ➖"
        p_color = "#00FF00" if bullish_pattern else "#FF1744" if bearish_pattern else "#848E9C"

        swing_low = df['low'].tail(15).min()
        swing_high = df['high'].tail(15).max()
        is_choppy = atr < (df['close'].iloc[-1] * 0.001)

        return {
            'price': df['close'].iloc[-1], 'closed_price': closed_price, 'signal': signal_type, 
            'buy_score': buy_score, 'sell_score': sell_score, 'rsi': closed_rsi, 
            'vwap': closed_vwap, 'atr': atr, 'mtf_up': mtf_15m_trend_up, 
            'trend_up': trend_up, 'momentum_bullish': momentum_bullish,
            'is_choppy': is_choppy, 'p_name': p_name, 'p_color': p_color, 
            'swing_low': swing_low, 'swing_high': swing_high
        }
    except Exception: return None

all_data = {coin: fetch_and_analyze(coin) for coin in SCALPING_COINS}

# ================= 🚨 5. GLOBAL SIGNAL RADAR UI =================
st.markdown("<h3 style='color:#FCD535;'>🚨 প্রফেশনাল লাইভ রাডার (No-Repaint & Score Engine)</h3>", unsafe_allow_html=True)

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
        st.markdown("<p style='color:#848E9C; font-size:14px; margin-top:8px;'>⏸️ লাইভ মোড অফ করা আছে। (API বাঁচাতে ট্রেড না করলে অফ রাখুন)</p>", unsafe_allow_html=True)

active_signals = 0
for coin, data in all_data.items():
    if data and data['signal'] in ["HIGH PROBABILITY BUY", "HIGH PROBABILITY SELL"]:
        active_signals += 1
        is_buy = "BUY" in data['signal']
        
        cc = "global-alert-buy" if is_buy else "global-alert-sell"
        cm = "#00FF00" if is_buy else "#FF1744"
        ic = "✅ HIGH PROBABILITY BUY" if is_buy else "⚠️ HIGH PROBABILITY SELL"
        score = data['buy_score'] if is_buy else data['sell_score']
        
        # MAX RISK CAP (0.5%) & DYNAMIC FEE CALCULATION
        max_risk_cap = 0.005 
        taker_fee = 0.001 
        entry = data['price']
        
        if is_buy:
            tech_sl = data['swing_low'] if data['swing_low'] < entry else entry - (data['atr'] * 1.5)
            if (entry - tech_sl) / entry > max_risk_cap: sl = entry * (1 - max_risk_cap)
            else: sl = tech_sl
            tp = entry + ((entry - sl) * 1.5) + (entry * taker_fee * 2)
        else:
            tech_sl = data['swing_high'] if data['swing_high'] > entry else entry + (data['atr'] * 1.5)
            if (tech_sl - entry) / entry > max_risk_cap: sl = entry * (1 + max_risk_cap)
            else: sl = tech_sl
            tp = entry - ((sl - entry) * 1.5) - (entry * taker_fee * 2)
        
        html_card = (
            f"<div class='{cc}'>"
            f"<h3 style='color:{cm}; margin:0 0 10px 0;'>{ic}: {coin}</h3>"
            f"<div style='display: flex; justify-content: space-between; flex-wrap: wrap; margin-bottom: 8px;'>"
            f"<span style='font-size:14px; color:#EAECEF;'>📍 এন্ট্রি: <b>{entry:.4f}</b></span>"
            f"<span style='font-size:14px; color:#EAECEF;'>🎯 বট স্কোর: <b>{score}/7</b></span>"
            f"</div>"
            f"<div style='display: flex; justify-content: space-between; flex-wrap: wrap;'>"
            f"<span style='color:#00FF00; font-weight:bold; font-size:15px;'>🚀 নিট টার্গেট (ফী সহ): {tp:.4f}</span>"
            f"<span style='color:#FF1744; font-weight:bold; font-size:15px;'>🛑 সেফ SL (Risk Capped): {sl:.4f}</span>"
            f"</div>"
            f"</div>"
        )
        st.markdown(html_card, unsafe_allow_html=True)
        st.button(f"🔍 {coin} চার্ট দেখুন", key=f"btn_{coin}", on_click=change_active_coin, args=(coin,))

if active_signals == 0:
    st.markdown("<div class='global-alert-normal'>⏳ বর্তমানে কোনো কয়েনে প্রো-সিগন্যাল নেই। ৫ পয়েন্টের বেশি স্কোর পেলেই এখানে শো করবে...</div>", unsafe_allow_html=True)
    
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
    
    if d['closed_price'] > d['vwap']: vv, vc = "VWAP এর উপরে 🟢", "#00FF00"
    else: vv, vc = "VWAP এর নিচে 🔴", "#FF1744"
    with mc3: st.markdown(f"<div class='metric-card' style='border-color:{vc}'><div class='metric-title'>৩. VWAP</div><div class='metric-value' style='color:{vc}'>{vv}</div></div>", unsafe_allow_html=True)
    
    with mc4: st.markdown(f"<div class='metric-card' style='border-color:{d['p_color']}'><div class='metric-title'>৪. ক্যান্ডেলস্টিক</div><div class='metric-value' style='color:{d['p_color']}'>{d['p_name']}</div></div>", unsafe_allow_html=True)
    
    header_msg = f"<h4 style='color:#FCD535; margin-top:15px; border-bottom: 1px solid #2B3139; padding-bottom:10px;'>💡 {st.session_state.active_coin} মাস্টার ব্রেকডাউন (Closed Candle Logic)</h4>"
    st.markdown(header_msg, unsafe_allow_html=True)
    
    if d['is_choppy']:
        st.markdown("<div class='reason-box' style='border-left-color: #848E9C;'><b>মার্কেট ডেড!</b><br>স্ক্যাল্পিংয়ের জন্য এন্ট্রি নিলে লস হওয়ার চান্স বেশি। ভলিউম আসার অপেক্ষা করুন।</div>", unsafe_allow_html=True)
    elif "BUY" in d['signal']:
        st.markdown(f"<div class='reason-box'><b>HIGH PROBABILITY BUY সিগন্যাল কেন?</b><br>বট ৭ এর মধ্যে <b>{d['buy_score']} পয়েন্ট</b> পেয়েছে। ৫ মিনিটের ট্রেন্ড আপ, প্রাইস VWAP এর উপরে এবং ভলিউম কনফার্মড। ফী হিসাব করে টার্গেট সেট করা হয়েছে।</div>", unsafe_allow_html=True)
    elif "SELL" in d['signal']:
        st.markdown(f"<div class='reason-box'><b>HIGH PROBABILITY SELL সিগন্যাল কেন?</b><br>বট ৭ এর মধ্যে <b>{d['sell_score']} পয়েন্ট</b> পেয়েছে। ৫ মিনিটের ট্রেন্ড ডাউন, প্রাইস VWAP এর নিচে এবং ভলিউম কনফার্মড। ফী হিসাব করে টার্গেট সেট করা হয়েছে।</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='reason-box' style='border-left-color: #848E9C;'><b>{st.session_state.active_coin} এ কোনো প্রো-সিগন্যাল নেই।</b><br>বটের স্কোর এখনো ৫ পয়েন্টে পৌঁছায়নি। সবগুলো সেফটি রুল না মেলা পর্যন্ত এন্ট্রি নেওয়া রিস্কি।</div>", unsafe_allow_html=True)

    header_dash = "<h4 style='color:#00BFFF; margin-top:20px;'>📊 লাইভ প্যারামিটার ও ড্যাশবোর্ড</h4>"
    st.markdown(header_dash, unsafe_allow_html=True)
    
    lc1, lc2 = st.columns(2)
    with lc1:
        st.markdown((
            "<div class='learning-box'>"
            "<b style='color:#FCD535;'>📌 বর্তমান টেকনিক্যাল নাম্বার</b><br>"
            f"🔹 বর্তমান প্রাইস (Live): {d['price']:.4f}<br>"
            f"🔹 VWAP (Closed): {d['vwap']:.4f}<br>"
            f"🔹 RSI (Closed): {d['rsi']:.2f}<br>"
            f"🔹 বাই স্কোর: {d['buy_score']}/7 | সেল স্কোর: {d['sell_score']}/7"
            "</div>"
        ), unsafe_allow_html=True)
        
    with lc2:
        mtf_status = 'বুলিশ 🟢' if d['mtf_up'] else 'বিয়ারিশ 🔴'
        vwap_status = 'উপরে 🟢' if d['closed_price'] > d['vwap'] else 'নিচে 🔴'
        mom_status = 'Bullish 🟢' if d['momentum_bullish'] else 'Bearish 🔴'
        chop_status = 'ডেড 🔴' if d['is_choppy'] else 'ভলিউম আছে 🟢'
        st.markdown((
            "<div class='learning-box'>"
            "<b style='color:#00FF00;'>💡 মাস্টার কন্ডিশন স্ট্যাটাস</b><br>"
            f"✅ 15m ট্রেন্ড (No-Repaint): {mtf_status}<br>"
            f"✅ VWAP পজিশন: {vwap_status}<br>"
            f"✅ 5m মোমেন্টাম: {mom_status}<br>"
            f"✅ মার্কেট অবস্থা: {chop_status}<br>"
            "</div>"
        ), unsafe_allow_html=True)
