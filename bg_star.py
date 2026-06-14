import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
import time 
from datetime import datetime

# 👑 Premium Layout Config
st.set_page_config(page_title="BG STAR AUTO-BOT", layout="wide", initial_sidebar_state="collapsed")

# 🌟 Ultra-Premium CSS
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #0B0E11 !important; color: #EAECEF !important; overscroll-behavior: none !important; }
    .brand-title { font-size: 36px; font-weight: 900; background: -webkit-linear-gradient(45deg, #FCD535, #F39C12); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 0px; }
    .sub-title { text-align: center; color: #848E9C; font-size: 14px; margin-bottom: 15px; }
    .buy-glow { color: #00FF00; font-weight: 900; }
    .sell-glow { color: #FF0000; font-weight: 900; }
    .wait-glow { color: #848E9C; font-weight: bold; }
    .main-detail-card { background: linear-gradient(135deg, #1E2329 0%, #14181C 100%); border-radius: 16px; padding: 25px; border: 1px solid #FCD535; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .bot-panel { background-color: #181A20; border: 1px solid #00BFFF; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    hr { border-color: #2B3139; margin: 15px 0; }
    </style>
""", unsafe_allow_html=True)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 
FEE_RATE = 0.0005 # 0.05% Exchange Fee

# ================= 🧠 Bot Memory Setup (Paper Trading) =================
if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"
if 'bot_balance_inr' not in st.session_state: st.session_state.bot_balance_inr = 1000.0 # Starting 1000 INR
if 'bot_positions' not in st.session_state: st.session_state.bot_positions = {} # Holds active trades
if 'bot_history' not in st.session_state: st.session_state.bot_history = [] # Trade history log

st.markdown('<div class="brand-title">BG STAR PAPER TRADING BOT</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">🤖 1000 INR VIRTUAL WALLET | AUTO EXECUTION ACTIVE</div>', unsafe_allow_html=True)

col_toggle1, col_toggle2, col_toggle3 = st.columns([1, 2, 1])
with col_toggle2:
    auto_refresh = st.toggle("🟢 Bot Auto-Run (অন রাখলে বট নিজে ট্রেড করবে)", value=True)

def fetch_coin_radar(coin):
    try:
        bars = exchange.fetch_ohlcv(coin, timeframe=selected_tf, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        curr_price = df['close'].iloc[-1]
        curr_ema_50 = df['ema_50'].iloc[-1]
        trend_50 = "BULLISH" if curr_price > curr_ema_50 else "BEARISH"
        ema_bullish = df['ema_9'].iloc[-1] > df['ema_20'].iloc[-1]
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        vol_sma = df['volume'].rolling(20).mean().iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        is_volume_high = curr_vol > vol_sma  
        macd_bullish = df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]
        
        local_support = df['low'].tail(15).min()
        local_resistance = df['high'].tail(15).max()
        
        # 🕯️ AI Candlestick Engine
        curr_O, curr_C, curr_H, curr_L = df['open'].iloc[-1], df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
        prev_O, prev_C = df['open'].iloc[-2], df['close'].iloc[-2]
        
        curr_body = abs(curr_C - curr_O)
        curr_upper_shadow = curr_H - max(curr_C, curr_O)
        curr_lower_shadow = min(curr_C, curr_O) - curr_L
        curr_range = curr_H - curr_L if (curr_H - curr_L) > 0 else 0.0001 
        prev_body = abs(prev_C - prev_O)
        
        pattern_text = "Normal"
        pattern_type = "NEUTRAL"
        if curr_lower_shadow >= 2 * curr_body and curr_upper_shadow <= 0.2 * curr_body: pattern_type = "BULLISH"
        elif curr_upper_shadow >= 2 * curr_body and curr_lower_shadow <= 0.2 * curr_body: pattern_type = "BEARISH"
        elif prev_C < prev_O and curr_C > curr_O and curr_C >= prev_O and curr_O <= prev_C and curr_body > prev_body: pattern_type = "BULLISH"
        elif prev_C > prev_O and curr_C < curr_O and curr_C <= prev_O and curr_O >= prev_C and curr_body > prev_body: pattern_type = "BEARISH"
        
        # 🚦 Signals
        signal_text = "WAITING..."
        css_class = "wait-glow"
        is_signal_active = False
        signal_dir = "NONE"
        
        if trend_50 == "BULLISH" and ema_bullish and macd_bullish and rsi < 65 and is_volume_high:
            signal_text = "🚀 SUPER BUY" if pattern_type == "BULLISH" else "🟢 BUY SETUP"
            css_class = "buy-glow"
            is_signal_active = True
            signal_dir = "LONG"
                
        elif trend_50 == "BEARISH" and not ema_bullish and not macd_bullish and rsi > 35 and is_volume_high:
            signal_text = "🧨 SUPER SELL" if pattern_type == "BEARISH" else "🔴 SELL SETUP"
            css_class = "sell-glow"
            is_signal_active = True
            signal_dir = "SHORT"
                
        return {
            'price': curr_price, 'signal': signal_text, 'css': css_class, 'dir': signal_dir,
            'df': df, 'sup': local_support, 'res': local_resistance, 'trend': trend_50, 
            'is_signal_active': is_signal_active
        }
    except Exception as e: return None

# Fetch Data
radars = {
    "BTC": fetch_coin_radar("BTC/USDT"),
    "ETH": fetch_coin_radar("ETH/USDT"),
    "SOL": fetch_coin_radar("SOL/USDT"),
    "DOGE": fetch_coin_radar("DOGE/USDT")
}

# ================= 🤖 AUTO-TRADING ENGINE =================
for coin, data in radars.items():
    if not data: continue
    current_price = data['price']
    
    # 1. Check Exits (Target or Stop Loss Hit)
    if coin in st.session_state.bot_positions:
        pos = st.session_state.bot_positions[coin]
        close_trade = False
        reason = ""
        
        if pos['dir'] == "LONG":
            if current_price >= pos['tp']: close_trade, reason = True, "🎯 TP Hit"
            elif current_price <= pos['sl']: close_trade, reason = True, "🛑 SL Hit"
            elif data['dir'] == "SHORT": close_trade, reason = True, "🔄 Signal Reversed"
        elif pos['dir'] == "SHORT":
            if current_price <= pos['tp']: close_trade, reason = True, "🎯 TP Hit"
            elif current_price >= pos['sl']: close_trade, reason = True, "🛑 SL Hit"
            elif data['dir'] == "LONG": close_trade, reason = True, "🔄 Signal Reversed"
            
        if close_trade:
            # PnL Calculation (With 10x Virtual Leverage for visibility)
            leverage = 10
            if pos['dir'] == "LONG":
                pnl_pct = ((current_price - pos['entry']) / pos['entry']) * leverage
            else:
                pnl_pct = ((pos['entry'] - current_price) / pos['entry']) * leverage
                
            gross_pnl_inr = pos['invested_inr'] * pnl_pct
            fee_inr = pos['invested_inr'] * FEE_RATE * 2 # Open + Close fee
            net_pnl_inr = gross_pnl_inr - fee_inr
            
            st.session_state.bot_balance_inr += (pos['invested_inr'] + net_pnl_inr)
            
            # Log History
            st.session_state.bot_history.insert(0, {
                'time': datetime.now().strftime("%H:%M:%S"),
                'coin': coin, 'dir': pos['dir'], 'reason': reason,
                'pnl': net_pnl_inr, 'bal': st.session_state.bot_balance_inr
            })
            del st.session_state.bot_positions[coin] # Remove position
            st.toast(f"{coin} Trade Closed: {reason} | PnL: ₹{net_pnl_inr:.2f}", icon="🤖")

    # 2. Check Entries (If no open position for this coin)
    if coin not in st.session_state.bot_positions and data['is_signal_active']:
        invest_amount = st.session_state.bot_balance_inr * 0.10 # Bot uses 10% of balance per trade
        
        if invest_amount > 50: # Minimum 50 INR required to trade
            st.session_state.bot_balance_inr -= invest_amount
            
            # Set TP/SL
            tp = data['res'] if data['dir'] == "LONG" else data['sup']
            sl = data['sup'] if data['dir'] == "LONG" else data['res']
            
            st.session_state.bot_positions[coin] = {
                'dir': data['dir'], 'entry': current_price, 
                'invested_inr': invest_amount, 'tp': tp, 'sl': sl
            }
            st.toast(f"{coin} {data['dir']} Trade Opened automatically!", icon="🚀")

# ================= 📊 BOT DASHBOARD UI =================
st.markdown(f"""
    <div class="bot-panel">
        <h3 style="margin-top:0; color:#00BFFF; text-align:center;">🤖 PAPER TRADING PORTFOLIO</h3>
        <div style="display:flex; justify-content:space-around; text-align:center; margin-top:15px;">
            <div>
                <div style="color:#848E9C; font-size:14px;">Total Wallet Balance</div>
                <div style="font-size:32px; font-weight:bold; color:{'#00FF00' if st.session_state.bot_balance_inr >= 1000 else '#FF0000'};">₹{st.session_state.bot_balance_inr:,.2f}</div>
            </div>
            <div>
                <div style="color:#848E9C; font-size:14px;">Active Trades</div>
                <div style="font-size:32px; font-weight:bold; color:#FCD535;">{len(st.session_state.bot_positions)}</div>
            </div>
            <div>
                <div style="color:#848E9C; font-size:14px;">Net Profit/Loss</div>
                <div style="font-size:32px; font-weight:bold; color:{'#00FF00' if st.session_state.bot_balance_inr >= 1000 else '#FF0000'};">₹{st.session_state.bot_balance_inr - 1000:,.2f}</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

col_pos, col_hist = st.columns(2)
with col_pos:
    st.markdown("#### 🟢 Active Positions")
    if not st.session_state.bot_positions:
        st.write("No active trades. Waiting for signals...")
    else:
        for c, p in st.session_state.bot_positions.items():
            curr_p = radars[c]['price']
            st.info(f"**{c}** | {p['dir']} | Entry: ${p['entry']:.2f} | Current: ${curr_p:.2f}\n\nInvested: ₹{p['invested_inr']:.2f} | TP: ${p['tp']:.2f} | SL: ${p['sl']:.2f}")

with col_hist:
    st.markdown("#### 📜 Trade History")
    if not st.session_state.bot_history:
        st.write("No trades closed yet.")
    else:
        for h in st.session_state.bot_history[:5]: # Show last 5 trades
            color = "green" if h['pnl'] > 0 else "red"
            st.markdown(f"**{h['time']} | {h['coin']} {h['dir']}** -> {h['reason']} | PnL: <span style='color:{color}; font-weight:bold;'>₹{h['pnl']:.2f}</span>", unsafe_allow_html=True)

st.markdown("---")

# Navigation & Chart (Same as before)
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
def get_btn(emoji, name, radar): return f"{emoji} {name}\n${radar['price']:,.2f}" if radar else f"{name} Error"
with m_col1:
    if st.button(get_btn("👑", "BTC", radars["BTC"])): st.session_state.active_coin = "BTC/USDT"
with m_col2:
    if st.button(get_btn("💠", "ETH", radars["ETH"])): st.session_state.active_coin = "ETH/USDT"
with m_col3:
    if st.button(get_btn("🚀", "SOL", radars["SOL"])): st.session_state.active_coin = "SOL/USDT"
with m_col4:
    if st.button(get_btn("🐕", "DOGE", radars["DOGE"])): st.session_state.active_coin = "DOGE/USDT"

active_data = radars[st.session_state.active_coin.split("/")[0]]
if active_data:
    st.markdown(f"<h3 style='text-align:center; color:#FCD535;'>{st.session_state.active_coin} Live Chart</h3>", unsafe_allow_html=True)
    fig = go.Figure(data=[go.Candlestick(x=active_data['df'].index, open=active_data['df']['open'], high=active_data['df']['high'], low=active_data['df']['low'], close=active_data['df']['close'], name='Price')])
    fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_9'], name='EMA 9', line=dict(color='#00BFFF', width=2)))
    fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_20'], name='EMA 20', line=dict(color='#FF8C00', width=2)))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

if auto_refresh:
    time.sleep(15)
    st.rerun()
