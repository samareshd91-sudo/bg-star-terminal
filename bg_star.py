import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time 
import requests 

# টেলিগ্রাম সেটিং (আপনার নতুন টোকেনটি এখানে বসাবেন)
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_TOKEN_HERE"
TELEGRAM_CHAT_ID = "8614370967"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
    except:
        pass

st.set_page_config(page_title="BG STAR V6 PRO (Sniper Edition)", layout="wide")

# ----------------- প্রিমিয়াম CSS (Binance & Gold Style) -----------------
st.markdown("""
    <style>
    /* মেইন ব্যাকগ্রাউন্ড */
    .stApp { background-color: #0B0E11; color: #EAECEF; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    html, body, #root, [data-testid="stAppViewContainer"], .main {
        overscroll-behavior: none !important;
        overscroll-behavior-y: none !important;
    }
    
    /* প্রিমিয়াম মেট্রিক কার্ড */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #1E2329, #181A20);
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #2B3139; 
        border-left: 5px solid #F3BA2F; 
        box-shadow: 0 8px 16px rgba(0,0,0,0.4);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-5px); }
    
    /* সিগন্যাল বক্স */
    .premium-signal-box { 
        background: linear-gradient(145deg, #181A20, #0B0E11); 
        padding: 25px; 
        border-radius: 15px; 
        text-align: center; 
        border: 1px solid #2B3139; 
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.5);
        margin-bottom: 25px;
    }
    .buy-glow { border-color: #0ECB81; box-shadow: 0 0 25px rgba(14, 203, 129, 0.2); border-bottom: 5px solid #0ECB81;}
    .sell-glow { border-color: #F6465D; box-shadow: 0 0 25px rgba(246, 70, 93, 0.2); border-bottom: 5px solid #F6465D;}
    .wait-glow { border-bottom: 5px solid #888888; }
    
    /* সাবটাইটেল */
    h1, h2, h3 { color: #F3BA2F !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# শুধুমাত্র বিটকয়েন রাখা হলো
coins = ["BTC/USDT"]

st.sidebar.title("⚙️ BG STAR Control")
st.sidebar.write("🤖 শুধুমাত্র BTC/USDT-এ স্নাইপার অ্যানালাইসিস চলছে!")
chart_view = "BTC/USDT"
selected_tf = st.sidebar.selectbox("Timeframe", ["5m", "15m", "1h", "4h", "1d"], index=1)
auto_refresh = st.sidebar.checkbox("🟢 Auto-Refresh (Live 3s)", value=True)

st.title(f"🎯 BG STAR V6 PRO (Sniper Edition - BTC Only)")

exchange = ccxt.kucoin()
coin_data = {}
play_sound = False

# সিগন্যাল বক্সটি স্ক্রিনের মাঝে রাখার জন্য লেআউট
col1, col2, col3 = st.columns([1, 2, 1])

# 🧠 সুপার স্ক্যানার লুপ
for coin in coins:
    bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    bars_4h = exchange.fetch_ohlcv(coin, timeframe='4h', limit=50)
    df_4h = pd.DataFrame(bars_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_4h['ema_200'] = df_4h['close'].ewm(span=200).mean()
    trend_4h = "BULLISH" if df_4h['close'].iloc[-1] > df_4h['ema_200'].iloc[-1] else "BEARISH"
    
    df['rsi'] = 100 - (100 / (1 + (df['close'].diff().where(df['close'].diff() > 0, 0).rolling(14).mean() / (-df['close'].diff().where(df['close'].diff() < 0, 0)).rolling(14).mean())))
    df['ema_200'] = df['close'].ewm(span=200).mean()
    df['vol_sma'] = df['volume'].rolling(20).mean() 
    
    support = df['low'].min()
    resistance = df['high'].max()
    curr_price = df['close'].iloc[-1]
    curr_vol = df['volume'].iloc[-1]
    curr_rsi = df['rsi'].iloc[-1]
    vol_sma = df['vol_sma'].iloc[-1]
    risk_reward_gap = resistance - support
    
    buy_zone = support + (risk_reward_gap * 0.15)
    sell_zone = resistance - (risk_reward_gap * 0.15)
    
    coin_data[coin] = {'df': df, 'support': support, 'resistance': resistance, 'curr_price': curr_price, 'risk_reward_gap': risk_reward_gap, 'trend_4h': trend_4h, 'curr_vol': curr_vol, 'vol_sma': vol_sma, 'curr_rsi': curr_rsi}
    
    signal_text = "⚪ WAIT"
    box_class = "wait-glow"
    price_color = "#F3BA2F"
    
    is_volume_high = curr_vol > vol_sma  
    
    if curr_price <= buy_zone and trend_4h == "BULLISH" and is_volume_high and curr_rsi < 40:
        signal_text = "🟢 SNIPER BUY"
        box_class = "buy-glow"
        price_color = "#0ECB81"
        play_sound = True
        send_telegram_alert(f"🟢 SNIPER BUY ALERT!\nCoin: {coin}\nPrice: ${curr_price:.2f}\nTrend: Bullish 🚀\nTimeframe: {selected_tf}")
        
    elif curr_price >= sell_zone and trend_4h == "BEARISH" and is_volume_high and curr_rsi > 60:
        signal_text = "🔴 SNIPER SELL"
        box_class = "sell-glow"
        price_color = "#F6465D"
        play_sound = True
        send_telegram_alert(f"🔴 SNIPER SELL ALERT!\nCoin: {coin}\nPrice: ${curr_price:.2f}\nTrend: Bearish 📉\nTimeframe: {selected_tf}")
        
    with col2:
        st.markdown(f'<div class="premium-signal-box {box_class}"><b>{coin}</b><br><span style="font-size:35px; font-weight:bold; color:{price_color};">${curr_price:.2f}</span><br><span style="font-size:18px;">{signal_text}</span></div>', unsafe_allow_html=True)

if play_sound:
    st.toast("🔔 SNIPER SIGNAL DETECTED!", icon="🔔")
    st.markdown('<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>', unsafe_allow_html=True)

st.markdown("---")
sel_data = coin_data[chart_view]
df = sel_data['df']
curr_price = sel_data['curr_price']
support = sel_data['support']
resistance = sel_data['resistance']
risk_reward_gap = sel_data['risk_reward_gap']

st.subheader(f"Deep Analysis: {chart_view} ({selected_tf})")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Live Price", f"${curr_price:.2f}")
m2.metric("4H Big Trend", sel_data['trend_4h'])
m3.metric("Support Zone", f"${support:.2f}")
m4.metric("Resistance Zone", f"${resistance:.2f}")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)
fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], 
                             increasing_line_color='#0ECB81', decreasing_line_color='#F6465D', name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], name='EMA 200', line=dict(color='#F3BA2F', width=2)), row=1, col=1)
fig.add_hline(y=support, line_dash="dash", line_color="#0ECB81", annotation_text="Support", annotation_font_color="#0ECB81", row=1, col=1)
fig.add_hline(y=resistance, line_dash="dash", line_color="#F6465D", annotation_text="Resistance", annotation_font_color="#F6465D", row=1, col=1)

colors = ['#0ECB81' if close >= open else '#F6465D' for open, close in zip(df['open'], df['close'])]
fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors), row=2, col=1)

fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#2B3139')
fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#2B3139')
st.plotly_chart(fig, use_container_width=True)

st.markdown("### 🧠 BG STAR SMC Sniper Engine")
smc_analysis = []
smc_analysis.append(f"**বড় ট্রেন্ড (4h):** {sel_data['trend_4h']}।")

if sel_data['curr_vol'] > sel_data['vol_sma']:
    smc_analysis.append("**ভলিউম:** মার্কেটে এখন বড় ট্রেডারদের টাকা ঢুকছে (High Volume)।")
else:
    smc_analysis.append("**ভলিউম:** মার্কেটে এখন ভলিউম কম (Retailers Trap হতে পারে)।")

if curr_price <= support + (risk_reward_gap * 0.15): 
    st.info(f"**🔍 AI ব্যাকগ্রাউন্ড রিপোর্ট:** {' '.join(smc_analysis)}")
    if sel_data['trend_4h'] == "BULLISH" and sel_data['curr_vol'] > sel_data['vol_sma'] and sel_data['curr_rsi'] < 40:
        st.success(f"**🟢 PERFECT BUY (Sniper Entry):** \n* **Entry:** ${curr_price:.2f} | 🎯 **TP1:** ${support + (risk_reward_gap * 0.5):.2f} | 🛑 **SL:** ${support - (support * 0.015):.2f}")
    else:
        st.warning("⚠️ সাপোর্ট জোনে এসেছে, কিন্তু বড় ট্রেন্ড বা ভলিউম কনফার্ম করেনি। এখনই কিনবেন না।")

elif curr_price >= resistance - (risk_reward_gap * 0.15): 
    st.info(f"**🔍 AI ব্যাকগ্রাউন্ড রিপোর্ট:** {' '.join(smc_analysis)}")
    if sel_data['trend_4h'] == "BEARISH" and sel_data['curr_vol'] > sel_data['vol_sma'] and sel_data['curr_rsi'] > 60:
        st.error(f"**🔴 PERFECT SELL (Sniper Entry):** \n* **Entry:** ${curr_price:.2f} | 🎯 **TP1:** ${resistance - (risk_reward_gap * 0.5):.2f} | 🛑 **SL:** ${resistance + (resistance * 0.015):.2f}")
    else:
        st.warning("⚠️ রেজিস্টেন্স জোনে এসেছে, কিন্তু বড় ট্রেন্ড বা ভলিউম কনফার্ম করেনি। এখনই বিক্রি করবেন না।")
else:
    st.write("⚪ নো-ট্রেড জোন। পারফেক্ট স্নাইপার এন্ট্রির জন্য অপেক্ষা করুন।")

if auto_refresh:
    time.sleep(3)
    st.rerun()
