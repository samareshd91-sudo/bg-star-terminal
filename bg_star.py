import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time 

st.set_page_config(page_title="BG STAR V6 PRO (Pure Scalper)", layout="wide")

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
st.sidebar.write("🛡️ Pure Scalping (50 EMA Shield)")
selected_tf = st.sidebar.selectbox("Timeframe", ["5m", "15m", "1h"], index=1) 
auto_refresh = st.sidebar.checkbox("🟢 Auto-Refresh (Live 15s)", value=True)

st.title(f"🎯 BG STAR V6 PRO (Pure Scalper Engine)")

exchange = ccxt.kucoin({'enableRateLimit': True})
play_sound = False

col1, col2, col3 = st.columns([1, 2, 1])

try:
    # 50 EMA সঠিকভাবে ক্যালকুলেট করার জন্য ডাটা লিমিট ২০০ করা হলো
    bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=200)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # ৩টি প্রধান EMA (আপনার বন্ধুর লজিক)
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    curr_price = df['close'].iloc[-1]
    curr_ema_50 = df['ema_50'].iloc[-1]
    
    # 50 EMA এর সাহায্যে কারেন্ট ট্রেন্ড (Safety Shield)
    trend_50 = "BULLISH" if curr_price > curr_ema_50 else "BEARISH"
    ema_bullish = df['ema_9'].iloc[-1] > df['ema_21'].iloc[-1]
    
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
    
    # কাছাকাছি সাপোর্ট ও রেজিস্ট্যান্স (গত ১৫ ক্যান্ডেলের ডেটা)
    local_support = df['low'].tail(15).min()
    local_resistance = df['high'].tail(15).max()
    
    curr_vol = df['volume'].iloc[-1]
    curr_rsi = df['rsi'].iloc[-1]
    vol_sma = df['vol_sma'].iloc[-1]
    curr_macd = df['macd'].iloc[-1]
    curr_macd_sig = df['macd_signal'].iloc[-1]
    
    macd_bullish = curr_macd > curr_macd_sig
    is_volume_high = curr_vol > vol_sma  
    
    signal_text = "⚪ WAITING FOR SETUP"
    box_class = "wait-box"
    price_color = "#f39c12"
    
    # 🛡️ পিওর স্ক্যাল্পিং লজিক (50 EMA Shield + 9/21 Cross)
    if trend_50 == "BULLISH" and ema_bullish and macd_bullish and curr_rsi < 65:
        if is_volume_high:
            signal_text = "🟢 FAST SCALP BUY"
            box_class = "buy-box"
            price_color = "#00E676"
            play_sound = True
        else:
            signal_text = "⚪ LOW VOLUME - WAIT"
        
    elif trend_50 == "BEARISH" and not ema_bullish and not macd_bullish and curr_rsi > 35:
        if is_volume_high:
            signal_text = "🔴 FAST SCALP SELL"
            box_class = "sell-box"
            price_color = "#FF1744"
            play_sound = True
        else:
            signal_text = "⚪ LOW VOLUME - WAIT"
        
    with col2:
        st.markdown(f'<div class="signal-box {box_class}"><b>{coin}</b><br><span style="font-size:32px; font-weight:bold; color:{price_color};">${curr_price:.2f}</span><br><span style="font-size:18px; font-weight:bold;">{signal_text}</span></div>', unsafe_allow_html=True)

    if play_sound:
        st.toast("⚡ FAST SCALP SIGNAL DETECTED!", icon="🔔")

    st.markdown("---")

    # ৪টি প্রধান মেট্রিকস (এখন 50 EMA শিল্ড দেখাবে)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Live Price", f"${curr_price:.2f}")
    m2.metric("50 EMA Shield", "UPTREND 🟢" if trend_50 == "BULLISH" else "DOWNTREND 🔴")
    m3.metric("Local Support", f"${local_support:.2f}")
    m4.metric("Local Resistance", f"${local_resistance:.2f}")

    # 📊 ক্যান্ডেলস্টিক চার্ট
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    
    # চার্টে ৩টি লাইন যোগ করা হলো
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_9'], name='EMA 9 (Fast)', line=dict(color='#00BFFF', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_21'], name='EMA 21 (Slow)', line=dict(color='#FF8C00', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_50'], name='EMA 50 (Shield)', line=dict(color='#F1C40F', width=3, dash='dot')), row=1, col=1)
    
    fig.add_hline(y=local_support, line_dash="dash", line_color="#00ff00", row=1, col=1)
    fig.add_hline(y=local_resistance, line_dash="dash", line_color="#ff0000", row=1, col=1)
    
    colors = ['#00ff00' if close >= open else '#ff0000' for open, close in zip(df['open'], df['close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 📥 বিস্তারিত এনালাইসিস প্যানেল
    with st.expander("🔍 এখানে টিপুন: বিস্তারিত AI স্ক্যাল্পিং রিপোর্ট (50 EMA Active)"):
        st.markdown("### 🧠 BG STAR Pure Scalper Engine")
        smc_analysis = []
        
        # ১. 50 EMA Shield
        smc_analysis.append(f"**১. সেফটি শিল্ড (50 EMA):** {trend_50}।")
        
        # ২. 9/21 Crossover
        cross_status = "BULLISH (9 EMA ওপরে)" if ema_bullish else "BEARISH (9 EMA নিচে)"
        smc_analysis.append(f"**২. অ্যাকশন লাইন:** {cross_status}।")

        # ৩. RSI
        rsi_status = "OVERSOLD 🟢" if curr_rsi < 45 else "OVERBOUGHT 🔴" if curr_rsi > 60 else "NEUTRAL ⚪"
        smc_analysis.append(f"**৩. RSI পজিশন:** {curr_rsi:.1f} ({rsi_status})।")
        
        # ৪. ভলিউম শিল্ড
        vol_status = "🟢 হাই ভলিউম (ট্রেড করা যাবে)" if is_volume_high else "🔴 লো ভলিউম (অপেক্ষা করুন)"
        smc_analysis.append(f"**৪. ভলিউম:** {vol_status}।")

        st.info(f"**📊 লাইভ মার্কেট ডাটা রিপোর্ট:** {' '.join(smc_analysis)}")

        # ডায়নামিক টেক প্রফিট এবং স্টপ লস লজিক
        if "BUY" in signal_text:
            st.success(f"**🟢 FAST SCALP BUY DETECTED:** \n* **১. Entry:** ${curr_price:.2f} \n* 🎯 **২. TP (Nearest Resistance):** ${local_resistance:.2f} \n* 🛡️ **৩. SL (Nearest Support):** ${(local_support - (local_support*0.002)):.2f}")
        elif "SELL" in signal_text:
            st.error(f"**🔴 FAST SCALP SELL DETECTED:** \n* **১. Entry:** ${curr_price:.2f} \n* 🎯 **২. TP (Nearest Support):** ${local_support:.2f} \n* 🛡️ **৩. SL (Nearest Resistance):** ${(local_resistance + (local_resistance*0.002)):.2f}")
        elif "LOW VOLUME" in signal_text:
            st.warning("⚠️ প্রাইস এবং ইন্ডিকেটর পারফেক্ট জায়গায় আছে, কিন্তু মার্কেটে ভলিউম কম। ফেক ব্রেকআউট এড়াতে ভলিউম বাড়া পর্যন্ত অপেক্ষা করুন।")
        else:
            st.write("⚪ নো-ট্রেড জোন। 50 EMA-এর সাথে 9 এবং 21 লাইনের ক্রসওভার মেলার জন্য অপেক্ষা করুন।")

except Exception as e:
    st.error("⚠️ সার্ভার থেকে লাইভ ডাটা লোড হচ্ছে, দয়া করে অপেক্ষা করুন...")

if auto_refresh:
    time.sleep(15)
    st.rerun()
