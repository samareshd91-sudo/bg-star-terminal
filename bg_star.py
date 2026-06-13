import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time 

st.set_page_config(page_title="BG STAR V6 PRO", layout="wide")

# হিজিবিজি মুক্ত একদম পরিষ্কার ও রেসপন্সিভ ডিজাইন
st.markdown("""
    <style>
    html, body, #root, .stApp, [data-testid="stAppViewContainer"], .main {
        overscroll-behavior: none !important;
        overscroll-behavior-y: none !important;
    }
    .stMetric { background-color: #1E1E2E; padding: 15px; border-radius: 12px; border: 1px solid #333; border-left: 4px solid #f39c12; }
    .signal-box { background-color: #1E1E2E; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; border: 1px solid #333;}
    .buy-box { border-bottom: 5px solid #00E676; box-shadow: 0px 4px 15px rgba(0, 230, 118, 0.15); }
    .sell-box { border-bottom: 5px solid #FF1744; box-shadow: 0px 4px 15px rgba(255, 23, 68, 0.15); }
    .wait-box { border-bottom: 5px solid #888888; }
    </style>
""", unsafe_allow_html=True)

coin = "BTC/USDT"

st.sidebar.title("⚙️ BG STAR Control")
st.sidebar.write("🤖 শুধুমাত্র BTC/USDT-এ স্নাইপার অ্যানালাইসিস চলছে!")
selected_tf = st.sidebar.selectbox("Timeframe", ["5m", "15m", "1h", "4h", "1d"], index=1)
auto_refresh = st.sidebar.checkbox("🟢 Auto-Refresh (Live 15s)", value=True)

st.title(f"🎯 BG STAR V6 PRO (Ultimate Sniper)")

# ক্র্যাশ প্রোটেকশন চালু করা হলো
exchange = ccxt.kucoin({'enableRateLimit': True})
play_sound = False

# সিগন্যাল বক্সটি স্ক্রিনের মাঝে রাখার জন্য লেআউট
col1, col2, col3 = st.columns([1, 2, 1])

