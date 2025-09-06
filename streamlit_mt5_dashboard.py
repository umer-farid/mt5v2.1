import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

from mt5_init import initialize_mt5
from config import setup_page, sidebar_controls, top_controls
from mt5_helpers import get_positions_df, analyze_symbol
from ui import display_symbol_tab
from autotrade import run_autotrade
from strategies.simple_autotrader import SimpleAutoTrader
#from strategies.atr_trailer import ATRTrailingStop
from strategies.candle_trailer import CandleTrailingStop



def main():
    # -----------------------
    # MT5 init and page setup
    # -----------------------
    mt5 = initialize_mt5()
    setup_page()

    all_symbols = [s.name for s in mt5.symbols_get()]
    if not all_symbols:
        st.error("⚠️ No symbols returned from MT5. Check the terminal and Market Watch.")
        st.stop()

    # -----------------------
    # Sidebar controls
    # -----------------------
    refresh_seconds, lot_size, default_sl_points, default_tp_points = sidebar_controls()
    timeframe, timeframe_choice, num_candles, selected_symbols = top_controls(all_symbols)

    # -----------------------
    # Auto-refresh
    # -----------------------
    st_autorefresh(interval=refresh_seconds * 1000, key="auto_refresher")

    # -----------------------
    # Session state initialization
    # -----------------------

    if "last_trade" not in st.session_state:
        st.session_state.last_trade = {}
    if "autotrade" not in st.session_state:
        st.session_state.autotrade = {}
    if "execution_logs" not in st.session_state:
        st.session_state.execution_logs = []
    if "autotrade_logs" not in st.session_state:
        st.session_state.autotrade_logs = []

    for s in selected_symbols:
        st.session_state.last_trade.setdefault(s, None)
        st.session_state.autotrade.setdefault(s, True)

    # -----------------------
    # Symbol tabs
    # -----------------------
    if not selected_symbols:
        st.info("Select symbols above to create tabs for each symbol.")
    else:
        tabs = st.tabs(selected_symbols)
        for i, symbol in enumerate(selected_symbols):
            with tabs[i]:
                levels, df = analyze_symbol(symbol, timeframe, num_candles)
                if levels is None:
                    st.warning("No candle data for this symbol (open in Market Watch & try again).")
                    continue

                # Display chart, calculation table, positions, and trade controls
                suggested_tp_points, point = display_symbol_tab(
                    symbol, levels, df, timeframe_choice,
                    lot_size, default_tp_points, default_sl_points
                )

                # -----------------------
                # Auto-trade logic
                # -----------------------
                if st.session_state.autotrade.get(symbol, False):
                    run_autotrade(
                        symbol,
                        float(df["close"].iloc[-1]),
                        levels,
                        lot_size,
                        suggested_tp_points,
                        point,
                        default_tp_points,
                        default_sl_points
                    )
                   
                    # ✅ ATR trailing stop-loss only
                    #atr_trailer = ATRTrailingStop(symbol, timeframe, atr_period=14, atr_mult=2.0)
                    #atr_trailer.run()
                    # ✅ Candle-based trailing stop (BE after 20 pips, trail after 3 candles)
                    candle_trailer = CandleTrailingStop(
                        symbol=symbol,
                        timeframe=timeframe,
                        profit_trigger_pips=20,
                        lookback_candles=3
                    )
                    candle_trailer.run()

                   

    # -----------------------
    # Global positions
    # -----------------------
    df_pos_all = get_positions_df()
    st.markdown("---")
    st.subheader("All Open Positions (global)")
    if df_pos_all.empty:
        st.info("No open positions.")
    else:
        cols_to_show = [
            c for c in
            ["ticket", "symbol", "volume", "type", "price_open", "sl", "tp", "price_current", "profit"]
            if c in df_pos_all.columns
        ]
        df_show = df_pos_all[cols_to_show].copy()
        if "type" in df_show.columns:
            df_show["type"] = df_show["type"].map({0: "BUY", 1: "SELL"}).fillna(df_show["type"])
        st.dataframe(df_show.style.format(precision=2), use_container_width=True)

    # -----------------------
    # Build logs HTML
    # -----------------------
    logs_html = ""
    checks_html = ""

    # Execution logs (max 10, with spacing)
    if st.session_state.get("execution_logs"):
        for log in reversed(st.session_state.execution_logs[-50:]):
            logs_html += f"<div style='margin-bottom:10px; color:{log.get('color','white')};'>[{log['time']}] {log['msg']}</div>"
    else:
        logs_html = "<p style='color:#22db22'>No executed trades yet.</p>"

    # Auto-trade checks (with separators, more entries allowed)
    if st.session_state.get("autotrade_logs"):
        for log in reversed(st.session_state.autotrade_logs[-50:]):
            if log.get("msg") == "----------------":
                checks_html += "<div style='color:gray; margin:8px 0;'>----------------</div>"
            else:
                checks_html += f"<div style='margin-bottom:4px; color:{log.get('color','yellow')};border-bottom: 1px dotted #888; padding-bottom:5px;'>[{log['time']}] {log['msg']}</div>"
    else:
        checks_html = "<p style='color:#999'>No checks yet.</p>"

    # -----------------------
    # Account info (for embedding into same block)
    # -----------------------
    account_info = mt5.account_info()
    if account_info:
        balance_str = f"{account_info.balance:,.2f}"
        equity_str = f"{account_info.equity:,.2f}"
        margin_str = f"{account_info.margin:,.2f}"
        total_pnl_val = account_info.profit
        total_pnl_str = f"{total_pnl_val:,.2f}"
        pnl_color = "blue" if total_pnl_val >= 0 else "red"
        pnl_label = "📈 Profit" if total_pnl_val >= 0 else "📉 Loss"
    else:
        balance_str = equity_str = margin_str = total_pnl_str = "N/A"
        pnl_color = "gray"
        pnl_label = "Account"

    # -----------------------
    # Single HTML block: checkbox + toolbar + toggle label + account bar
    # (CSS-only toggle using hidden checkbox, very fast)
    # -----------------------
    st.markdown(
        f"""
        <style>
        /* toolbar container */
        #toolbar-toggle-checkbox {{ display: none; }}

        .right-toolbar {{
            position: fixed;
            top: 70px;
            right: 0;
            width: 350px;
            height: calc(100% - 70px);
            background-color: #1e1e1e;
            border-left: 2px solid #333;
            display: flex;
            flex-direction: column;
            padding: 10px;
            z-index: 999;
            transition: width 0.20s ease, padding 0.20s ease;
            box-sizing: border-box;
        }}
        /* collapsed state when checkbox checked */
        #toolbar-toggle-checkbox:checked + .right-toolbar {{
            width: 0;
            padding: 0;
            border-left: none;
            overflow: hidden;
        }}

        .terminal-box {{
            background-color: #111111;
            padding: 8px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 13px;
            color: #00ff00;
            overflow-y: auto;
            box-sizing: border-box;
        }}
        .execution-log {{ flex: 1; margin-bottom: 8px; }}
        .check-log {{ flex: 1; }}

        /* the visible toggle label */
        .toolbar-toggle {{
            position: fixed;
            top: 50%;
            right: 320px;
            transform: translateY(-50%);
            background-color: #333;
            color: white;
            padding: 6px 10px;
            border-radius: 4px 0 0 4px;
            cursor: pointer;
            z-index: 1000;
            font-size: 16px;
            font-weight: bold;
            display: inline-block;
            user-select: none;
        }}
        /* default symbol « for hide */
        .toolbar-toggle::after {{ content: '«'; }}

        /* when checked (collapsed) change to » */
        #toolbar-toggle-checkbox:checked + .right-toolbar + .toolbar-toggle::after {{ content: '»'; }}

        /* account bar positioning adjusts based on checkbox */
        #account-bar {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 320px;
            background-color: #f9f9f9;
            border-top: 2px solid #ddd;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: sans-serif;
            z-index: 998;
            transition: right 0.20s ease;
            box-sizing: border-box;
        }}
        #toolbar-toggle-checkbox:checked ~ #account-bar {{
            right: 0;
        }}

        /* small responsiveness for narrow screens */
        @media (max-width: 900px) {{
            .right-toolbar {{ width: 260px; }}
            .toolbar-toggle {{ right: 260px; }}
            #account-bar {{ right: 260px; }}
            #toolbar-toggle-checkbox:checked + .right-toolbar + .toolbar-toggle::after {{ content: '»'; }}
            #toolbar-toggle-checkbox:checked ~ #account-bar {{ right: 0; }}
        }}
        </style>

        <!-- hidden checkbox controls state -->
        <input id="toolbar-toggle-checkbox" type="checkbox">

        <!-- the toolbar itself (immediately after checkbox for adjacent selector) -->
        <div class="right-toolbar">
            <div class="terminal-box execution-log">
                <h4 style='margin:0; color:white;'>📜 Execution Log</h4>
                <hr style='border:1px solid gray;'>
                {logs_html}
            </div>
            <div class="terminal-box check-log">
                <h4 style='margin:0; color:white;'>🔍 Auto-Trade Checks</h4>
                <hr style='border:1px solid gray;'>
                {checks_html}
            </div>
        </div>

        <!-- label toggles the checkbox (sits after the toolbar so CSS selectors match) -->
        <label class="toolbar-toggle" for="toolbar-toggle-checkbox"></label>

        <!-- account bar (sibling of checkbox so CSS can move it) -->
        <div id="account-bar">
            <div style="display:flex; gap:18px; align-items:center;">
                <div style="text-align:center;">
                    <div style="font-size:14px;color:gray;">💰 Balance</div>
                    <div style="font-size:18px;font-weight:bold;">{balance_str}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:14px;color:gray;">📊 Equity</div>
                    <div style="font-size:18px;font-weight:bold;">{equity_str}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:14px;color:gray;">📉 Margin</div>
                    <div style="font-size:18px;font-weight:bold;">{margin_str}</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:14px;color:gray;">{pnl_label}</div>
                    <div style="font-size:18px;font-weight:bold;color:{pnl_color};">{total_pnl_str}</div>
                </div>
            </div>
            <div style="font-size:13px;color:gray;white-space:nowrap;">
                © Umer Farid ™ | All Rights Reserved
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------
    # done
    # -----------------------

if __name__ == "__main__":
    main()
