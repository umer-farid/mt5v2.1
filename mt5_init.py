import MetaTrader5 as mt5
import streamlit as st

def initialize_mt5():
    if not mt5.initialize():
        st.error("❌ MT5 initialization failed. Make sure MetaTrader5 terminal is running and logged in.")
        st.stop()
    return mt5
