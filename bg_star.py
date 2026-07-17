import streamlit as st
import ccxt
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="TRADE MENTOR: PRO SCALPER MASTER", layout="wide", initial_sidebar_state="collapsed")
exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "5m"
SCALPING_COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

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
    div.stButton > button { border-radius: 6px !important; font-weight: bold !important; width: 100% !important; background-color: #1E2329 !important; color: #EAECEF !important; border: 1px solid #FCD535 !important;}
    div.stButton > button:hover { background-color: #FCD535 !important; color: #000000 !important;}
    </style>
""", unsafe_allow_html=True)

if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"
if 'live_mode' not in st.session_state: st.session_state.live_mode = False 
def change_active_coin(new_coin): st.session_state.active_coin = new_coin
if st.session_state.live_mode: st_autorefresh(interval=10000, limit=None, key="live_data_refresh")

def fetch_and_analyze(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=500)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=5, minutes=30)
        df_15m = df.set_index('timestamp').resample('15min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last'}).dropna()
        df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
        mtf_15m_trend_up = df_15m['close'].iloc[-1] > df_15m['ema_50'].iloc[-1]
        df['date'] = df['timestamp'].dt.date
        df['tp_v'] = ((df['high'] + df['low'] + df['close']) / 3) * df['volume']
        df['vwap'] = df.groupby('date')['tp_v'].cumsum() / df.groupby('date')['volume'].cumsum()
        support_level = df['low'].rolling(window=100).min().iloc[-1]
        resistance_level = df['high'].rolling(window=100).max().iloc[-1]
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() + 1e-10
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        rsi_live, rsi_closed = df['rsi'].iloc[-1], df['rsi'].iloc[-2]
        df['body'] = abs(df['open'] - df['close'])
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_green'] = df['close'] > df['open']
        df['is_red'] = df['close'] < df['open']
        c2, c3, c4 = df.iloc[-2], df.iloc[-3], df.iloc[-4]
        is_hammer = (c2['lower_shadow'] >= (2 * c2['body'])) and (c2['upper_shadow'] <= c2['body']) and c2['body'] > 0
        is_shooting_star = (c2['upper_shadow'] >= (2 * c2['body'])) and (c2['lower_shadow'] <= c2['body']) and c2['body'] > 0
        is_be = c3['is_red'] and c2['is_green'] and (c2['close'] >= c3['open']) and (c2['open'] <= c3['close']) and (c2['body'] > c3['body'])
        is_bere = c3['is_green'] and c2['is_red'] and (c2['close'] <= c3['open']) and (c2['open'] >= c3['close']) and (c2['body'] > c3['body'])
        c4_mid = (c4['open'] + c4['close']) / 2
        is_ms = c4['is_red'] and (c3['body'] <= (c3['high'] - c3['low']) * 0.3) and c2['is_green'] and (c2['close'] >= c4_mid)
        is_es = c4['is_green'] and (c3['body'] <= (c3['high'] - c3['low']) * 0.3) and c2['is_red'] and (c2['close'] <= c4_mid)
        bullish_pattern = is_hammer or is_be or is_ms
        bearish_pattern = is_shooting_star or is_bere or is_es
        df['is_peak'] = (df['high'].shift(2) > df['high'].shift(1)) & (df['high'].shift(2) > df['high']) & (df['high'].shift(2) > df['high'].shift(3)) & (df['high'].shift(2) > df['high'].shift(4))
        df['is_valley'] = (df['low'].shift(2) < df['low'].shift(1)) & (df['low'].shift(2) < df['low']) & (df['low'].shift(2) < df['low'].shift(3)) & (df['low'].shift(2) < df['low'].shift(4))
        df['peak_price'] = np.where(df['is_peak'], df['high'].shift(2), np.nan)
        df['valley_price'] = np.where(df['is_valley'], df['low'].shift(2), np.nan)
        recent_peaks = df.tail(60)['peak_price'].dropna().values
        recent_valleys = df.tail(60)['valley_price'].dropna().values
        is_dt = len(recent_peaks) >= 2 and abs(recent_peaks[-1] - recent_peaks[-2]) / recent_peaks[-2] < 0.003
        is_hs = len(recent_peaks) >= 3 and recent_peaks[-2] > recent_peaks[-1] and recent_peaks[-2] > recent_peaks[-3]
        is_db = len(recent_valleys) >= 2 and abs(recent_valleys[-1] - recent_valleys[-2]) / recent_valleys[-2] < 0.003
        is_ihs = len(recent_valleys) >= 3 and recent_valleys[-2] < recent_valleys[-1] and recent_valleys[-2] < recent_valleys[-3]
        artistic_buy_pattern, artistic_sell_pattern = is_db or is_ihs, is_dt or is_hs
        p_name, p_color, p_desc = "প্যাটার্ন নেই ➖", "#848E9C", "বিশেষ কোনো রিভার্সাল বা স্ট্রং প্যাটার্ন নেই।"
        if is_db: p_name, p_color, p_desc = "ডাবল বটম ✌️", "#00BFFF", "চার্টে ডাবল বটম (W) প্যাটার্ন।"
        elif is_ihs: p_name, p_color, p_desc = "ইনভার্স হেড এন্ড শোল্ডার 👤", "#00BFFF", "ইনভার্স হেড এন্ড শোল্ডার।"
        elif is_dt: p_name, p_color, p_desc = "ডাবল টপ ⛰️", "#FF00FF", "চার্টে ডাবল টপ (M) প্যাটার্ন।"
        elif is_hs: p_name, p_color, p_desc = "হেড এন্ড শোল্ডার 👤", "#FF00FF", "হেড এন্ড শোল্ডার।"
        elif is_ms: p_name, p_color, p_desc = "মর্নিং স্টার 🌅", "#00FF00", "স্ট্রং বুলিশ রিভার্সাল।"
        elif is_es: p_name, p_color, p_desc = "ইভনিং স্টার 🌃", "#FF1744", "স্ট্রং বিয়ারিশ রিভার্সাল।"
        elif is_be: p_name, p_color, p_desc = "বুলিশ এনগালফিং 📈", "#00FF00", "বায়াররা সেলারদের গিলেছে।"
        elif is_bere: p_name, p_color, p_desc = "বিয়ারিশ এনগালফিং 📉", "#FF1744", "সেলাররা বায়ারদের গিলেছে।"
        elif is_hammer: p_name, p_color, p_desc = "হ্যামার 🔨", "#00FF00", "নিচে নামার পর কড়া রিজেকশন।"
        elif is_shooting_star: p_name, p_color, p_desc = "শুটিং স্টার 🌠", "#FF1744", "উপরে ওঠার পর কড়া রিজেকশন।"
        curr_price, curr_open, curr_vol = df['close'].iloc[-1], df['open'].iloc[-1], df['volume'].iloc[-1]
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        curr_ema5, curr_ema13, curr_ema50 = df['ema_5'].iloc[-1], df['ema_13'].iloc[-1], df['ema_50'].iloc[-1]
        closed_price, closed_ema5, closed_ema13, closed_ema50 = df['close'].iloc[-2], df['ema_5'].iloc[-2], df['ema_13'].iloc[-2], df['ema_50'].iloc[-2]
        curr_vwap = df['vwap'].iloc[-1]
        buyer_vol_spike = (curr_vol > (vol_sma * 1.5)) and (curr_price > curr_open)
        seller_vol_spike = (curr_vol > (vol_sma * 1.5)) and (curr_price < curr_open)
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['prev_close']), abs(x['low'] - x['prev_close'])), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]
        is_choppy = atr < (curr_price * 0.001) 
        swing_low = df['low'].tail(15).min()
        swing_high = df['high'].tail(15).max()
        trend_up = closed_price > closed_ema50
        momentum_bullish = closed_ema5 > closed_ema13
        signal_type = "NORMAL"
        if is_choppy: signal_type = "CHOPPY MARKET"
        elif artistic_buy_pattern: signal_type = "ARTISTIC SIGNAL BUY"
        elif artistic_sell_pattern: signal_type = "ARTISTIC SIGNAL SELL"
        elif trend_up and mtf_15m_trend_up and curr_price > curr_vwap and momentum_bullish and (bullish_pattern or buyer_vol_spike) and rsi_closed < 70: signal_type = "STRONG BUY"
        elif not trend_up and not mtf_15m_trend_up and curr_price < curr_vwap and not momentum_bullish and (bearish_pattern or seller_vol_spike) and rsi_closed > 30: signal_type = "STRONG SELL"
        return {
            'price': curr_price, 'signal': signal_type, 'rsi': rsi_live, 'curr_vol': curr_vol, 'vol_sma': vol_sma,
            'ema5': curr_ema5, 'ema13': curr_ema13, 'ema50': curr_ema50, 'vwap': curr_vwap, 'mtf_up': mtf_15m_trend_up, 
            'is_choppy': is_choppy, 'support': support_level, 'resistance': resistance_level, 'p_name': p_name, 
            'p_desc': p_desc, 'p_color': p_color, 'buyer_vol_spike': buyer_vol_spike, 'seller_vol_spike': seller_vol_spike, 
            'trend_up': curr_price > curr_ema50, 'momentum_bullish': curr_ema5 > curr_ema13, 'atr': atr, 
            'swing_low': swing_low, 'swing_high': swing_high
        }
    except Exception: return None

all_data = {coin: fetch_and_analyze(coin) for coin in SCALPING_COINS if fetch_and_analyze(coin) is not None}

st.markdown("<h3 style='color:#FCD535;'>🚨 স্ক্যাল্পিং মাস্টার লাইভ রাডার (5m + 15m MTF + VWAP)</h3>", unsafe_allow_html=True)
tc1, tc2 = st.columns([1, 4])
with tc1:
    live_status = st.toggle("🔴 লাইভ স্ক্যানার অন/অফ", value=st.session_state.live_mode)
    if live_status != st.session_state.live_mode:
        st.session_state.live_mode = live_status
        st.rerun()
with tc2:
    if st.session_state.live_mode: st.markdown("<p style='color:#00FF00; font-size:14px; margin-top:8px;'>✅ লাইভ মোড অ্যাক্টিভ! অটোমেটিক ১০ সেকেন্ড পর পর আপডেট হচ্ছে।</p>", unsafe_allow_html=True)
    else: st.markdown("<p style='color:#848E9C; font-size:14px; margin-top:8px;'>⏸️ লাইভ মোড অফ করা আছে। (API বাঁচাতে ট্রেড না করলে অফ রাখুন)</p>", unsafe_allow_html=True)

active_signals = 0
for coin, data in all_data.items():
    if data['signal'] in ["STRONG BUY", "STRONG SELL", "ARTISTIC SIGNAL BUY", "ARTISTIC SIGNAL SELL"]:
        active_signals += 1
        is_buy = data['signal'] in ["STRONG BUY", "ARTISTIC SIGNAL BUY"]
        if data['signal'] == "ARTISTIC SIGNAL BUY": cc, cm, ic = "global-alert-artistic-buy", "#00BFFF", "🎨 আর্টিস্টিক বাই"
        elif data['signal'] == "ARTISTIC SIGNAL SELL": cc, cm, ic = "global-alert-artistic-sell", "#FF00FF", "🎨 আর্টিস্টিক সেল"
        elif data['signal'] == "STRONG BUY": cc, cm, ic = "global-alert-buy", "#00FF00", "🚀 STRONG BUY"
        elif data['signal'] == "STRONG SELL": cc, cm, ic = "global-alert-sell", "#FF1744", "🧨 STRONG SELL"
        
        fee_m = data['price'] * 0.002 
        sl = data['swing_low'] if (is_buy and data['swing_low'] < data['price']) else data['price'] - (data['atr'] * 1.5) if is_buy else data['swing_high'] if data['swing_high'] > data['price'] else data['price'] + (data['atr'] * 1.5)
        tp = data['price'] + ((data['price'] - sl) * 1.5) + fee_m if is_buy else data['price'] - ((sl - data['price']) * 1.5) - fee_m
        
        st.markdown(f"<div class='{cc}'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1: st.markdown(f"<h3 style='color:{cm}; margin:0;'>{ic}: {coin}</h3><div style='font-size:13px; color:#EAECEF;'>📍 এন্ট্রি: {data['price']:.4f} | 📊 VWAP: {data['vwap']:.4f}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div style='color:#00FF00; font-weight:bold; font-size:15px;'>🎯 টার্গেট: {tp:.4f}</div><div style='color:#FF1744; font-weight:bold; font-size:15px;'>🛑 স্টপ লস: {sl:.4f}</div>", unsafe_allow_html=True)
        with c3: st.button(f"🔍 চার্ট দেখুন", key=f"btn_{coin}", on_click=change_active_coin, args=(coin,))
        st.markdown("</div>", unsafe_allow_html=True)

if active_signals == 0: st.markdown("<div class='global-alert-normal'>⏳ বর্তমানে কোনো কয়েনে সিগন্যাল নেই। মাস্টার বট মার্কেট ফিল্টার করছে...</div>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#2B3139;'>", unsafe_allow_html=True)

ca, cb = st.columns([3, 1])
with ca: st.markdown(f"<h3 style='color:#EAECEF; margin:0;'>🔍 {st.session_state.active_coin} প্রো অ্যানালাইসিস</h3>", unsafe_allow_html=True)
with cb:
    selected = st.selectbox("📊 ম্যানুয়াল সিলেকশন", SCALPING_COINS, index=SCALPING_COINS.index(st.session_state.active_coin))
    if selected != st.session_state.active_coin:
        change_active_coin(selected)
        st.rerun()

if st.session_state.active_coin in all_data:
    d = all_data[st.session_state.active_coin]
    mc1, mc2, mc3, mc4 = st.columns(4)
    tv, tc = ("আপ-ট্রেন্ড", "#00FF00") if d['trend_up'] else ("ডাউন-ট্রেন্ড", "#FF1744")
    with mc1: st.markdown(f"<div class='metric-card' style='border-color:{tc}'><div class='metric-title'>১. 5m ট্রেন্ড</div><div class='metric-value' style='color:{tc}'>{tv}</div></div>", unsafe_allow_html=True)
    mtv, mtc = ("আপ-ট্রেন্ড", "#00FF00") if d['mtf_up'] else ("ডাউন-ট্রেন্ড", "#FF1744")
    with mc2: st.markdown(f"<div class='metric-card' style='border-color:{mtc}'><div class='metric-title'>২. 15m বড় ট্রেন্ড</div><div class='metric-value' style='color:{mtc}'>{mtv}</div></div>", unsafe_allow_html=True)
    vv, vc = ("VWAP এর উপরে 🟢", "#00FF00") if d['price'] > d['vwap'] else ("VWAP এর নিচে 🔴", "#FF1744")
    with mc3: st.markdown(f"<div class='metric-card' style='border-color:{vc}'><div class='metric-title'>৩. VWAP</div><div class='metric-value' style='color:{vc}'>{vv}</div></div>", unsafe_allow_html=True)
    with mc4: st.markdown(f"<div class='metric-card' style='border-color:{d['p_color']}'><div class='metric-title'>৪. স্ক্যানার</div><div class='metric-value' style='color:{d['p_color']}'>{d['p_name']}</div></div>", unsafe_allow_html=True)
    
    mc5, mc6, mc7, mc8 = st.columns(4)
    mv, mc_c = ("বায়াররা স্ট্রং 🟢", "#00FF00") if d['momentum_bullish'] else ("সেলাররা স্ট্রং 🔴", "#FF1744")
    with mc5: st.markdown(f"<div class='metric-card' style='border-color:{mc_c}'><div class='metric-title'>৫. মোমেন্টাম</div><div class='metric-value' style='color:{mc_c}'>{mv}</div></div>", unsafe_allow_html=True)
    with mc6: st.markdown(f"<div class='metric-card' style='border-color:#00BFFF'><div class='metric-title'>৬. সাপোর্ট</div><div class='metric-value' style='color:#00BFFF'>{d['support']:.4f}</div></div>", unsafe_allow_html=True)
    with mc7: st.markdown(f"<div class='metric-card' style='border-color:#FF00FF'><div class='metric-title'>৭. রেজিস্ট্যান্স</div><div class='metric-value' style='color:#FF00FF'>{d['resistance']:.4f}</div></div>", unsafe_allow_html=True)
    ch_v, ch_c = ("ডেড মার্কেট 😴", "#848E9C") if d['is_choppy'] else ("মার্কেট রানিং ⚡", "#FCD535")
    with mc8: st.markdown(f"<div class='metric-card' style='border-color:{ch_c}'><div class='metric-title'>৮. কন্ডিশন</div><div class='metric-value' style='color:{ch_c}'>{ch_v}</div></div>", unsafe_allow_html=True)

    st.markdown(f"<h4 style='color:#FCD535; margin-top:15px; border-bottom: 1px solid #2B3139; padding-bottom:10px;'>💡 {st.session_state.active_coin} মাস্টার ব্রেকডাউন</h4>", unsafe_allow_html=True)
    
    if d['signal'] == "CHOPPY MARKET":
        st.markdown("""<div class='reason-box' style='border-left-color: #848E9C;'><b>মার্কেট ডেড!</b><br>স্ক্যাল্পিংয়ের জন্য এন্ট্রি নিলে লস হওয়ার চান্স বেশি। ভলিউম আসার অপেক্ষা করুন।</div>""", unsafe_allow_html=True)
    elif d['signal'] == "ARTISTIC SIGNAL BUY":
        st.markdown(f"""<div class='reason-box' style='border-left-color: #00BFFF;'><b>ARTISTIC BUY কেন আসলো?</b><br>চার্টে <b>{d['p_name']}</b> প্যাটার্ন তৈরি হয়েছে। এটি অনেক নির্ভরযোগ্য।</div>""", unsafe_allow_html=True)
    elif d['signal'] == "ARTISTIC SIGNAL SELL":
        st.markdown(f"""<div class='reason-box' style='border-left-color: #FF00FF;'><b>ARTISTIC SELL কেন আসলো?</b><br>চার্টে <b>{d['p_name']}</b> প্যাটার্ন তৈরি হয়েছে। এটি অনেক নির্ভরযোগ্য।</div>""", unsafe_allow_html=True)
    elif d['signal'] == "STRONG BUY":
        st.markdown("""<div class='reason-box'><b>STRONG BUY সিগন্যাল কেন?</b><br>MTF আপ, প্রাইস VWAP এর উপরে, 5m আপ-ট্রেন্ড এবং মোমেন্টাম বুলিশ। ফী হিসাব করে টার্গেট দেওয়া হয়েছে।</div>""", unsafe_allow_html=True)
    elif d['signal'] == "STRONG SELL":
        st.markdown("""<div class='reason-box'><b>STRONG SELL সিগন্যাল কেন?</b><br>MTF ডাউন, প্রাইস VWAP এর নিচে, 5m ডাউন-ট্রেন্ড এবং মোমেন্টাম বিয়ারিশ। ফী হিসাব করে টার্গেট দেওয়া হয়েছে।</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class='reason-box' style='border-left-color: #848E9C;'><b>{st.session_state.active_coin} এ কোনো সিগন্যাল নেই।</b><br>সবগুলো কন্ডিশন একসাথে না মিললে স্ক্যাল্পিংয়ে এন্ট্রি নেওয়া রিস্কি।</div>""", unsafe_allow_html=True)

    st.markdown(f"<h4 style='color:#00BFFF; margin-top:20px;'>📊 লাইভ প্যারামিটার ও ড্যাশবোর্ড</h4>", unsafe_allow_html=True)
    lc1, lc2 = st.columns(2)
    with lc1:
        st.markdown(f"""
        <div class='learning-box'>
        <b style='color:#FCD535;'>📌 বর্তমান টেকনিক্যাল নাম্বার</b><br>
        🔹 বর্তমান প্রাইস: {d['price']:.4f}<br>
        🔹 VWAP: {d['vwap']:.4f}<br>
        🔹 EMA 50: {d['ema50']:.4f}<br>
        🔹 RSI (14): {d['rsi']:.2f}<br>
        🔹 ভলাটিলিটি (ATR): {d['atr']:.4f}
        </div>
        """, unsafe_allow_html=True)
    with lc2:
        mtf_status = 'বুলিশ 🟢' if d['mtf_up'] else 'বিয়ারিশ 🔴'
        vwap_status = 'উপরে 🟢' if d['price'] > d['vwap'] else 'নিচে 🔴'
        mom_status = 'Bullish 🟢' if d['momentum_bullish'] else 'Bearish 🔴'
        chop_status = 'ডেড 🔴' if d['is_choppy'] else 'ভলিউম আছে 🟢'
        st.markdown(f"""
        <div class='learning-box'>
        <b style='color:#00FF00;'>💡 মাস্টার কন্ডিশন স্ট্যাটাস</b><br>
        ✅ MTF 15m ট্রেন্ড: {mtf_status}<br>
        ✅ VWAP লজিক: {vwap_status}<br>
        ✅ 5m মোমেন্টাম: {mom_status}<br>
        ✅ মার্কেট অবস্থা: {chop_status}<br>
        ✅ প্যাটার্ন: {d['p_name']}
        </div>
        """, unsafe_allow_html=True)
