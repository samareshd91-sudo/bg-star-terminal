import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time 

# ১. প্রফেশনাল লেআউট ও ডার্ক থিম
st.set_page_config(page_title="BG STAR Pro Analytics", layout="wide")
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        overscroll-behavior-y: none !important;
    }
    .stMetric { background-color: #1E1E2E; padding: 15px; border-radius: 10px; border: 1px solid #333; border-left: 4px solid #f39c12; }
    </style>
""", unsafe_allow_html=True)

# ২. সাইডবার (কন্ট্রোল প্যানেল)
st.sidebar.title("⚙️ BG STAR Control")
selected_coin = st.sidebar.selectbox("Select Coin", ["ETH/USDT", "BTC/USDT", "BNB/USDT", "SOL/USDT"])
selected_tf = st.sidebar.selectbox("Timeframe", ["5m", "15m", "1h", "4h", "1d"], index=1)

auto_refresh = st.sidebar.checkbox("🟢 Auto-Refresh (Live 3s)", value=True)

st.title(f"🚀 BG STAR ADVANCED TERMINAL V6 (Live Edition)")
st.subheader(f"Live Market Analysis: {selected_coin} ({selected_tf})")

# ৩. ডাটা আনা
exchange = ccxt.kucoin()
bars = exchange.fetch_ohlcv(selected_coin, timeframe=selected_tf, limit=100)
df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# ৪. বেসিক ইন্ডিকেটর
df['rsi'] = 100 - (100 / (1 + (df['close'].diff().where(df['close'].diff() > 0, 0).rolling(14).mean() / (-df['close'].diff().where(df['close'].diff() < 0, 0)).rolling(14).mean())))
df['ema_200'] = df['close'].ewm(span=200).mean()

# ৫. ব্যাকগ্রাউন্ড ইন্ডিকেটর (SMC)
df['ema_12'] = df['close'].ewm(span=12).mean()
df['ema_26'] = df['close'].ewm(span=26).mean()
df['macd'] = df['ema_12'] - df['ema_26']
df['macd_signal'] = df['macd'].ewm(span=9).mean()

df['sma_20'] = df['close'].rolling(20).mean()
df['std_20'] = df['close'].rolling(20).std()
df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)

support = df['low'].min()
resistance = df['high'].max()
curr_price = df['close'].iloc[-1]
curr_rsi = df['rsi'].iloc[-1]
curr_macd = df['macd'].iloc[-1]
curr_macd_signal = df['macd_signal'].iloc[-1]

# ৬. প্রিমিয়াম ড্যাশবোর্ড প্যানেল
col1, col2, col3, col4 = st.columns(4)
col1.metric("Live Price", f"${curr_price:.2f}")
col2.metric("RSI (Momentum)", f"{curr_rsi:.2f}")
col3.metric("Support Zone", f"${support:.2f}")
col4.metric("Resistance Zone", f"${resistance:.2f}")

# ৭. ক্লিন প্রফেশনাল চার্ট 
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)

fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], name='EMA 200', line=dict(color='orange', width=2)), row=1, col=1)

fig.add_hline(y=support, line_dash="dash", line_color="#00ff00", annotation_text="Support", row=1, col=1)
fig.add_hline(y=resistance, line_dash="dash", line_color="#ff0000", annotation_text="Resistance", row=1, col=1)

colors = ['#00ff00' if close >= open else '#ff0000' for open, close in zip(df['open'], df['close'])]
fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors), row=2, col=1)

fig.update_layout(template="plotly_dark", height=650, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# ৮. BG STAR AI: SMC ইঞ্জিন ও সাউন্ড অ্যালার্ম
st.markdown("### 🧠 BG STAR Smart Money Engine (Hidden Analysis)")

risk_reward_gap = resistance - support

smc_analysis = []
if curr_macd > curr_macd_signal:
    smc_analysis.append("MACD বুলিশ (Buyers এর পাওয়ার বেশি)।")
else:
    smc_analysis.append("MACD বিয়ারিশ (Sellers এর পাওয়ার বেশি)।")

if curr_price <= df['bb_lower'].iloc[-1] + 2:
    smc_analysis.append("Bollinger Band সাপোর্ট।")
elif curr_price >= df['bb_upper'].iloc[-1] - 2:
    smc_analysis.append("Bollinger Band রেজিস্টেন্স।")

if curr_price <= support + (risk_reward_gap * 0.15): 
    sl = support - (support * 0.005)
    tp1 = support + (risk_reward_gap * 0.5)
    tp2 = resistance
    
    st.success(f"**🟢 WHALE BUY ZONE (Bullish Order Block):** \n\n**🔍 AI ব্যাকগ্রাউন্ড রিপোর্ট:** {' '.join(smc_analysis)}\n\n* **Entry:** ${curr_price:.2f} | 🎯 **TP1:** ${tp1:.2f} | 🎯 **TP2:** ${tp2:.2f} | 🛑 **SL:** ${sl:.2f}")
    
    # সাউন্ড ও নোটিফিকেশন (Buy)
    st.toast("🟢 STRONG BUY SIGNAL! এখনই চেক করুন!", icon="🔔")
    st.markdown('<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>', unsafe_allow_html=True)

elif curr_price >= resistance - (risk_reward_gap * 0.15): 
    sl = resistance + (resistance * 0.005)
    tp1 = resistance - (risk_reward_gap * 0.5)
    tp2 = support
    
    st.error(f"**🔴 WHALE SELL ZONE (Bearish Order Block):** \n\n**🔍 AI ব্যাকগ্রাউন্ড রিপোর্ট:** {' '.join(smc_analysis)}\n\n* **Entry:** ${curr_price:.2f} | 🎯 **TP1:** ${tp1:.2f} | 🎯 **TP2:** ${tp2:.2f} | 🛑 **SL:** ${sl:.2f}")
    
    # সাউন্ড ও নোটিফিকেশন (Sell)
    st.toast("🔴 STRONG SELL SIGNAL! এখনই চেক করুন!", icon="🔔")
    st.markdown('<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>', unsafe_allow_html=True)

else:
    st.warning(f"**⚪ NO TRADE ZONE (Retail Trap):** \n\n**🔍 AI ব্যাকগ্রাউন্ড রিপোর্ট:** {' '.join(smc_analysis)}\n\n💡 **পরামর্শ:** কোনো ট্রেড নেবেন না। দাম ${support:.2f} বা ${resistance:.2f} এ আসার জন্য অপেক্ষা করুন।")

# ৯. ম্যাজিক অটো-রিফ্রেশ লুপ (৩ সেকেন্ড পর পর)
if auto_refresh:
    time.sleep(3)
    st.rerun()