try:
    # ছোট টাইমফ্রেম (এন্ট্রির জন্য)
    bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=150)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # বড় টাইমফ্রেম (৪ ঘণ্টা - ট্রেন্ড কনফার্মেশনের জন্য - 250 লিমিট ফিক্সড)
    bars_4h = exchange.fetch_ohlcv(coin, timeframe='4h', limit=250)
    df_4h = pd.DataFrame(bars_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_4h['ema_200'] = df_4h['close'].ewm(span=200, adjust=False).mean()
    trend_4h = "BULLISH" if df_4h['close'].iloc[-1] > df_4h['ema_200'].iloc[-1] else "BEARISH"
    
    # ইন্ডিকেটর - RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ইন্ডিকেটর - MACD
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['vol_sma'] = df['volume'].rolling(20).mean() 
    
    # স্মার্ট মানি কনসেপ্ট (SMC) - লেটেস্ট লিকুইডিটি জোন (শেষ ৫০ ক্যান্ডেল)
    support = df['low'].tail(50).min()
    resistance = df['high'].tail(50).max()
    
    curr_price = df['close'].iloc[-1]
    curr_vol = df['volume'].iloc[-1]
    curr_rsi = df['rsi'].iloc[-1]
    vol_sma = df['vol_sma'].iloc[-1]
    curr_macd = df['macd'].iloc[-1]
    curr_macd_sig = df['macd_signal'].iloc[-1]
    risk_reward_gap = resistance - support
    
    macd_bullish = curr_macd > curr_macd_sig
    
    buy_zone = support + (risk_reward_gap * 0.15)
    sell_zone = resistance - (risk_reward_gap * 0.15)
    
    signal_text = "⚪ WAIT"
    box_class = "wait-box"
    price_color = "#f39c12"
    
    is_volume_high = curr_vol > vol_sma  
    
    # প্রো-স্নাইপার লজিক (MACD এবং RSI একসাথে)
    if curr_price <= buy_zone and trend_4h == "BULLISH" and is_volume_high and curr_rsi < 45 and macd_bullish:
        signal_text = "🟢 SNIPER BUY"
        box_class = "buy-box"
        price_color = "#00E676"
        play_sound = True
        
    elif curr_price >= sell_zone and trend_4h == "BEARISH" and is_volume_high and curr_rsi > 55 and not macd_bullish:
        signal_text = "🔴 SNIPER SELL"
        box_class = "sell-box"
        price_color = "#FF1744"
        play_sound = True
        
    with col2:
        st.markdown(f'<div class="signal-box {box_class}"><b>{coin}</b><br><span style="font-size:32px; font-weight:bold; color:{price_color};">${curr_price:.2f}</span><br><span style="font-size:18px; font-weight:bold;">{signal_text}</span></div>', unsafe_allow_html=True)

    if play_sound:
        st.toast("🔔 SNIPER SIGNAL DETECTED!", icon="🔔")
        st.markdown('<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>', unsafe_allow_html=True)

    st.markdown("---")

    # ৪টি প্রধান মেট্রিকস
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Live Price", f"${curr_price:.2f}")
    m2.metric("4H Big Trend", trend_4h)
    m3.metric("Smart Support Zone", f"${support:.2f}")
    m4.metric("Smart Resistance", f"${resistance:.2f}")

    # 📊 ক্যান্ডেলস্টিক চার্ট
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], name='EMA 200', line=dict(color='orange', width=2)), row=1, col=1)
    fig.add_hline(y=support, line_dash="dash", line_color="#00ff00", row=1, col=1)
    fig.add_hline(y=resistance, line_dash="dash", line_color="#ff0000", row=1, col=1)
    colors = ['#00ff00' if close >= open else '#ff0000' for open, close in zip(df['open'], df['close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 📥 বিস্তারিত এনালাইসিস প্যানেল (লুকানো)
    with st.expander("🔍 এখানে টিপুন: বিস্তারিত AI এবং SMC ব্যাকগ্রাউন্ড রিপোর্ট"):
        st.markdown("### 🧠 BG STAR Ultimate Sniper Engine")
        smc_analysis = []
        smc_analysis.append(f"**বড় ট্রেন্ড (4h):** {trend_4h}।")
        
        macd_status = "BULLISH 🟢" if macd_bullish else "BEARISH 🔴"
        smc_analysis.append(f"**MACD ট্রেন্ড:** {macd_status}।")

        if is_volume_high:
            smc_analysis.append("**ভলিউম:** মার্কেটে এখন বড় ট্রেডারদের টাকা ঢুকছে (High Volume)।")
        else:
            smc_analysis.append("**ভলিউম:** মার্কেটে এখন ভলিউম কম (Retailers Trap হতে পারে)।")

        st.info(f"**📊 লাইভ মার্কেট ডাটা রিপোর্ট:** {' '.join(smc_analysis)}")

        if curr_price <= buy_zone: 
            if trend_4h == "BULLISH" and is_volume_high and curr_rsi < 45 and macd_bullish:
                st.success(f"**🟢 PERFECT BUY (Sniper Entry):** \n* **Entry:** ${curr_price:.2f} | 🎯 **TP1:** ${support + (risk_reward_gap * 0.5):.2f} | 🛑 **SL:** ${support - (support * 0.015):.2f}")
            else:
                st.warning("⚠️ সাপোর্ট জোনে এসেছে, কিন্তু সব ইন্ডিকেটর (MACD/Volume) এখনো কনফার্ম করেনি।")

        elif curr_price >= sell_zone: 
            if trend_4h == "BEARISH" and is_volume_high and curr_rsi > 55 and not macd_bullish:
                st.error(f"**🔴 PERFECT SELL (Sniper Entry):** \n* **Entry:** ${curr_price:.2f} | 🎯 **TP1:** ${resistance - (risk_reward_gap * 0.5):.2f} | 🛑 **SL:** ${resistance + (resistance * 0.015):.2f}")
            else:
                st.warning("⚠️ রেজিস্টেন্স জোনে এসেছে, কিন্তু সব ইন্ডিকেটর (MACD/Volume) এখনো কনফার্ম করেনি।")
        else:
            st.write("⚪ নো-ট্রেড জোন। পারফেক্ট স্নাইপার এন্ট্রির জন্য অপেক্ষা করুন।")

except Exception as e:
    st.error("⚠️ সার্ভার কানেকশনে সমস্যা হচ্ছে। ডাটা লোড হওয়ার জন্য অপেক্ষা করুন...")

if auto_refresh:
    time.sleep(15)
    st.rerun()
