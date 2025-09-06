import streamlit as st
import pytz

tz = pytz.timezone("Asia/Karachi")

def setup_page():
    st.set_page_config(page_title="Bloomberg Terminal V2", layout="wide")
    st.title("Bloomberg Terminal V2")

    # Quote with custom spacing
    st.markdown("""
    <div style='margin-top: -15px; margin-bottom: 25px; color: gray; font-style: italic; font-size: 16px;'><h4>
        “Trade with discipline, not with emotions.”</h4>
    </div>
""", unsafe_allow_html=True)
def sidebar_controls():
    with st.sidebar:
        st.header("App Controls")
        refresh_seconds = st.number_input("Auto-refresh interval (seconds)", min_value=2, max_value=60, value=6)
        lot_size = st.number_input("Default Lot Size", min_value=0.01, step=0.01, value=0.01)
        default_sl_points = st.number_input("Default SL (points, 0 = no SL)", min_value=0, value=0, step=1)
        default_tp_points = st.number_input("Default TP (points, 0 = auto from levels)", min_value=0, value=0, step=1)
        #st.markdown("---")
       # st.write("Symbols are loaded from your MT5 terminal (Market Watch).")
        #st.write("Test with demo account. Auto-trade will place live orders when enabled.")
    return refresh_seconds, lot_size, default_sl_points, default_tp_points

def top_controls(all_symbols):
    import MetaTrader5 as mt5
    col1, col2 = st.columns([2, 1])
    with col1:
        timeframe_map = {
            "1 Minute": mt5.TIMEFRAME_M1,
            "5 Minutes": mt5.TIMEFRAME_M5,
            "15 Minutes": mt5.TIMEFRAME_M15,
            "1 Hour": mt5.TIMEFRAME_H1,
            "4 Hours": mt5.TIMEFRAME_H4,
            "1 Day": mt5.TIMEFRAME_D1
        }
        timeframe_choice = st.selectbox("Timeframe", list(timeframe_map.keys()), index=0)
        timeframe = timeframe_map[timeframe_choice]

        num_candles = st.slider("Number of candles to fetch",min_value=20, max_value=800, value=200)
        selected_symbols = st.multiselect(
            "Select symbols to analyze (choose from MT5 Market Watch)",
            options=all_symbols,
            #default=[s for s in ["XAUUSDm","GBPJPYm","GBPUSDm", "USDJPYm","EURUSDm"] if s in all_symbols]
            default=[s for s in ["BTCUSDm"] if s in all_symbols]
        )
    with col2:
        positions_all = mt5.positions_get()
        total_open = len(positions_all) if positions_all is not None else 0
        st.metric("Open Positions (total)", total_open)
    return timeframe, timeframe_choice, num_candles, selected_symbols
