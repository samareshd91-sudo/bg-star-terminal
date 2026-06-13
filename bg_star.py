import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time 
import requests 

# ----------------- কনফিগারেশন -----------------
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_TOKEN_HERE"
TELEGRAM_CHAT_ID = "8614370967"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
    except:
        pass

# ----------------- পেজ সেটআপ -----------------
st.set_page_config(page_title="BG STAR | PRO TERMINAL", layout="wide", initial_sidebar_state="expanded")

# ----------------- প্রিমিয়াম CSS (Binance & Gold Style) -----------------
st.markdown("""
    <style>
    /* মেইন ব্যাকগ্রাউন্ড */
    .stApp { background-color: #0B0E11; color: #EAECEF; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* হাইড ডিফল্ট জিনিসপত্র */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* প্রিমিয়াম মেট্রিক কার্ড */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #1E2329, #181A20);
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #2B3139; 
        border-left: 5px solid #F3BA2F; /* লাক্সারি গোল্ডেন লাইন */
        box-shadow: 0 8px 16px rgba(0,0,0,0.4);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-5px); }
    
    /* সিগন্যাল বক্স */
    .premium-signal-box { 
        background: linear-gradient(145deg, #181A20, #0B0E11); 
        padding: 30px; 
        border-radius: 15px; 
        text-align: center; 
        border: 1px solid #F3BA2F; 
        box-shadow: 0 0 20px rgba(243, 186, 47, 0.15);
        margin-bottom: 25px;
    }
    .buy-glow { border-color: #0ECB81; box-shadow: 0 0 25px rgba(14, 203, 129, 0.2); }
    .sell-glow { border-color: #F6465D; box-shadow: 0 0 25px rgba(246, 70, 93, 0.2); }
    
    /* টার্মিনাল টেক্সট */
    .terminal-text { font-family: 'Courier New', Courier, monospace; color: #F3BA2F; font-size: 16px; }
    
    /* সাবটাইটেল */
    h1, h2, h3 { color: #F3BA2F !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

coins = ["BTC/USDT"]

# ----------------- সাইডবার কন্ট্রোল প্যানেল -----------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Bitcoin.svg/1200px-Bitcoin.svg.png", width=60)
    st.title("⚙️ BG STAR SYSTEM")
    st.markdown("---")
    st.markdown("<p style='color:#848E9C;'>TERMINAL SETTINGS</p>", unsafe_allow_html=True)
    selected_tf = st.selectbox("⏱️ Timeframe Focus", ["5m", "15m", "1h", "4h", "1d"], index=1)
    auto_refresh = st.checkbox("🟢 Live Sync (3s)", value=True)
    st.markdown("---")
    st.info("🛡️ Institutional Risk Management Active (1.5% SL)")

# ----------------- মেইন হেডার -----------------
st.markdown("<h1 style='text-align: center; font-size: 45px;'>👑 BG STAR INSTITUTIONAL TERMINAL</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #848E9C; font-size: 18px; margin-bottom: 40px;'>Advanced Sniper AI Engine • BTC Exclusive Edition</p>", unsafe_allow_html=True)

exchange = ccxt.kucoin()
play_sound = False

# ----------------- কোর লজিক ও ইঞ্জিন -----------------
try:
    coin = coins[0] # শুধুমাত্র BTC
    
    bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    bars_4h = exchange.fetch_ohlcv(coin, timeframe='4h', limit=50)
    df_4h = pd.DataFrame(bars_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_4h['ema_200'] = df_4h['close'].ewm(span=200).mean()
    trend_4h = "BULLISH 🚀" if df_4h['close'].iloc[-1] > df_4h['ema_200'].iloc[-1] else "BEARISH 📉"
    
    # ইন্ডিকেটর
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
    
    signal_text = "SCANNING ZONES... ⚪"
    box_class = ""
    status_color = "#F3BA2F"
    
    is_volume_high = curr_vol > vol_sma 
    
    # স্নাইপার লজিক
    if curr_price <= buy_zone and "BULLISH" in trend_4h and is_volume_high and curr_rsi < 40:
        signal_text = "🟢 EXECUTE LONG (BUY)"
        box_class = "buy-glow"
        status_color = "#0ECB81"
        play_sound = True
        send_telegram_alert(f"🟢 BG STAR VIP BUY!\nCoin: {coin}\nEntry: ${curr_price:.2f}\nTrend: Bullish\nSL: 1.5%")
        
    elif curr_price >= sell_zone and "BEARISH" in trend_4h and is_volume_high and curr_rsi > 60:
        signal_text = "🔴 EXECUTE SHORT (SELL)"
        box_class = "sell-glow"
        status_color = "#F6465D"
        play_sound = True
        send_telegram_alert(f"🔴 BG STAR VIP SELL!\nCoin: {coin}\nEntry: ${curr_price:.2f}\nTrend: Bearish\nSL: 1.5%")

    # ----------------- টপ সিগন্যাল ড্যাশবোর্ড -----------------
    st.markdown(f"""
        <div class="premium-signal-box {box_class}">
            <h3 style='color: #848E9C; margin:0;'>LIVE MARKET STATUS: {coin}</h3>
            <h1 style='font-size: 60px; color: {status_color}; margin: 10px 0;'>${curr_price:,.2f}</h1>
            <h2 style='color: {status_color}; letter-spacing: 2px;'>{signal_text}</h2>
        </div>
    """, unsafe_allow_html=True)

    # ----------------- লাইভ ডাটা মেট্রিকস -----------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📌 Global 4H Trend", trend_4h)
    m2.metric("🟢 Institutional Buy Zone", f"${support:,.2f}")
    m3.metric("🔴 Institutional Sell Zone", f"${resistance:,.2f}")
    m4.metric("⚡ RSI Momentum (14)", f"{curr_rsi:.1f}")

    st.write("") # স্পেসিং

    # ----------------- প্রো-চার্ট ভিউ -----------------
    st.markdown("### 📊 Market Blueprint")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)
    
    # ক্যান্ডেলস্টিক (ব্রাইট কালার)
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], 
                                 increasing_line_color='#0ECB81', decreasing_line_color='#F6465D', name='BTC'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_200'], name='EMA 200', line=dict(color='#F3BA2F', width=2)), row=1, col=1)
    
    # সাপোর্ট/রেজিস্ট্যান্স লাইন
    fig.add_hline(y=support, line_dash="dash", line_color="#0ECB81", annotation_text="BUY WALL", annotation_font_color="#0ECB81", row=1, col=1)
    fig.add_hline(y=resistance, line_dash="dash", line_color="#F6465D", annotation_text="SELL WALL", annotation_font_color="#F6465D", row=1, col=1)
    
    # ভলিউম
    colors = ['#0ECB81' if close >= open else '#F6465D' for open, close in zip(df['open'], df['close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors, opacity=0.8), row=2, col=1)
    
    fig.update_layout(
        template="plotly_dark", 
        height=550, 
        margin=dict(l=0, r=0, t=10, b=0), 
        xaxis_rangeslider_visible=False,
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)'
    )
    # গ্রিড লাইন হালকা করা
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#2B3139')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#2B3139')
    st.plotly_chart(fig, use_container_width=True)

    # ----------------- AI ব্রেন (টার্মিনাল আউটপুট) -----------------
    st.markdown("### 🤖 BG STAR AI Engine Report")
    
    vol_status = "Smart Money INFLOW Detected (High Volume)" if is_volume_high else "Low Liquidity (Retail Zone)"
    
    with st.container():
        st.markdown(f"""
            <div style="background-color: #0d1117; padding: 20px; border-radius: 8px; border: 1px solid #30363d;">
                <p class="terminal-text">> Analyzing Market Data...</p>
                <p class="terminal-text">> Trend Match: {trend_4h}</p>
                <p class="terminal-text">> Volume Check: {vol_status}</p>
                <p class="terminal-text">> Overbought/Oversold Level: {curr_rsi:.1f}</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    if curr_price <= buy_zone and "BULLISH" in trend_4h and is_volume_high and curr_rsi < 40:
        st.success(f"**⚡ AI CONFIRMATION:** 100% PERFECT BUY ENTRY DETECTED.\n\n🎯 **Take Profit:** ${support + (risk_reward_gap * 0.5):,.2f} | 🛑 **Stop Loss (1.5%):** ${support - (support * 0.015):,.2f}")
    elif curr_price >= sell_zone and "BEARISH" in trend_4h and is_volume_high and curr_rsi > 60:
        st.error(f"**⚡ AI CONFIRMATION:** 100% PERFECT SELL ENTRY DETECTED.\n\n🎯 **Take Profit:** ${resistance - (risk_reward_gap * 0.5):,.2f} | 🛑 **Stop Loss (1.5%):** ${resistance + (resistance * 0.015):,.2f}")

except Exception as e:
    st.warning("Fetching Live Data from Exchange... Please wait.")

if play_sound:
    st.toast("🚨 BG STAR SNIPER TRIGGERED!", icon="🚨")
    st.markdown('<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>', unsafe_allow_html=True)

if auto_refresh:
    time.sleep(3)
    st.rerun()
    
