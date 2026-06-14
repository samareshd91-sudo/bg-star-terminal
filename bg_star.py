import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time 

st.set_page_config(page_title="BG STAR V6 PRO (Fast Scalper)", layout="wide")

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
st.sidebar.write("🤖 Fast Scalping Mode Active!")
selected_tf = st.sidebar.selectbox("Timeframe", ["5m", "15m", "1h"], index=1) # স্ক্যাল্পিংয়ের জন্য 4h/1d বাদ দেওয়া হলো
auto_refresh = st.sidebar.checkbox("🟢 Auto-Refresh (Live 10s)", value=True)

st.title(f"🎯 BG STAR V6 PRO (Fast Scalper Engine)")

# ক্র্যাশ প্রোটেকশন চালু করা হলো
exchange = ccxt.kucoin({'enableRateLimit': True})
play_sound = False

# সিগন্যাল বক্সটি স্ক্রিনের মাঝে রাখার জন্য লেআউট
col1, col2, col3 = st.columns([1, 2, 1])

try:
    # ডাটা ফেচ করা (শুধুমাত্র প্রয়োজনীয় ক্যান্ডেল)
    bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=150)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # ফাস্ট স্ক্যাল্পিং ইন্ডিকেটর (9 EMA এবং 21 EMA)
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    ema_bullish = df['ema_9'].iloc[-1] > df['ema_21'].iloc[-1]
    scalp_trend = "BULLISH (9>21)" if ema_bullish else "BEARISH (9<21)"
    
    # ইন্ডিকেটর - RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ইন্ডিকেটর - MACD (12, 26, 9)
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    df['vol_sma'] = df['volume'].rolling(20).mean() 
    
    # ফাস্ট লোকাল লিকুইডিটি জোন (গত ২০ ক্যান্ডেল)
    support = df['low'].tail(20).min()
    resistance = df['high'].tail(20).max()
    
    curr_price = df['close'].iloc[-1]
    curr_vol = df['volume'].iloc[-1]
    curr_rsi = df['rsi'].iloc[-1]
    vol_sma = df['vol_sma'].iloc[-1]
    curr_macd = df['macd'].iloc[-1]
    curr_macd_sig = df['macd_signal'].iloc[-1]
    risk_reward_gap = resistance - support
    
    macd_bullish = curr_macd > curr_macd_sig
    
    signal_text = "⚪ WAIT FOR CROSSOVER"
    box_class = "wait-box"
    price_color = "#f39c12"
    
    is_volume_high = curr_vol > vol_sma  
    
    # ⚡ ফাস্ট স্ক্যাল্পিং লজিক (EMA 9/21 Cross + MACD)
    if ema_bullish and macd_bullish and curr_rsi < 65:
        signal_text = "🟢 FAST SCALP BUY"
        box_class = "buy-box"
        price_color = "#00E676"
        play_sound = True
        
    elif not ema_bullish and not macd_bullish and curr_rsi > 35:
        signal_text = "🔴 FAST SCALP SELL"
        box_class = "sell-box"
        price_color = "#FF1744"
        play_sound = True
        
    with col2:
        st.markdown(f'<div class="signal-box {box_class}"><b>{coin}</b><br><span style="font-size:32px; font-weight:bold; color:{price_color};">${curr_price:.2f}</span><br><span style="font-size:18px; font-weight:bold;">{signal_text}</span></div>', unsafe_allow_html=True)

    if play_sound:
        st.toast("🔔 SCALP SIGNAL DETECTED!", icon="🔔")

    st.markdown("---")

    # ৪টি প্রধান মেট্রিকস (নতুন স্ক্যাল্পিং ডিজাইনে)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Live Price", f"${curr_price:.2f}")
    m2.metric("Scalp Trend (9/21)", "UPTREND 🟢" if ema_bullish else "DOWNTREND 🔴")
    m3.metric("Local Support (20 C)", f"${support:.2f}")
    m4.metric("Local Resistance (20 C)", f"${resistance:.2f}")

    # 📊 ক্যান্ডেলস্টিক চার্ট (EMA 9 এবং 21 সহ)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    
    # নতুন ফাস্ট EMA লাইন
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_9'], name='EMA 9 (Fast)', line=dict(color='#00BFFF', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_21'], name='EMA 21 (Slow)', line=dict(color='#FF8C00', width=2)), row=1, col=1)
    
    fig.add_hline(y=support, line_dash="dash", line_color="#00ff00", row=1, col=1)
    fig.add_hline(y=resistance, line_dash="dash", line_color="#ff0000", row=1, col=1)
    colors = ['#00ff00' if close >= open else '#ff0000' for open, close in zip(df['open'], df['close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 📥 বিস্তারিত এনালাইসিস প্যানেল
    with st.expander("🔍 এখানে টিপুন: বিস্তারিত AI স্ক্যাল্পিং রিপোর্ট"):
        st.markdown("### 🧠 BG STAR Fast Scalper Engine")
        smc_analysis = []
        
        # ১. EMA Crossover
        cross_status = "9 EMA ওপরে আছে (Bullish)" if ema_bullish else "9 EMA নিচে আছে (Bearish)"
        smc_analysis.append(f"**১. স্ক্যাল্প ট্রেন্ড:** {cross_status}।")
        
        # ২. MACD
        macd_status = "BULLISH 🟢" if macd_bullish else "BEARISH 🔴"
        smc_analysis.append(f"**২. MACD ট্রেন্ড:** {macd_status}।")

        # ৩. RSI
        rsi_status = "OVERSOLD 🟢" if curr_rsi < 45 else "OVERBOUGHT 🔴" if curr_rsi > 60 else "NEUTRAL ⚪"
        smc_analysis.append(f"**৩. RSI পজিশন:** {curr_rsi:.1f} ({rsi_status})।")

        st.info(f"**📊 লাইভ মার্কেট ডাটা রিপোর্ট:** {' '.join(smc_analysis)}")

        # ফাস্ট স্ক্যাল্পিং টার্গেট (ছোট স্টপ লস 1%)
        if ema_bullish and macd_bullish and curr_rsi < 65:
            st.success(f"**🟢 FAST SCALP BUY:** \n* **Entry:** ${curr_price:.2f} | 🎯 **Quick TP:** ${curr_price + (risk_reward_gap * 0.3):.2f} | 🛑 **Tight SL (1%):** ${curr_price - (curr_price * 0.01):.2f}")
        elif not ema_bullish and not macd_bullish and curr_rsi > 35:
            st.error(f"**🔴 FAST SCALP SELL:** \n* **Entry:** ${curr_price:.2f} | 🎯 **Quick TP:** ${curr_price - (risk_reward_gap * 0.3):.2f} | 🛑 **Tight SL (1%):** ${curr_price + (curr_price * 0.01):.2f}")
        else:
            st.write("⚪ নো-ট্রেড জোন। 9 ও 21 EMA ক্রসওভারের জন্য অপেক্ষা করুন।")

except Exception as e:
    st.error("⚠️ সার্ভার কানেকশনে সমস্যা হচ্ছে। ডাটা লোড হওয়ার জন্য অপেক্ষা করুন...")

if auto_refresh:
    time.sleep(10)
    st.rerun()
