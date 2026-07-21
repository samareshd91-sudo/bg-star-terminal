import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import traceback
import time
from streamlit_autorefresh import st_autorefresh

# ================= 👑 1. PAGE CONFIGURATION =================
st.set_page_config(
    page_title="TRADE MENTOR: INSTITUTIONAL SCALPER (v11 PRO)", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "5m"
SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

# ================= 🎨 2. PREMIUM CSS =================
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
    .risk-box { background: rgba(0, 191, 255, 0.1); border: 1px dashed #00BFFF; padding: 12px; border-radius: 6px; margin-top: 15px; font-size: 14px;}
    div.stButton > button { border-radius: 6px !important; font-weight: bold !important; width: 100% !important; background-color: #1E2329 !important; color: #EAECEF !important; border: 1px solid #FCD535 !important; margin-bottom: 20px;}
    div.stButton > button:hover { background-color: #FCD535 !important; color: #000000 !important;}
    </style>
""", unsafe_allow_html=True)

# ================= 🧠 3. STATE & AUTO REFRESH =================
if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"
if 'live_mode' not in st.session_state: st.session_state.live_mode = False 

def change_active_coin(new_coin): st.session_state.active_coin = new_coin

if st.session_state.live_mode:
    st_autorefresh(interval=10000, limit=None, key="live_data_refresh")

# ================= 🛡️ RISK MANAGEMENT SETTINGS =================
st.sidebar.markdown("<h3 style='color:#FCD535;'>🛡️ রিস্ক ম্যানেজমেন্ট</h3>", unsafe_allow_html=True)
st.sidebar.markdown("আপনার ক্যাপিটাল অনুযায়ী হিসাব করুন:")
acc_balance = st.sidebar.number_input("অ্যাকাউন্ট ব্যালেন্স (USDT)", value=3.5, step=1.0) # $3.5 = approx ₹300
leverage = st.sidebar.number_input("লিভারেজ (Leverage)", value=50, step=5)
risk_per_trade = st.sidebar.number_input("ট্রেড প্রতি রিস্ক (%)", value=5.0, step=1.0, help="$3.5 এর 5% মানে $0.17 বা প্রায় ₹15 লস")

# ================= ⚡ 4. INSTITUTIONAL CORE ENGINE =================
def wilder_rma(series, length):
    return series.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

# 🔥 NEW: API Retry System (Resilience against network drops)
def fetch_data_with_retry(symbol, tf, limit, retries=3):
    for i in range(retries):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        except Exception as e:
            if i == retries - 1: raise e
            time.sleep(2) # Wait 2 seconds before retrying

def fetch_and_analyze(coin):
    try:
        # MTF using Retry System
        bars_15m = fetch_data_with_retry(coin, '15m', 100)
        df_15m = pd.DataFrame(bars_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
        mtf_15m_trend_up = df_15m['close'].iloc[-2] > df_15m['ema_50'].iloc[-2]

        # 5m using Retry System
        bars = fetch_data_with_retry(coin, selected_tf, 500)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # VWAP
        df['utc_date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        df['tp_v'] = ((df['high'] + df['low'] + df['close']) / 3) * df['volume']
        df['vwap'] = df.groupby('utc_date')['tp_v'].cumsum() / df.groupby('utc_date')['volume'].cumsum()
        
        # Indicators
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        df['rsi'] = (100 - (100 / (1 + (gain / loss)))).fillna(50)
        
        # Exact Wilder's ATR & ADX
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        df['atr'] = wilder_rma(df['tr'], 14).fillna(0)
        
        up_move = df['high'] - df['high'].shift(1)
        down_move = df['low'].shift(1) - df['low']
        df['+dm'] = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        df['-dm'] = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        df['+di'] = 100 * (wilder_rma(pd.Series(df['+dm']), 14) / (df['atr'] + 1e-10))
        df['-di'] = 100 * (wilder_rma(pd.Series(df['-dm']), 14) / (df['atr'] + 1e-10))
        df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'] + 1e-10)
        df['adx'] = wilder_rma(df['dx'], 14).fillna(0)

        # Closed Candle
        c2 = df.iloc[-2]; c3 = df.iloc[-3]
        c2_body = abs(c2['open'] - c2['close']); c3_body = abs(c3['open'] - c3['close'])
        c2_upper = c2['high'] - max(c2['open'], c2['close'])
        c2_lower = min(c2['open'], c2['close']) - c2['low']
        
        c2_is_green = c2['close'] > c2['open']; c2_is_red = c2['close'] < c2['open']
        c3_is_green = c3['close'] > c3['open']; c3_is_red = c3['close'] < c3['open']
        
        is_hammer = (c2_lower >= (1.5 * c2_body)) and (c2_upper <= c2_body) and (c2_body > 0)
        is_shooting_star = (c2_upper >= (1.5 * c2_body)) and (c2_lower <= c2_body) and (c2_body > 0)
        is_be = c3_is_red and c2_is_green and (c2['close'] > c3['open'] - (c3_body * 0.3)) and (c2_body >= c3_body * 0.7)
        is_bere = c3_is_green and c2_is_red and (c2['close'] < c3['open'] + (c3_body * 0.3)) and (c2_body >= c3_body * 0.7)
        
        bullish_pattern = is_hammer or is_be
        bearish_pattern = is_shooting_star or is_bere

        closed_price = c2['close']; live_price = df['close'].iloc[-1] 
        closed_vwap = df['vwap'].iloc[-2]; closed_rsi = df['rsi'].iloc[-2]
        closed_vol = c2['volume'] if not pd.isna(c2['volume']) else 0
        closed_adx = df['adx'].iloc[-2]; closed_atr = df['atr'].iloc[-2]
        
        # Normalized Volume Regime
        avg_vol_8h = df['volume'].rolling(96).mean().fillna(0).iloc[-2]
        rvol = closed_vol / (avg_vol_8h + 1e-10) # Relative Volume
        
        trend_up = closed_price > df['ema_50'].iloc[-2]
        momentum_bullish = df['ema_5'].iloc[-2] > df['ema_13'].iloc[-2]
        buyer_vol_spike = (rvol > 1.5) and c2_is_green
        seller_vol_spike = (rvol > 1.5) and c2_is_red

        swing_low = df['low'].iloc[-16:-1].min()
        swing_high = df['high'].iloc[-16:-1].max()
        
        is_rsi_sideways = (closed_rsi >= 45) and (closed_rsi <= 55)
        is_choppy = False
        if pd.isna(closed_adx) or pd.isna(rvol): is_choppy = True 
        else: is_choppy = ((closed_adx < 15) and (rvol < 0.5)) or is_rsi_sideways

        # Scoring
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
        if is_choppy: signal_type = "DEAD MARKET"
        elif buy_score >= 5 and 55 < closed_rsi < 75: signal_type = "HIGH PROBABILITY BUY"
        elif sell_score >= 4 and 30 < closed_rsi < 45: signal_type = "HIGH PROBABILITY SELL"
            
        p_name = "প্যাটার্ন কনফার্ম 🟢" if bullish_pattern else "প্যাটার্ন কনফার্ম 🔴" if bearish_pattern else "প্যাটার্ন নেই ➖"
        p_color = "#00FF00" if bullish_pattern else "#FF1744" if bearish_pattern else "#848E9C"

        return {
            'signal_price': closed_price, 'live_price': live_price, 'signal': signal_type, 
            'buy_score': buy_score, 'sell_score': sell_score, 'rsi': closed_rsi, 
            'vwap': closed_vwap, 'atr': closed_atr, 'mtf_up': mtf_15m_trend_up, 
            'trend_up': trend_up, 'momentum_bullish': momentum_bullish,
            'is_choppy': is_choppy, 'is_rsi_sideways': is_rsi_sideways, 'adx': closed_adx, 'rvol': rvol,
            'p_name': p_name, 'p_color': p_color, 'swing_low': swing_low, 'swing_high': swing_high
        }
    except Exception as e: 
        st.error(f"🚨 Network/API Error processing {coin}: {str(e)}")
        return None

all_data = {coin: fetch_and_analyze(coin) for coin in SCALPING_COINS}

# ================= 🚨 5. GLOBAL SIGNAL RADAR UI =================
st.markdown("<h3 style='color:#FCD535;'>🚨 প্রপ-ফার্ম লাইভ রাডার (v11 - Ultimate Execution)</h3>", unsafe_allow_html=True)

tc1, tc2 = st.columns([1, 4])
with tc1:
    live_status = st.toggle("🔴 লাইভ স্ক্যানার অন/অফ", value=st.session_state.live_mode)
    if live_status != st.session_state.live_mode:
        st.session_state.live_mode = live_status; st.rerun()
with tc2:
    if st.session_state.live_mode: st.markdown("<p style='color:#00FF00; font-size:14px; margin-top:8px;'>✅ লাইভ মোড অ্যাক্টিভ! অটোমেটিক ১০ সেকেন্ড পর পর আপডেট হচ্ছে।</p>", unsafe_allow_html=True)

active_signals = 0
for coin, data in all_data.items():
    if data and data['signal'] in ["HIGH PROBABILITY BUY", "HIGH PROBABILITY SELL"]:
        active_signals += 1
        is_buy = "BUY" in data['signal']
        
        cc = "global-alert-buy" if is_buy else "global-alert-sell"
        cm = "#00FF00" if is_buy else "#FF1744"
        ic = "✅ HIGH PROBABILITY BUY" if is_buy else "⚠️ HIGH PROBABILITY SELL"
        
        entry = data['signal_price'] 
        live_p = data['live_price']
        atr = data['atr']
        
        # Risk Limits
        tech_sl_dist = abs(entry - data['swing_low']) if is_buy else abs(data['swing_high'] - entry)
        atr_sl_dist = atr * 1.5
        stop_distance = max(atr_sl_dist, tech_sl_dist)
        
        sl = entry - stop_distance if is_buy else entry + stop_distance
        sl_pct = abs(entry - sl) / entry
        
        # 🔥 NEW: Fee & Slippage Logic
        taker_fee = 0.002   # 0.1% Buy + 0.1% Sell
        slippage = 0.0005   # 0.05% Slippage Buffer
        total_cost_percent = taker_fee + slippage
        
        # TP Calculation (Includes Fee + Slippage)
        if is_buy:
            tp = entry + (stop_distance * 1.8) + (entry * total_cost_percent)
        else:
            tp = entry - (stop_distance * 1.8) - (entry * total_cost_percent)
        
        # Position Sizing Logic
        risk_amount_usdt = acc_balance * (risk_per_trade / 100) # Max loss allowed
        position_size_usdt = risk_amount_usdt / sl_pct # Total Position Size needed
        margin_required = position_size_usdt / leverage # Margin to open trade
        
        html_card = (
            f"<div class='{cc}'>"
            f"<h3 style='color:{cm}; margin:0 0 10px 0;'>{ic}: {coin}</h3>"
            f"<div style='display: flex; justify-content: space-between; flex-wrap: wrap; margin-bottom: 8px;'>"
            f"<span style='font-size:14px; color:#EAECEF;'>📍 সিগন্যাল এন্ট্রি: <b>{entry:.4f}</b></span>"
            f"<span style='color:#FF1744; font-weight:bold; font-size:15px;'>🛑 SL: {sl:.4f}</span>"
            f"<span style='color:#00FF00; font-weight:bold; font-size:15px;'>🚀 টার্গেট (নিট 1.8R): {tp:.4f}</span>"
            f"</div>"
            f"<div class='risk-box'>"
            f"<b>💼 পজিশন সাইজিং (Risk: ${risk_amount_usdt:.2f} | Lev: {leverage}x)</b><br>"
            f"👉 ট্রেড নেওয়ার জন্য মার্জিন ব্যবহার করুন: <b style='color:#FCD535;'>${margin_required:.2f} USDT</b><br>"
            f"<i>(ফী ও স্লিপেজ টার্গেটের সাথে যুক্ত করা হয়েছে। SL হিট করলে ঠিক ${risk_amount_usdt:.2f} লস হবে।)</i>"
            f"</div>"
            f"</div>"
        )
        st.markdown(html_card, unsafe_allow_html=True)
        st.button(f"🔍 {coin} চার্ট দেখুন", key=f"btn_{coin}", on_click=change_active_coin, args=(coin,))

if active_signals == 0: st.markdown("<div class='global-alert-normal'>⏳ বর্তমানে কোনো কয়েনে প্রো-সিগন্যাল নেই। সঠিক ব্রেকআউটের জন্য অপেক্ষা করা হচ্ছে...</div>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#2B3139;'>", unsafe_allow_html=True)

# ================= 📚 6. DETAILED MASTER DASHBOARD =================
ca, cb = st.columns([3, 1])
with ca: st.markdown(f"<h3 style='color:#EAECEF; margin:0;'>🔍 {st.session_state.active_coin} প্রো অ্যানালাইসিস</h3>", unsafe_allow_html=True)
with cb:
    selected = st.selectbox("📊 ম্যানুয়াল সিলেকশন", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))
    if selected != st.session_state.active_coin: change_active_coin(selected); st.rerun()

if st.session_state.active_coin in all_data and all_data[st.session_state.active_coin] is not None:
    d = all_data[st.session_state.active_coin]
    
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: st.markdown(f"<div class='metric-card' style='border-color:{'#00FF00' if d['trend_up'] else '#FF1744'}'><div class='metric-title'>১. 5m ট্রেন্ড</div><div class='metric-value'>{'আপ-ট্রেন্ড' if d['trend_up'] else 'ডাউন-ট্রেন্ড'}</div></div>", unsafe_allow_html=True)
    with mc2: st.markdown(f"<div class='metric-card' style='border-color:{'#00FF00' if d['mtf_up'] else '#FF1744'}'><div class='metric-title'>২. 15m বড় ট্রেন্ড</div><div class='metric-value'>{'আপ-ট্রেন্ড' if d['mtf_up'] else 'ডাউন-ট্রেন্ড'}</div></div>", unsafe_allow_html=True)
    with mc3: st.markdown(f"<div class='metric-card' style='border-color:{'#FF1744' if d['is_choppy'] else '#00FF00'}'><div class='metric-title'>৩. ADX + RSI ফিল্টার</div><div class='metric-value'>{'DEAD 🔴' if d['is_choppy'] else 'ACTIVE 🟢'}</div></div>", unsafe_allow_html=True)
    with mc4: st.markdown(f"<div class='metric-card' style='border-color:{d['p_color']}'><div class='metric-title'>৪. ক্যান্ডেলস্টিক</div><div class='metric-value' style='color:{d['p_color']}'>{d['p_name']}</div></div>", unsafe_allow_html=True)
    
    if d['signal'] == "DEAD MARKET":
        msg = "<b>🚨 নো-ট্রেড জোন!</b><br>RSI সাইডওয়েজ (৪৫-৫৫) অথবা ADX/Volume ডেড। ফেক সিগন্যাল ফিল্টার করা হচ্ছে।"
        st.markdown(f"<div class='reason-box' style='border-left-color: #FF1744;'>{msg}</div>", unsafe_allow_html=True)
    elif "BUY" in d['signal'] or "SELL" in d['signal']:
        st.markdown(f"<div class='reason-box' style='border-left-color: #00FF00;'><b>{d['signal']} 🚀</b><br>মার্কেট আপনার ফেভারে আছে। রুলস মেনে এন্ট্রি নিন।</div>", unsafe_allow_html=True)
    
    lc1, lc2 = st.columns(2)
    with lc1:
        st.markdown((
            "<div class='learning-box'>"
            "<b style='color:#FCD535;'>📌 বর্তমান টেকনিক্যাল নাম্বার</b><br>"
            f"🔹 RSI (Momentum): {d['rsi']:.2f}<br>"
            f"🔹 ADX (Wilder's): {d['adx']:.2f}<br>"
            f"🔹 RVOL (Relative Volume): {d['rvol']:.2f}x<br>"
            f"🔹 বাই স্কোর: {d['buy_score']}/7 | সেল স্কোর: {d['sell_score']}/7"
            "</div>"
        ), unsafe_allow_html=True)
        
    with lc2:
        st.markdown((
            "<div class='learning-box'>"
            "<b style='color:#00FF00;'>💡 মাস্টার কন্ডিশন স্ট্যাটাস</b><br>"
            f"✅ VWAP পজিশন: {'উপরে 🟢' if d['signal_price'] > d['vwap'] else 'নিচে 🔴'}<br>"
            f"✅ 5m মোমেন্টাম: {'Bullish 🟢' if d['momentum_bullish'] else 'Bearish 🔴'}<br>"
            f"✅ মার্কেট স্ট্যাটাস: {'সাইডওয়েজ 🔴' if d['is_choppy'] else 'রানিং 🟢'}<br>"
            "</div>"
        ), unsafe_allow_html=True)
