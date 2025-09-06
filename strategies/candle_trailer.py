import MetaTrader5 as mt5
from datetime import datetime
import streamlit as st
import pandas as pd
from mt5_helpers import update_order_sl_tp


class CandleTrailingStop:
    def __init__(self, symbol, timeframe=mt5.TIMEFRAME_M1,
                 profit_trigger_pips=20, lookback_candles=3):
        """
        Candle-based trailing stop:
        - symbol: trading pair (e.g., 'EURUSD')
        - timeframe: MT5 timeframe (default M1)
        - profit_trigger_pips: set BE SL after this many pips
        - lookback_candles: trailing uses last N candles high/low
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.profit_trigger_pips = profit_trigger_pips
        self.lookback_candles = lookback_candles

    def run(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if not positions:
            return

        tick = mt5.symbol_info_tick(self.symbol)
        point = mt5.symbol_info(self.symbol).point

        # Get last N+1 candles for trailing calc
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 1, self.lookback_candles)
        if rates is None or len(rates) < self.lookback_candles:
            return
        df = pd.DataFrame(rates)

        for pos in positions:
            if pos.type == 0:  # BUY
                profit_pips = (tick.bid - pos.price_open) / point

                # Step 1: Move to BE if profit ≥ trigger
                if profit_pips >= self.profit_trigger_pips and (pos.sl == 0 or pos.sl < pos.price_open):
                    update_order_sl_tp(pos.ticket, pos.price_open, pos.tp)
                    st.session_state.execution_logs.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "msg": f"🔵 {self.symbol} BUY moved SL → BE @ {pos.price_open:.5f}",
                        "color": "blue"
                    })

                # Step 2: Trail to lowest low of last N candles
                if profit_pips >= self.profit_trigger_pips:
                    new_sl = df["low"].min()
                    if new_sl > (pos.sl or 0):
                        update_order_sl_tp(pos.ticket, new_sl, pos.tp)
                        st.session_state.execution_logs.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "msg": f"🔵 {self.symbol} BUY trailing SL → {new_sl:.5f} ({profit_pips:.1f} pips)",
                            "color": "blue"
                        })

            elif pos.type == 1:  # SELL
                profit_pips = (pos.price_open - tick.ask) / point

                # Step 1: Move to BE if profit ≥ trigger
                if profit_pips >= self.profit_trigger_pips and (pos.sl == 0 or pos.sl > pos.price_open):
                    update_order_sl_tp(pos.ticket, pos.price_open, pos.tp)
                    st.session_state.execution_logs.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "msg": f"🔴 {self.symbol} SELL moved SL → BE @ {pos.price_open:.5f}",
                        "color": "red"
                    })

                # Step 2: Trail to highest high of last N candles
                if profit_pips >= self.profit_trigger_pips:
                    new_sl = df["high"].max()
                    if new_sl < (pos.sl or 999999):  # if SL is higher, move it down
                        update_order_sl_tp(pos.ticket, new_sl, pos.tp)
                        st.session_state.execution_logs.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "msg": f"🔴 {self.symbol} SELL trailing SL → {new_sl:.5f} ({profit_pips:.1f} pips)",
                            "color": "red"
                        })
