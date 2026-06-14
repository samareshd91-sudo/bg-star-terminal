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
    .brand-title { font-size: 32px; font-weight: 900; background: -webkit-linear-gradient(45deg, #00BFFF, #00FF88); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 0px; }
    .sub-title { text-align: center; color: #848E9C; font-size: 13px; margin-bottom: 15px; text-transform: uppercase; }
    
    /* Info Cards */
    .wallet-card { background: linear-gradient(135deg, #181A20 0%, #1E2329 100%); border: 1px solid #2B3139; border-radius: 12px; padding: 20px; text-align: center; }
    .wallet-val { font-size: 28px; font-weight: bold; margin-top: 5px; }
    
    .pos-card { background-color: #181A20; border-left: 4px solid #FCD535; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
    .pos-long { border-left-color: #00FF00; }
    .pos-short { border-left-color: #FF0000; }
    
    .buy-glow { color: #00FF00; font-weight: 900; }
    .sell-glow { color: #FF0000; font-weight: 900; }
    
    hr { border-color: #2B3139; margin: 15px 0; }
    </style>
""", unsafe_allow_html=True)

exchange = ccxt.kucoin({'enableRateLimit': True})
selected_tf = "15m" 
FEE_RATE = 0.0005 # 0.05% Exchange Fee
VIRTUAL_LEVERAGE = 10 # 10x Leverage for realistic paper trading

# ================= 🧠 Bot Memory Setup (Paper Trading) =================
if 'active_coin' not in st.session_state: st.session_state.active_coin = "BTC/USDT"
if 'total_balance_inr' not in st.session_state: st.session_state.total_balance_inr = 1000.0
if 'available_balance_inr' not in st.session_state: st.session_state.available_balance_inr = 1000.0
if 'bot_positions' not in st.session_state: st.session_state.bot_positions = {} 
if 'bot_history' not in st.session_state: st.session_state.bot_history = [] 

st.markdown('<div class="brand-title">BG STAR PAPER TRADING AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">🟢 LIVE AUTO-EXECUTION ENGINE | ₹1000 INR VIRTUAL PORTFOLIO</div>', unsafe_allow_html=True)

col_toggle1, col_toggle2, col_toggle3 = st.columns([1, 2, 1])
with col_toggle2:
    auto_refresh = st.toggle("🟢 Auto-Trading & Refresh Active (প্রতি ১৫ সেকেন্ডে আপডেট হবে)", value=True)

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
        
        pattern_text = "সাধারণ (Normal)"
        pattern_type = "NEUTRAL"
        if curr_lower_shadow >= 2 * curr_body and curr_upper_shadow <= 0.2 * curr_body: pattern_text, pattern_type = "হ্যামার (BULLISH)", "BULLISH"
        elif curr_upper_shadow >= 2 * curr_body and curr_lower_shadow <= 0.2 * curr_body: pattern_text, pattern_type = "শুটিং স্টার (BEARISH)", "BEARISH"
        elif prev_C < prev_O and curr_C > curr_O and curr_C >= prev_O and curr_O <= prev_C and curr_body > prev_body: pattern_text, pattern_type = "বুলিশ এনগাল্ফিং", "BULLISH"
        elif prev_C > prev_O and curr_C < curr_O and curr_C <= prev_O and curr_O >= prev_C and curr_body > prev_body: pattern_text, pattern_type = "বেয়ারিশ এনগাল্ফিং", "BEARISH"
        
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
            'is_signal_active': is_signal_active, 'pattern': pattern_text, 'rsi': rsi
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
    
    # 1. Manage Active Positions (Check Exits)
    if coin in st.session_state.bot_positions:
        pos = st.session_state.bot_positions[coin]
        close_trade = False
        reason = ""
        
        # Calculate Live PnL
        if pos['dir'] == "LONG":
            pnl_pct = ((current_price - pos['entry']) / pos['entry']) * VIRTUAL_LEVERAGE
            if current_price >= pos['tp']: close_trade, reason = True, "🎯 TP Hit (Profit)"
            elif current_price <= pos['sl']: close_trade, reason = True, "🛑 SL Hit (Loss)"
            elif data['dir'] == "SHORT": close_trade, reason = True, "🔄 Signal Reversed"
        else:
            pnl_pct = ((pos['entry'] - current_price) / pos['entry']) * VIRTUAL_LEVERAGE
            if current_price <= pos['tp']: close_trade, reason = True, "🎯 TP Hit (Profit)"
            elif current_price >= pos['sl']: close_trade, reason = True, "🛑 SL Hit (Loss)"
            elif data['dir'] == "LONG": close_trade, reason = True, "🔄 Signal Reversed"
            
        pos['live_pnl'] = pos['invested_inr'] * pnl_pct
            
        if close_trade:
            gross_pnl_inr = pos['live_pnl']
            fee_inr = pos['invested_inr'] * FEE_RATE * 2 # Open + Close fee
            net_pnl_inr = gross_pnl_inr - fee_inr
            
            # Update Balances
            st.session_state.available_balance_inr += pos['invested_inr'] + net_pnl_inr
            st.session_state.total_balance_inr = st.session_state.available_balance_inr + sum(p['invested_inr'] for k, p in st.session_state.bot_positions.items() if k != coin)
            
            # Log History
            st.session_state.bot_history.insert(0, {
                'time': datetime.now().strftime("%H:%M:%S"),
                'coin': coin, 'dir': pos['dir'], 'entry': pos['entry'], 'exit': current_price,
                'reason': reason, 'pnl': net_pnl_inr, 'fee': fee_inr
            })
            del st.session_state.bot_positions[coin]
            st.toast(f"Trade Closed: {coin} | {reason} | PnL: ₹{net_pnl_inr:.2f}", icon="✅")

    # 2. Take New Entries
    if coin not in st.session_state.bot_positions and data['is_signal_active']:
        invest_amount = st.session_state.total_balance_inr * 0.10 # Bot uses 10% of total portfolio
        
        if st.session_state.available_balance_inr >= invest_amount and invest_amount > 10:
            st.session_state.available_balance_inr -= invest_amount
            
            tp = data['res'] if data['dir'] == "LONG" else data['sup']
            sl = data['sup'] if data['dir'] == "LONG" else data['res']
            
            st.session_state.bot_positions[coin] = {
                'dir': data['dir'], 'entry': current_price, 
                'invested_inr': invest_amount, 'tp': tp, 'sl': sl, 'live_pnl': 0.0
            }
            st.toast(f"New Trade Executed: {coin} {data['dir']} at ${current_price:,.2f}", icon="🚀")

# Recalculate Total Balance (Available + Invested + Live Unrealized PnL)
active_invested = sum(p['invested_inr'] for p in st.session_state.bot_positions.values())
unrealized_pnl = sum(p['live_pnl'] for p in st.session_state.bot_positions.values())
st.session_state.total_balance_inr = st.session_state.available_balance_inr + active_invested + unrealized_pnl

# ================= 📊 TOP WALLET DASHBOARD =================
w_col1, w_col2, w_col3, w_col4 = st.columns(4)
with w_col1:
    st.markdown(f"""<div class="wallet-card"><div style="color:#848E9C; font-size:14px;">Total Portfolio (INR)</div>
        <div class="wallet-val" style="color:{'#00FF00' if st.session_state.total_balance_inr >= 1000 else '#FF0000'};">₹{st.session_state.total_balance_inr:,.2f}</div></div>""", unsafe_allow_html=True)
with w_col2:
    st.markdown(f"""<div class="wallet-card"><div style="color:#848E9C; font-size:14px;">Available Cash</div>
        <div class="wallet-val" style="color:#EAECEF;">₹{st.session_state.available_balance_inr:,.2f}</div></div>""", unsafe_allow_html=True)
with w_col3:
    st.markdown(f"""<div class="wallet-card"><div style="color:#848E9C; font-size:14px;">Locked in Trades</div>
        <div class="wallet-val" style="color:#FCD535;">₹{active_invested:,.2f}</div></div>""", unsafe_allow_html=True)
with w_col4:
    net_profit = st.session_state.total_balance_inr - 1000
    st.markdown(f"""<div class="wallet-card"><div style="color:#848E9C; font-size:14px;">Net Profit / Loss</div>
        <div class="wallet-val" style="color:{'#00FF00' if net_profit >= 0 else '#FF0000'};">₹{net_profit:,.2f}</div></div>""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ================= 🔴 POSITIONS & HISTORY (BINANCE STYLE) =================
col_pos, col_hist = st.columns([1.2, 1])

with col_pos:
    st.markdown("<h4 style='color:#EAECEF;'>🟢 Live Positions (অ্যাক্টিভ ট্রেড)</h4>", unsafe_allow_html=True)
    if not st.session_state.bot_positions:
        st.markdown("<div style='color:#848E9C; text-align:center; padding:20px; background:#181A20; border-radius:8px;'>বট এখন সিগন্যালের জন্য অপেক্ষা করছে... কোনো রানিং ট্রেড নেই।</div>", unsafe_allow_html=True)
    else:
        for c, p in st.session_state.bot_positions.items():
            curr_p = radars[c]['price']
            card_class = "pos-long" if p['dir'] == "LONG" else "pos-short"
            pnl_color = "#00FF00" if p['live_pnl'] >= 0 else "#FF0000"
            st.markdown(f"""
                <div class="pos-card {card_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:20px; font-weight:bold; color:#EAECEF;">{c}</span> 
                            <span style="background-color:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; font-size:12px; margin-left:5px; color:{'#00FF00' if p['dir']=='LONG' else '#FF0000'};">{p['dir']} 10x</span>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:12px; color:#848E9C;">Live PnL (INR)</div>
                            <div style="font-size:20px; font-weight:bold; color:{pnl_color};">₹{p['live_pnl']:,.2f}</div>
                        </div>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-top:10px; font-size:14px; color:#848E9C;">
                        <div>Entry: <span style="color:#EAECEF;">${p['entry']:,.2f}</span><br>Current: <span style="color:#FCD535;">${curr_p:,.2f}</span></div>
                        <div style="text-align:right;">Invested: <span style="color:#EAECEF;">₹{p['invested_inr']:,.2f}</span><br>Target: <span style="color:#00FF00;">${p['tp']:,.2f}</span> | SL: <span style="color:#FF0000;">${p['sl']:,.2f}</span></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

with col_hist:
    st.markdown("<h4 style='color:#EAECEF;'>📜 Trade History (হিসাবের খাতা)</h4>", unsafe_allow_html=True)
    if not st.session_state.bot_history:
        st.markdown("<div style='color:#848E9C; text-align:center; padding:20px; background:#181A20; border-radius:8px;'>এখনো কোনো ট্রেড ক্লোজ হয়নি।</div>", unsafe_allow_html=True)
    else:
        for h in st.session_state.bot_history[:5]: # Last 5 trades
            pnl_color = "#00FF00" if h['pnl'] > 0 else "#FF0000"
            st.markdown(f"""
                <div style="background-color:#181A20; border: 1px solid #2B3139; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-weight:bold; color:#EAECEF;">{h['coin']} <span style="font-size:12px; color:#848E9C;">{h['dir']}</span></span>
                        <span style="font-weight:bold; color:{pnl_color};">₹{h['pnl']:,.2f}</span>
                    </div>
                    <div style="font-size:12px; color:#848E9C; margin-top:5px;">
                        {h['time']} | {h['reason']}<br>
                        Entry: ${h['entry']:,.2f} → Exit: ${h['exit']:,.2f} (Fee: ₹{h['fee']:.2f})
                    </div>
                </div>
            """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# Navigation & Chart 
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
    chart_col, info_col = st.columns([2.5, 1])
    
    with chart_col:
        fig = go.Figure(data=[go.Candlestick(x=active_data['df'].index, open=active_data['df']['open'], high=active_data['df']['high'], low=active_data['df']['low'], close=active_data['df']['close'], name='Price')])
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_9'], name='EMA 9', line=dict(color='#00BFFF', width=2)))
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_20'], name='EMA 20', line=dict(color='#FF8C00', width=2)))
        fig.add_trace(go.Scatter(x=active_data['df'].index, y=active_data['df']['ema_50'], name='EMA 50', line=dict(color='#FCD535', width=3, dash='dot')))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
    with info_col:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1E2329 0%, #14181C 100%); border-radius: 12px; padding: 15px; border: 1px solid #2B3139;">
            <div style="text-align:center; font-size:20px; font-weight:bold; color:#FCD535; margin-bottom:10px;">{st.session_state.active_coin}</div>
            <div class="{active_data['css']}" style="text-align:center; font-size:18px; margin-bottom:15px; background: rgba(0,0,0,0.3); padding:8px; border-radius:6px;">{active_data['signal']}</div>
            <div style="font-size:13px; color:#848E9C; line-height:2;">
                <b>🧠 বটের লজিক:</b><br>
                • <b>ট্রেন্ড (50 EMA):</b> <span style="color:#EAECEF;">{active_data['trend']}</span><br>
                • <b>ক্যান্ডেল:</b> <span style="color:#FCD535;">{active_data['pattern']}</span><br>
                • <b>RSI (14):</b> <span style="color:#EAECEF;">{active_data['rsi']:.1f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

if auto_refresh:
    time.sleep(15)
    st.rerun()
