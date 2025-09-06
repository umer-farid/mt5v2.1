import pandas as pd
import streamlit as st
from mt5_helpers import place_order_safe


class SimpleAutoTrader:
    """
    Auto-trader that executes trades at Buy1 / PHH / HH levels.
    - Places orders with lot size + stop-loss only (no TP).
    - ATR trailing stop is handled separately by atr_trailer.py.
    """

    def __init__(self, symbol, lot_size, default_sl_points):
        self.symbol = symbol
        self.lot_size = lot_size
        self.default_sl_points = default_sl_points

    def run(self, last_close, levels):
        """
        Run auto-trading checks and execute trades if levels are hit.
        Args:
            last_close (float): latest close price.
            levels (dict): dictionary with Buy1, PHH, HH levels.
        """
        now = pd.Timestamp.now().strftime("%H:%M:%S")

        # ---------------- BUY condition ----------------
        if "Buy1" in levels and last_close <= levels["Buy1"]:
            st.session_state.autotrade_logs.append({
                "time": now,
                "msg": f"📈 BUY signal at {self.symbol} (last_close={last_close:.5f} <= Buy1={levels['Buy1']:.5f})",
                "color": "cyan"
            })
            place_order_safe(
                self.symbol,
                self.lot_size,
                "BUY",
                sl_points=self.default_sl_points
            )

        # ---------------- SELL condition ----------------
        elif "PHH" in levels and last_close >= levels["PHH"]:
            st.session_state.autotrade_logs.append({
                "time": now,
                "msg": f"📉 SELL signal at {self.symbol} (last_close={last_close:.5f} >= PHH={levels['PHH']:.5f})",
                "color": "magenta"
            })
            place_order_safe(
                self.symbol,
                self.lot_size,
                "SELL",
                sl_points=self.default_sl_points
            )

        elif "HH" in levels and last_close >= levels["HH"]:
            st.session_state.autotrade_logs.append({
                "time": now,
                "msg": f"📉 SELL signal at {self.symbol} (last_close={last_close:.5f} >= HH={levels['HH']:.5f})",
                "color": "red"
            })
            place_order_safe(
                self.symbol,
                self.lot_size,
                "SELL",
                sl_points=self.default_sl_points
            )
