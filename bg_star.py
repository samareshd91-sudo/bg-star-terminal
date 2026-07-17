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
    .global-alert-artistic-buy { background: linear-gradient(90deg, rgba(0,191,255,0.1) 0%, #181A20 100%); border-left: 5px solid #00BFFF; padding: 15px; border-radius: 8px; margin-bottom: 10px;}
    .global-alert-artistic-sell { background: linear-gradient(90deg, rgba(255,0,255,0.1) 0%, #181A20 100%); border-left: 5px solid #FF00FF; padding: 15px; border-radius: 8px; margin-bottom: 10px;}
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

# ================= ⚡ 4. HARDCORE CORE ENGINE =================
def fetch_and_analyze(coin):
    try:
        # MTF
        bars_15m = exchange.fetch_ohlcv(coin, timeframe='15m', limit=100)
        df_15m = pd.DataFrame(bars_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
        mtf_15m_trend_up = df_15m['close'].iloc[-1] > df_15m['ema_50'].iloc[-1]

        # 5m
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=500)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # VWAP
        df['utc_date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        df['tp_v'] = ((df['high'] + df['low'] + df['close']) / 3) * df['volume']
        df['vwap'] = df.groupby('utc_date')['tp_v'].cumsum() / df.groupby('utc_date')['volume'].cumsum()
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        
        recent_100_vol = df.tail(100)
        top_5_vol_candles = recent_100_vol.nlargest(5, 'volume')
        support_level = top_5_vol_candles['low'].min()
        resistance_level = top_5_vol_candles['high'].max()

        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        rsi_live = df['rsi'].iloc[-1]
        rsi_closed = df['rsi'].iloc[-2] 
        
        df['body'] = abs(df['open'] - df['close'])
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_green'] = df['close'] > df['open']
        df['is_red'] = df['close'] < df['open']
        
        c2 = df.iloc[-2]
        c3 = df.iloc[-3]
        c4 = df.iloc[-4]
        
        is_hammer = (c2['lower_shadow'] >= (2 * c2['body'])) and (c2['upper_shadow'] <= c2['body']) and (c2['body'] > 0)
        is_shooting_star = (c2['upper_shadow'] >= (2 * c2['body'])) and (c2['lower_shadow'] <= c2['body']) and (c2['body'] > 0)
        
        is_be = c3['is_red'] and c2['is_green'] and (c2['close'] >= c3['open']) and (c2['open'] <= c3['close']) and (c2['body'] > c3['body'])
        is_bere = c3['is_green'] and c2['is_red'] and (c2['close'] <= c3['open']) and (c2['open'] >= c3['close']) and (c2['body'] > c3['body'])
        
        c4_mid = (c4['open'] + c4['close']) / 2
        is_ms = c4['is_red'] and (c3['body'] <= (c3['high'] - c3['low']) * 0.3) and c2['is_green'] and (c2['close'] >= c4_mid)
        is_es = c4['is_green'] and (c3['body'] <= (c3['high'] - c3['low']) * 0.3) and c2['is_red'] and (c2['close'] <= c4_mid)

        bullish_pattern = is_hammer or is_be or is_ms
        bearish_pattern = is_shooting_star or is_bere or is_es

        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(
            lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), 
            axis=1
        )
        atr = df['tr'].rolling(14).mean().iloc[-1]

        # 📌 Broken down long lines for mobile safety
        df['is_peak'] = (
            (df['high'].shift(2) > df['high'].shift(1)) & 
            (df['high'].shift(2) > df['high']) & 
            (df['high'].shift(2) > df['high'].shift(3)) & 
            (df['high'].shift(2) > df['high'].shift(4))
        )
        
        df['is_valley'] = (
            (df['low'].shift(2) < df['low'].shift(1)) & 
            (df['low'].shift(2) < df['low']) & 
            (df['low'].shift(2) < df['low'].shift(3)) & 
            (df['low'].shift(2) < df['low'].shift(4))
        )
        
        df['peak_price'] = np.where(df['is_peak'], df['high'].shift(2), np.nan)
        df['valley_price'] = np.where(df['is_valley'], df['low'].shift(2), np.nan)
        
        recent_peaks_s = df['peak_price'].tail(60).dropna()
        recent_valleys_s = df['valley_price'].tail(60).dropna()
        
        curr_idx = df.index[-1]
        is_dt = False
        is_hs = False
        is_db = False
        is_ihs = False
        
        dyn_tol = atr * 0.5

        if len(recent_peaks_s) >= 2:
            last_peak_idx = recent_peaks_s.index[-1]
            recent_peaks = recent_peaks_s.values
            if (curr_idx - last_peak_idx) <= 5:
                if abs(recent_peaks[-1] - recent_peaks[-2]) <= dyn_tol:
                    is_dt = True
                if len(recent_peaks) >= 3:
                    if (recent_peaks[-2] > recent_peaks[-1]) and (recent_peaks[-2] > recent_peaks[-3]):
                        is_hs = True

        if len(recent_valleys_s) >= 2:
            last_valley_idx = recent_valleys_s.index[-1]
            recent_valleys = recent_valleys_s.values
            if (curr_idx - last_valley_idx) <= 5:
                if abs(recent_valleys[-1] - recent_valleys[-2]) <= dyn_tol:
                    is_db = True
                if len(recent_valleys) >= 3:
                    if (recent_valleys[-2] < recent_valleys[-1]) and (recent_valleys[-2] < recent_valleys[-3]):
                        is_ihs = True

        artistic_buy_pattern = False
        if is_db or is_ihs:
            artistic_buy_pattern = True
            
        artistic_sell_pattern = False
        if is_dt or is_hs:
            artistic_sell_pattern = True

        p_name = "প্যাটার্ন নেই ➖"
        p_color = "#848E9C"
        
        if is_db: p_name, p_color = "ডাবল বটম ✌️", "#00BFFF"
        elif is_ihs: p_name, p_color = "ইনভার্স হেড এন্ড শোল্ডার 👤", "#00BFFF"
        elif is_dt: p_name, p_color = "ডাবল টপ ⛰️", "#FF00FF"
        elif is_hs: p_name, p_color = "হেড এন্ড শোল্ডার 👤", "#FF00FF"
        elif is_ms: p_name, p_color = "মর্নিং স্টার 🌅", "#00FF00"
        elif is_es: p_name, p_color = "ইভনিং স্টার 🌃", "#FF1744"
        elif is_be: p_name, p_color = "বুলিশ এনগালফিং 📈", "#00FF00"
        elif is_bere: p_name, p_color = "বিয়ারিশ এনগালফিং 📉", "#FF1744"
        elif is_hammer: p_name, p_color = "হ্যামার 🔨", "#00FF00"
        elif is_shooting_star: p_name, p_color = "শুটিং স্টার 🌠", "#FF1744"

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
        
        buyer_vol_spike = False
        seller_vol_spike = False
        if curr_vol > (vol_sma * 1.5):
            if curr_price > curr_open: buyer_vol_spike = True
            elif curr_price < curr_open: seller_vol_spike = True
                
        is_choppy = atr < (curr_price * 0.001) 
        swing_low = df['low'].tail(15).min()
        swing_high = df['high'].tail(15).max()
        
        trend_up = closed_price > closed_ema50
        momentum_bullish = closed_ema5 > closed_ema13
        
        signal_type = "NORMAL"
        if is_choppy:
            signal_type = "CHOPPY MARKET"
        elif artistic_buy_pattern:
            signal_type = "ARTISTIC SIGNAL BUY"
        elif artistic_sell_pattern:
            signal_type = "ARTISTIC SIGNAL SELL"
        elif trend_up and mtf_15m_trend_up and (curr_price > curr_vwap) and momentum_bullish and (bullish_pattern or buyer_vol_spike) and (rsi_closed < 70):
            signal_type = "STRONG BUY"
        elif not trend_up and not mtf_15m_trend_up and (curr_price < curr_vwap) and not momentum_bullish and (bearish_pattern or seller_vol_spike) and (rsi_closed > 30):
            signal_type = "STRONG SELL"
            
        return {
            'price': curr_price, 'signal': signal_type, 'rsi': rsi_live, 'curr_vol': curr_vol, 'vol_sma': vol_sma,
            'ema5': curr_ema5, 'ema13': curr_ema13, 'ema50': curr_ema50, 'vwap': curr_vwap, 'mtf_up': mtf_15m_trend_up, 
            'is_choppy': is_choppy, 'support': support_level, 'resistance': resistance_level, 'p_name': p_name, 
            'p_color': p_color, 'buyer_vol_spike': buyer_vol_spike, 'seller_vol_spike': seller_vol_spike, 
            'trend_up': trend_up, 'momentum_bullish': momentum_bullish, 'atr': atr, 
            'swing_low': swing_low, 'swing_high': swing_high
        }
    except Exception:
        return None

all_data = {}
for coin in SCALPING_COINS:
    res = fetch_and_analyze(coin)
    if res is not None:
        all_data[coin] = res

# ================= 🚨 5. GLOBAL SIGNAL RADAR UI =================
st.markdown("<h3 style='color:#FCD535;'>🚨 স্ক্যাল্পিং মাস্টার লাইভ রাডার (5m)</h3>", unsafe_allow_html=True)

tc1, tc2 = st.columns([1, 4])
with tc1:
    live_status = st.toggle("🔴 লাইভ স্ক্যানার অন/অফ", value=st.session_state.live_mode)
    if live_status != st.session_state.live_mode:
        st.session_state.live_mode = live_status
        st.rerun()
with tc2:
    if st.session_state.live_mode:
        msg = "<p style='color:#00FF00; font-size:14px; margin-top:8px;'>✅ লাইভ মোড অ্যাক্টিভ! অটোমেটিক ১০ সেকেন্ড পর পর আপডেট হচ্ছে।</p>"
        st.markdown(msg, unsafe_allow_html=True)
    else:
        msg = "<p style='color:#848E9C; font-size:14px; margin-top:8px;'>⏸️ লাইভ মোড অফ করা আছে। (API বাঁচাতে ট্রেড না করলে অফ রাখুন)</p>"
        st.markdown(msg, unsafe_allow_html=True)

active_signals = 0
for coin, data in all_data.items():
    if data['signal'] in ["STRONG BUY", "STRONG SELL", "ARTISTIC SIGNAL BUY", "ARTISTIC SIGNAL SELL"]:
        active_signals += 1
        is_buy = False
        
        if data['signal'] == "ARTISTIC SIGNAL BUY":
            cc, cm, ic, is_buy = "global-alert-artistic-buy", "#00BFFF", "🎨 আর্টিস্টিক বাই", True
        elif data['signal'] == "ARTISTIC SIGNAL SELL":
            cc, cm, ic = "global-alert-artistic-sell", "#FF00FF", "🎨 আর্টিস্টিক সেল"
        elif data['signal'] == "STRONG BUY":
            cc, cm, ic, is_buy = "global-alert-buy", "#00FF00", "🚀 STRONG BUY", True
        elif data['signal'] == "STRONG SELL":
            cc, cm, ic = "global-alert-sell", "#FF1744", "🧨 STRONG SELL"
        
        fee_m = data['price'] * 0.002 
        
        if is_buy:
            if data['swing_low'] < data['price']: sl = data['swing_low']
            else: sl = data['price'] - (data['atr'] * 1.5)
            tp = data['price'] + ((data['price'] - sl) * 1.5) + fee_m
        else:
            if data['swing_high'] > data['price']: sl = data['swing_high']
            else: sl = data['price'] + (data['atr'] * 1.5)
            tp = data['price'] - ((sl - data['price']) * 1.5) - fee_m
        
        html_card = (
            f"<div class='{cc}'>"
            f"<h3 style='color:{cm}; margin:0 0 10px 0;'>{ic}: {coin}</h3>"
            f"<div style='display: flex; justify-content: space-between; flex-wrap: wrap; margin-bottom: 8px;'>"
            f"<span style='font-size:14px; color:#EAECEF;'>📍 এন্ট্রি: <b>{data['price']:.4f}</b></span>"
            f"<span style='font-size:14px; color:#EAECEF;'>📊 VWAP: <b>{data['vwap']:.4f}</b></span>"
            f"</div>"
            f"<div style='display: flex; justify-content: space-between; flex-wrap: wrap;'>"
            f"<span style='color:#00FF00; font-weight:bold; font-size:15px;'>🎯 টার্গেট: {tp:.4f}</span>"
            f"<span style='color:#FF1744; font-weight:bold; font-size:15px;'>🛑 SL: {sl:.4f}</span>"
            f"</div>"
            f"</div>"
        )
        st.markdown(html_card, unsafe_allow_html=True)
        st.button(f"🔍 {coin} চার্ট দেখুন", key=f"btn_{coin}", on_click=change_active_coin, args=(coin,))

if active_signals == 0:
    msg = "<div class='global-alert-normal'>⏳ বর্তমানে কোনো কয়েনে সিগন্যাল নেই। মাস্টার বট মার্কেট ফিল্টার করছে...</div>"
    st.markdown(msg, unsafe_allow_html=True)
    
st.markdown("<hr style='border-color:#2B3139;'>", unsafe_allow_html=True)

# ================= 📚 6. DETAILED MASTER DASHBOARD =================
ca, cb = st.columns([3, 1])
with ca:
    title_msg = f"<h3 style='color:#EAECEF; margin:0;'>🔍 {st.session_state.active_coin} প্রো অ্যানালাইসিস</h3>"
    st.markdown(title_msg, unsafe_allow_html=True)
with cb:
    selected = st.selectbox(
        "📊 ম্যানুয়াল সিলেকশন", 
        SCALPING_COINS, 
        index=SCALPING_COINS.index(st.session_state.active_coin)
    )
    if selected != st.session_state.active_coin:
        change_active_coin(selected)
        st.rerun()

if st.session_state.active_coin in all_data:
    d = all_data[st.session_state.active_coin]
    
    mc1, mc2, mc3, mc4 = st.columns(4)
    if d['trend_up']: tv, tc = "আপ-ট্রেন্ড", "#00FF00"
    else: tv, tc = "ডাউন-ট্রেন্ড", "#FF1744"
    with mc1:
        msg1 = f"<div class='metric-card' style='border-color:{tc}'><div class='metric-title'>১. 5m ট্রেন্ড</div><div class='metric-value' style='color:{tc}'>{tv}</div></div>"
        st.markdown(msg1, unsafe_allow_html=True)
    
    if d['mtf_up']: mtv, mtc = "আপ-ট্রেন্ড", "#00FF00"
    else: mtv, mtc = "ডাউন-ট্রেন্ড", "#FF1744"
    with mc2:
        msg2 = f"<div class='metric-card' style='border-color:{mtc}'><div class='metric-title'>২. 15m বড় ট্রেন্ড</div><div class='metric-value' style='color:{mtc}'>{mtv}</div></div>"
        st.markdown(msg2, unsafe_allow_html=True)
    
    if d['price'] > d['vwap']: vv, vc = "VWAP এর উপরে 🟢", "#00FF00"
    else: vv, vc = "VWAP এর নিচে 🔴", "#FF1744"
    with mc3:
        msg3 = f"<div class='metric-card' style='border-color:{vc}'><div class='metric-title'>৩. VWAP</div><div class='metric-value' style='color:{vc}'>{vv}</div></div>"
        st.markdown(msg3, unsafe_allow_html=True)
    
    with mc4:
        msg4 = f"<div class='metric-card' style='border-color:{d['p_color']}'><div class='metric-title'>৪. স্ক্যানার</div><div class='metric-value' style='color:{d['p_color']}'>{d['p_name']}</div></div>"
        st.markdown(msg4, unsafe_allow_html=True)
    
    mc5, mc6, mc7, mc8 = st.columns(4)
    if d['momentum_bullish']: mv, mc_c = "বায়াররা স্ট্রং 🟢", "#00FF00"
    else: mv, mc_c = "সেলাররা স্ট্রং 🔴", "#FF1744"
    with mc5:
        msg5 = f"<div class='metric-card' style='border-color:{mc_c}'><div class='metric-title'>৫. মোমেন্টাম</div><div class='metric-value' style='color:{mc_c}'>{mv}</div></div>"
        st.markdown(msg5, unsafe_allow_html=True)
    
    with mc6:
        msg6 = f"<div class='metric-card' style='border-color:#00BFFF'><div class='metric-title'>৬. রিয়েল সাপোর্ট</div><div class='metric-value' style='color:#00BFFF'>{d['support']:.4f}</div></div>"
        st.markdown(msg6, unsafe_allow_html=True)
    
    with mc7:
        msg7 = f"<div class='metric-card' style='border-color:#FF00FF'><div class='metric-title'>৭. রিয়েল রেজিস্ট্যান্স</div><div class='metric-value' style='color:#FF00FF'>{d['resistance']:.4f}</div></div>"
        st.markdown(msg7, unsafe_allow_html=True)
    
    if d['is_choppy']: ch_v, ch_c = "ডেড মার্কেট 😴", "#848E9C"
    else: ch_v, ch_c = "মার্কেট রানিং ⚡", "#FCD535"
    with mc8:
        msg8 = f"<div class='metric-card' style='border-color:{ch_c}'><div class='metric-title'>৮. কন্ডিশন</div><div class='metric-value' style='color:{ch_c}'>{ch_v}</div></div>"
        st.markdown(msg8, unsafe_allow_html=True)

    header_msg = f"<h4 style='color:#FCD535; margin-top:15px; border-bottom: 1px solid #2B3139; padding-bottom:10px;'>💡 {st.session_state.active_coin} মাস্টার ব্রেকডাউন</h4>"
    st.markdown(header_msg, unsafe_allow_html=True)
    
    # 📌 Safely broken down Reason Boxes
    if d['signal'] == "CHOPPY MARKET":
        r_msg = (
            "<div class='reason-box' style='border-left-color: #848E9C;'>"
            "<b>মার্কেট ডেড!</b><br>"
            "স্ক্যাল্পিংয়ের জন্য এন্ট্রি নিলে লস হওয়ার চান্স বেশি। ভলিউম আসার অপেক্ষা করুন।"
            "</div>"
        )
        st.markdown(r_msg, unsafe_allow_html=True)
        
    elif d['signal'] == "ARTISTIC SIGNAL BUY":
        r_msg = (
            f"<div class='reason-box' style='border-left-color: #00BFFF;'>"
            f"<b>ARTISTIC BUY কেন আসলো?</b><br>"
            f"চার্টে <b>{d['p_name']}</b> তৈরি হয়েছে যা একটি শক্তিশালী বুলিশ রিভার্সাল প্যাটার্ন। "
            f"সাপোর্ট লেভেল ({d['support']:.4f}) থেকে মার্কেট বাউন্স করার সম্ভাবনা রয়েছে।"
            f"</div>"
        )
        st.markdown(r_msg, unsafe_allow_html=True)

    elif d['signal'] == "ARTISTIC SIGNAL SELL":
        r_msg = (
            f"<div class='reason-box' style='border-left-color: #FF00FF;'>"
            f"<b>ARTISTIC SELL কেন আসলো?</b><br>"
            f"চার্টে <b>{d['p_name']}</b> তৈরি হয়েছে যা একটি শক্তিশালী বিয়ারিশ রিভার্সাল প্যাটার্ন। "
            f"রেজিস্ট্যান্স লেভেল ({d['resistance']:.4f}) থেকে মার্কেট রিজেকশন পাচ্ছে।"
            f"</div>"
        )
        st.markdown(r_msg, unsafe_allow_html=True)

    elif d['signal'] == "STRONG BUY":
        r_msg = (
            f"<div class='reason-box' style='border-left-color: #00FF00;'>"
            f"<b>STRONG BUY কেন আসলো?</b><br>"
            f"১. প্রাইস 15m এবং 5m উভয় টাইমফ্রেমে আপ-ট্রেন্ডে আছে।<br>"
            f"২. প্রাইস VWAP ({d['vwap']:.4f}) এর উপরে অবস্থান করছে।<br>"
            f"৩. মোমেন্টাম স্ট্রং (EMA5 > EMA13)।<br>"
            f"৪. <b>{d['p_name']}</b> প্যাটার্ন অথবা বায়ার ভলিউম স্পাইক কনফার্মেশন দিয়েছে।"
            f"</div>"
        )
        st.markdown(r_msg, unsafe_allow_html=True)

    elif d['signal'] == "STRONG SELL":
        r_msg = (
            f"<div class='reason-box' style='border-left-color: #FF1744;'>"
            f"<b>STRONG SELL কেন আসলো?</b><br>"
            f"১. প্রাইস 15m এবং 5m উভয় টাইমফ্রেমে ডাউন-ট্রেন্ডে আছে।<br>"
            f"২. প্রাইস VWAP ({d['vwap']:.4f}) এর নিচে অবস্থান করছে।<br>"
            f"৩. মোমেন্টাম দুর্বল (EMA5 < EMA13)।<br>"
            f"৪. <b>{d['p_name']}</b> প্যাটার্ন অথবা সেলার ভলিউম স্পাইক কনফার্মেশন দিয়েছে।"
            f"</div>"
        )
        st.markdown(r_msg, unsafe_allow_html=True)

    else:
        r_msg = (
            "<div class='reason-box' style='border-left-color: #848E9C;'>"
            "<b>বর্তমান পরিস্থিতি:</b><br>"
            "এখনো কোনো স্ট্রং সিগন্যাল তৈরি হয়নি। স্ক্যাল্পিংয়ের জন্য একটি পারফেক্ট সেটআপের অপেক্ষা করুন।"
            "</div>"
        )
        st.markdown(r_msg, unsafe_allow_html=True)

    # ================= 📖 7. LEARNING & RULES SECTION =================
    learning_msg = (
        "<div class='learning-box'>"
        "<h4 style='margin-top:0; color:#FCD535;'>💡 প্রো ট্রেডিং টিপস:</h4>"
        "<ul>"
        "<li><b>স্টপ-লস (SL):</b> কখনোই স্টপ-লস ছাড়া স্ক্যাল্পিং করবেন না। মার্কেট যেকোনো সময় রিভার্স করতে পারে।</li>"
        "<li><b>রিস্ক ম্যানেজমেন্ট:</b> এক ট্রেডে পোর্টফোলিও-র ২-৩% এর বেশি রিস্ক নেবেন না।</li>"
        "<li><b>রিওয়ার্ড রেশিও:</b> সব সময় ১:১.৫ বা তার বেশি টার্গেট (TP) মেইনটেইন করার চেষ্টা করুন।</li>"
        "<li><b>ইমোশনাল কন্ট্রোল:</b> সিগন্যাল মিস হলে তাড়াহুড়ো করে রানিং ক্যান্ডেলে এন্ট্রি নেবেন না।</li>"
        "</ul>"
        "</div>"
    )
    st.markdown(learning_msg, unsafe_allow_html=True)
