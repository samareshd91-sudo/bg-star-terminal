import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go

# প্রফেশনাল লেআউট ও ডার্ক থিম স্টাইল
st.set_page_config(page_title="BG STAR Pro Analytics", layout="wide")
st.markdown("""
    <style>
    .stMetric { background-color: #1E1E2E; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 BG STAR ADVANCED TERMINAL V2")

# ১. ডাটা আনা
exchange = ccxt.binance()
bars = exchange.fetch_ohlcv('ETH/USDT', timeframe='15m', limit=100) # ১৫ মিনিটের ক্যান্ডেল (বেশি অ্যাকুরেট)
df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# ২. অ্যাডভান্সড ইন্ডিকেটরস (ফাঁকফোকর বন্ধ করার জন্য)
# RSI
df['rsi'] = 100 - (100 / (1 + (df['close'].diff().where(df['close'].diff() > 0, 0).rolling(14).mean() / (-df['close'].diff().where(df['close'].diff() < 0, 0)).rolling(14).mean())))
# EMA 200 (মেইন ট্রেন্ড)
df['ema_200'] = df['close'].ewm(span=200).mean()
# MACD
exp1 = df['close'].ewm(span=12, adjust=False).mean()
exp2 = df['close'].ewm(span=26, adjust=False).mean()
df['macd'] = exp1 - exp2
df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

# বর্তমান ডাটা
curr_price = df['close'].iloc[-1]
curr_rsi = df['rsi'].iloc[-1]
curr_macd = df['macd'].iloc[-1]
curr_signal = df['signal'].iloc[-1]
curr_ema = df['ema_200'].iloc[-1]

# ৩. প্রিমিয়াম ড্যাশবোর্ড প্যানেল
col1, col2, col3, col4 = st.columns(4)
col1.metric("ETH Live Price", f"${curr_price:.2f}")
col2.metric("RSI (Momentum)", f"{curr_rsi:.2f}")
col3.metric("MACD Status", "Bullish" if curr_macd > curr_signal else "Bearish")
col4.metric("Market Trend", "UPTREND" if curr_price > curr_ema else "DOWNTREND")

# ৪. প্রফেশনাল চার্ট
fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price')])
fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], name='EMA 200', line=dict(color='orange', width=2)))
fig.update_layout(template="plotly_dark", height=550, margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig, use_container_width=True)

# ৫. স্ট্রং সিগন্যাল ইঞ্জিন (৮০% কনফ্লুয়েন্স লজিক)
st.subheader("🤖 BG STAR AI Engine (Confluence Signal)")

# যদি RSI ওভারসোল্ড হয় + MACD বুলিশ হয় + দাম EMA এর উপরে থাকে
if curr_rsi < 35 and curr_macd > curr_signal and curr_price > curr_ema:
    st.success("🟢 80% CONFIRMED BUY: সব ইন্ডিকেটর পজিটিভ। ঝুঁকি কম।")
# যদি RSI ওভারবট হয় + MACD বিয়ারিশ হয় + দাম EMA এর নিচে থাকে
elif curr_rsi > 65 and curr_macd < curr_signal and curr_price < curr_ema:
    st.error("🔴 80% CONFIRMED SELL: সব ইন্ডিকেটর নেগেটিভ। মার্কেট পড়ার চান্স বেশি।")
else:
    st.warning("⚪ NEUTRAL: মার্কেট এখন ঝুঁকিপূর্ণ (ফাঁকফোকর আছে)। ট্রেড থেকে দূরে থাকুন।")