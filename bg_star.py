import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time 
import requests 

# টেলিগ্রাম সেটিং (তোমার নতুন টোকেনটি এখানে বসাও)
TELEGRAM_BOT_TOKEN = "YOUR_NEW_TOKEN_HERE"
TELEGRAM_CHAT_ID = "8614370967"

# --- অ্যান্টি-স্প্যাম মেমরি (যাতে বারবার একই মেসেজ না যায়) ---
if 'last_alert' not in st.session_state:
    st.session_state.last_alert = {"ETH/USDT": None, "BTC/USDT": None, "BNB/USDT": None, "SOL/USDT": None}

def send_telegram_alert(message, coin, alert_type):
    # যদি আগে থেকেই এই সিগন্যাল পাঠানো থাকে, তবে স্কিপ করবে
    if st.session_state.last_alert.get(coin) != alert_type:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
            st.session_state.last_alert[coin] = alert_type # সেভ করে রাখল যে মেসেজ পাঠানো হয়েছে
        except Exception as e:
            st.error(f"Telegram Error: {e}")

st.set_page_config(page_title="BG STAR V6 PRO (Sniper Edition)", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    html, body, #root, .stApp, [data-testid="stAppViewContainer"], .main {
        overscroll-behavior: none !important;
        overscroll-behavior-y: none !important;
    }
    .stMetric { background-color: #161A25; padding: 15px; border-radius: 8px; border: 1px solid #2B313F; border-left: 4px solid #f39c12; }
    .signal-box { background-color: #161A25; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px; border: 1px solid #2B313F; font-size: 16px;}
    .buy-box { border-bottom: 4px solid #00E676; box-shadow: 0px 4px 15px rgba(0, 230, 118, 0.15); }
    .sell-box { border-bottom: 4px solid #FF1744; box-shadow: 0px 4px 15px rgba(255, 23, 68, 0.15); }
    .wait-box { border-bottom: 4px solid #78909C; }
    </style>
""", unsafe_allow_html=True)

coins = ["ETH/USDT", "BTC/USDT", "BNB/USDT", "SOL/USDT"]

st.sidebar.title("⚙️ BG STAR Control")
st.sidebar.markdown("---")
st.sidebar.write("🤖 **Smart AI Active**")
chart_view = st.sidebar.selectbox("🎯 Select Coin For Deep Analysis", coins)
selected_tf = st.sidebar.selectbox("⏱️ Timeframe", ["5m", "15m", "1h", "4h", "1d"], index=1)
auto_refresh = st.sidebar.checkbox("🟢 Auto-Refresh (Live 3s)", value=True)
st.sidebar.markdown("---")
st.sidebar.info("💡 **Pro Tip:** MACD and RSI are working together to filter fake breakouts.")

st.title(f"🎯 BG STAR V6 PRO (Ultimate Sniper)")

exchange = ccxt.kucoin({'enableRateLimit': True}) # ক্র্যাশ প্রোটেকশন
coin_data = {}
play_sound = False

cols = st.columns(4)

# 🧠 সুপার স্ক্যানার লুপ
for i, coin in enumerate(coins):
    try:
        # মার্কেট ডাটা ফেচ করা
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        bars_4h = exchange.fetch_ohlcv(coin, timeframe='4h', limit=50)
        df_4h = pd.DataFrame(bars_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_4h['ema_200'] = df_4h['close'].ewm(span=200).mean()
        trend_4h = "BULLISH" if df_4h['close'].iloc[-1] > df_4h['ema_200'].iloc[-1] else "BEARISH"
        
        # --- ইন্ডিকেটর ক্যালকুলেশন ---
        # 1. RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 2. MACD (12, 26, 9)
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 3. Volume SMA & EMA
        df['ema_200'] = df['close'].ewm(span=200).mean()
        df['vol_sma'] = df['volume'].rolling(20).mean() 
        
        # লাইভ ভ্যালু
        support = df['low'].min()
        resistance = df['high'].max()
        curr_price = df['close'].iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        curr_rsi = df['rsi'].iloc[-1]
        vol_sma = df['vol_sma'].iloc[-1]
        risk_reward_gap = resistance - support
        
        curr_macd = df['macd'].iloc[-1]
        curr_macd_sig = df['macd_signal'].iloc[-1]
        macd_bullish = curr_macd > curr_macd_sig 
        
        buy_zone = support + (risk_reward_gap * 0.20) 
        sell_zone = resistance - (risk_reward_gap * 0.20)
        
        coin_data[coin] = {
            'df': df, 'support': support, 'resistance': resistance, 'curr_price': curr_price, 
            'risk_reward_gap': risk_reward_gap, 'trend_4h': trend_4h, 'curr_vol': curr_vol, 
            'vol_sma': vol_sma, 'curr_rsi': curr_rsi, 'macd_bullish': macd_bullish
        }
        
        signal_text = "⚪ WAIT"
        box_class = "wait-box"
        
        # স্নাইপার লজিক (SMC + MACD + RSI)
        is_volume_high = curr_vol > vol_sma 
        
        if curr_price <= buy_zone and trend_4h == "BULLISH" and curr_rsi < 45 and macd_bullish:
            signal_text = "🟢 BUY ZONE"
            box_class = "buy-box"
            play_sound = True
            send_telegram_alert(f"🟢 SNIPER BUY ALERT!\nCoin: {coin}\nPrice: ${curr_price:.2f}\nTrend: Bullish 🚀\nRSI: {curr_rsi:.2f}\nMACD: Bullish", coin, "BUY")
            
        elif curr_price >= sell_zone and trend_4h == "BEARISH" and curr_rsi > 55 and not macd_bullish:
            signal_text = "🔴 SELL ZONE"
            box_class = "sell-box"
            play_sound = True
            send_telegram_alert(f"🔴 SNIPER SELL ALERT!\nCoin: {coin}\nPrice: ${curr_price:.2f}\nTrend: Bearish 📉\nRSI: {curr_rsi:.2f}\nMACD: Bearish", coin, "SELL")
        else:
            # প্রাইস জোন থেকে বেরিয়ে গেলে বা সিগন্যাল না থাকলে অ্যান্টি-স্প্যাম রিসেট করে দেবে
            st.session_state.last_alert[coin] = None
            
        with cols[i]:
            st.markdown(f'<div class="signal-box {box_class}"><b>{coin}</b><br><span style="font-size:20px; font-weight:bold;">${curr_price:.2f}</span><br>{signal_text}</div>', unsafe_allow_html=True)
            
    except Exception as e:
        with cols[i]:
            st.markdown(f'<div class="signal-box wait-box"><b>{coin}</b><br>Loading Data...<br>API Waiting</div>', unsafe_allow_html=True)
        continue # ক্র্যাশ না করে পরের কয়েনে চলে যাবে

if play_sound:
    st.toast("🔔 SNIPER SIGNAL DETECTED!", icon="🔔")

st.markdown("---")

# --- Deep Analysis Section ---
if chart_view in coin_data:
    sel_data = coin_data[chart_view]
    df = sel_data['df']
    curr_price = sel_data['curr_price']
    support = sel_data['support']
    resistance = sel_data['resistance']
    risk_reward_gap = sel_data['risk_reward_gap']

    st.subheader(f"📊 Deep Analysis: {chart_view} ({selected_tf})")

    # মেট্রিকস প্যানেল
    c1, c2, c3 = st.columns(3)
    c1.metric("Live Price", f"${curr_price:.2f}")
    c2.metric("Support (Buy Zone)", f"${support:.2f}")
    c3.metric("Resistance (Sell Zone)", f"${resistance:.2f}")

    c4, c5, c6 = st.columns(3)
    c4.metric("4H Big Trend", sel_data['trend_4h'])

    # RSI Status
    rsi_status = "OVERBOUGHT 🔴" if sel_data['curr_rsi'] > 65 else "OVERSOLD 🟢" if sel_data['curr_rsi'] < 35 else "NEUTRAL ⚪"
    c5.metric("RSI (14) Status", f"{sel_data['curr_rsi']:.2f}", rsi_status)

    # MACD Status
    macd_status = "BULLISH 🟢" if sel_data['macd_bullish'] else "BEARISH 🔴"
    c6.metric("MACD Cross", macd_status)

    # --- Advanced Charting (Price + Volume + MACD) ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.05)

    # 1. Price Chart
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], name='EMA 200', line=dict(color='#FFA726', width=2)), row=1, col=1)
    fig.add_hline(y=support, line_dash="dot", line_color="#00E676", annotation_text="Support", row=1, col=1)
    fig.add_hline(y=resistance, line_dash="dot", line_color="#FF1744", annotation_text="Resistance", row=1, col=1)

    # 2. Volume Chart
    colors_vol = ['#00E676' if close >= open else '#FF1744' for open, close in zip(df['open'], df['close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors_vol), row=2, col=1)

    # 3. MACD Chart
    fig.add_trace(go.Scatter(x=df.index, y=df['macd'], name='MACD', line=dict(color='#29B6F6', width=2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], name='Signal', line=dict(color='#FFA726', width=2)), row=3, col=1)
    colors_macd = ['#00E676' if val >= 0 else '#FF1744' for val in df['macd_hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], name='Histogram', marker_color=colors_macd), row=3, col=1)

    fig.update_layout(template="plotly_dark", height=700, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False, paper_bgcolor='#0E1117', plot_bgcolor='#0E1117')
    st.plotly_chart(fig, use_container_width=True)

    # --- AI BG STAR Report ---
    st.markdown("### 🧠 BG STAR AI Trading Report")
    smc_analysis = []
    smc_analysis.append(f"**১. বিগ ট্রেন্ড:** ৪ ঘণ্টার ট্রেন্ড {sel_data['trend_4h']}।")
    smc_analysis.append(f"**২. মোমেন্টাম (RSI):** {sel_data['curr_rsi']:.1f} ({rsi_status})।")
    smc_analysis.append(f"**৩. ট্রেন্ড চেঞ্জ (MACD):** {macd_status}।")

    st.info(f"**📊 এনালাইসিস সামারি:** {' '.join(smc_analysis)}")

    if curr_price <= support + (risk_reward_gap * 0.20): 
        if sel_data['trend_4h'] == "BULLISH" and sel_data['macd_bullish'] and sel_data['curr_rsi'] < 45:
            st.success(f"**🟢 100% PERFECT BUY:** \n* **Entry:** ${curr_price:.2f} | 🎯 **Take Profit:** ${support + (risk_reward_gap * 0.6):.2f} | 🛑 **Stop Loss:** ${support - (support * 0.005):.2f}")
        else:
            st.warning("⚠️ সাপোর্ট জোনে এসেছে, কিন্তু MACD/RSI এখনো 'Buy' কনফার্ম করেনি।")

    elif curr_price >= resistance - (risk_reward_gap * 0.20): 
        if sel_data['trend_4h'] == "BEARISH" and not sel_data['macd_bullish'] and sel_data['curr_rsi'] > 55:
            st.error(f"**🔴 100% PERFECT SELL:** \n* **Entry:** ${curr_price:.2f} | 🎯 **Take Profit:** ${resistance - (risk_reward_gap * 0.6):.2f} | 🛑 **Stop Loss:** ${resistance + (resistance * 0.005):.2f}")
        else:
            st.warning("⚠️ রেজিস্ট্যান্স জোনে এসেছে, কিন্তু MACD/RSI এখনো 'Sell' কনফার্ম করেনি।")
    else:
        st.write("⚪ মার্কেট এখন নো-ট্রেড জোনে (মাঝামাঝি) আছে। এন্ট্রি নেওয়ার জন্য জোন পর্যন্ত অপেক্ষা করো।")

if auto_refresh:
    time.sleep(3)
    st.rerun()
        
