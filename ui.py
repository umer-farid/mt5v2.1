import streamlit as st
import pandas as pd
from charts import plot_candlestick
from mt5_helpers import get_positions_for_symbol, estimate_profit_usd, safe_symbol_info, pip_and_point, place_order_safe
from autotrade import run_autotrade

def display_symbol_tab(symbol, levels, df, timeframe_choice, lot_size, default_tp_points, default_sl_points):
    """
    Display a symbol tab including chart, calculation table, positions,
    and trade controls (manual + auto-trade toggle).
    """
    last_price = float(df["close"].iloc[-1])

    # -----------------------
    # Chart
    # -----------------------
    plot_candlestick(symbol, df, levels, last_price, timeframe_choice, key=f"chart_{symbol}")

    # -----------------------
    # Calculation table
    # -----------------------
    st.subheader("Calculation Table")
    st.dataframe(pd.DataFrame({k:[v] for k,v in levels.items()}).style.format(precision=5), use_container_width=True)

    # -----------------------
    # Symbol-specific open positions
    # -----------------------
    st.subheader("Open Positions (this symbol)")
    df_sym_pos = get_positions_for_symbol(symbol)
    if df_sym_pos.empty:
        st.info("No open positions for this symbol.")
    else:
        st.dataframe(df_sym_pos.style.format(precision=2), use_container_width=True)

    # -----------------------
    # TP calculation
    # -----------------------
    info = safe_symbol_info(symbol)
    point, pip = pip_and_point(symbol)

    suggested_tp_points = None
    tp_pips = None
    est_profit = None
    if levels["Resistance1"] is not None:
        suggested_tp_points = abs(levels["Resistance1"] - levels["Buy1"]) / point
        
        tp_pips = suggested_tp_points
        est_profit = estimate_profit_usd(symbol, suggested_tp_points, lot_size)

    # -----------------------
    # Trade Controls & Info
    # -----------------------
    st.subheader("Trade Controls & Info")
    colA, colB, colC = st.columns([1,1,1])
    with colA:
        st.write(f"Last Price: {last_price:.5f}")
        if tp_pips is not None:
         st.markdown(f"""
        **Full TP (calc):** {suggested_tp_points:.1f} points  
        **Applied TP (½ of full):** {tp_pips:.1f} points (≈ {tp_pips * pip:.5f} price units)  
        **Est. Profit (approx):** ${est_profit:.2f} (lot={lot_size})
        """)
        else:
            st.write("Suggested TP: N/A")


    # --- Column B: Auto-trade toggle & manual trade buttons
    with colB:
        autotrade_toggle = st.checkbox(
            "Enable Auto-Trade for this symbol",
            value=st.session_state.autotrade.get(symbol, True),
            key=f"autotrade_{symbol}"
        )
        st.session_state.autotrade[symbol] = autotrade_toggle

        # Manual BUY
        if st.button(f"Place BUY {symbol}", key=f"manual_buy_{symbol}"):
            tp_points_use = int(suggested_tp_points) if suggested_tp_points and suggested_tp_points > 0 else int(default_tp_points or 50)
            tp_price = last_price + tp_points_use * point
            res = place_order_safe(symbol, lot_size, "BUY", default_sl_points, tp_price)
            st.write("Order result:", res)
            st.session_state.last_trade[symbol] = f"BUY @{last_price:.5f} TP={tp_points_use} pts"

        # Manual SELL
        if st.button(f"Place SELL {symbol}", key=f"manual_sell_{symbol}"):
            tp_points_use = int(suggested_tp_points) if suggested_tp_points and suggested_tp_points > 0 else int(default_tp_points or 50)
            tp_price = last_price - tp_points_use * point
            res = place_order_safe(symbol, lot_size, "SELL", default_sl_points, tp_price)
            st.write("Order result:", res)
            st.session_state.last_trade[symbol] = f"SELL @{last_price:.5f} TP={tp_points_use} pts"

    # --- Column C: Last executed trade
    with colC:
        last_trade = st.session_state.last_trade.get(symbol)
        st.write("Last executed trade (session):")
        st.info(last_trade if last_trade else "No trade executed this session for symbol")

    return suggested_tp_points, point
