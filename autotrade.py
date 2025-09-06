import streamlit as st 
from datetime import datetime
from mt5_helpers import place_order_safe

def run_autotrade(symbol, last_price, levels, lot_size, suggested_tp_points, point, default_tp_points, default_sl_points):
    previous_state_key = f"prev_price_{symbol}"
    prev_price = st.session_state.get(previous_state_key, None)
    triggered = False

    buy_level = levels["Buy1"]
    sell_level = levels["PHH"] or levels["HH"]

    # Debug log
    st.session_state.autotrade_logs.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "msg": f"Check {symbol}: prev={prev_price}, last={last_price}, buy={buy_level}, sell={sell_level}",
        "color": "yellow"
    })

    # ---------------- BUY condition ----------------
    if buy_level is not None and prev_price is not None and prev_price <= buy_level and last_price > buy_level:
        if st.session_state.last_trade.get(symbol) != "BUY":
            tp_points_use = int(suggested_tp_points * 0.6) if suggested_tp_points and suggested_tp_points > 0 else int(default_tp_points or 50)
            tp_price = last_price + tp_points_use * point

            # ✅ place order WITHOUT SL
            result = place_order_safe(symbol, lot_size, "BUY", 0, tp_price)
            st.session_state.last_trade[symbol] = f"BUY @{last_price:.5f} TP={tp_points_use} pts"

            st.session_state.execution_logs.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "msg": f"✅ BUY {symbol} @{last_price:.5f} TP={tp_points_use} pts",
                "color": "blue"
            })
            triggered = True

    # ---------------- SELL condition ----------------
    if not triggered and sell_level is not None and prev_price is not None and prev_price >= sell_level and last_price < sell_level:
        if st.session_state.last_trade.get(symbol) != "SELL":
            tp_points_use = int(suggested_tp_points * 0.6) if suggested_tp_points and suggested_tp_points > 0 else int(default_tp_points or 50)
            tp_price = last_price - tp_points_use * point

            # ✅ place order WITHOUT SL
            result = place_order_safe(symbol, lot_size, "SELL", 0, tp_price)
            st.session_state.last_trade[symbol] = f"SELL @{last_price:.5f} TP={tp_points_use} pts"

            st.session_state.execution_logs.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "msg": f"✅ SELL {symbol} @{last_price:.5f} TP={tp_points_use} pts",
                "color": "red"
            })

    # Save current price for next tick
    st.session_state[previous_state_key] = last_price
