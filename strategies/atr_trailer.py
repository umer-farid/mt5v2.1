import MetaTrader5 as mt5
from datetime import datetime
import streamlit as st
import pandas as pd
from mt5_helpers import update_order_sl_tp


class ATRTrailingStop:
    def __init__(self, symbol, timeframe=mt5.TIMEFRAME_M1, atr_period=14,
                 atr_mult=2.0, profit_trigger_pips=20, step_pips=5):
        """
        ATR trailing stop:
        - symbol: trading pair (e.g., 'EURUSD')
        - timeframe: MT5 timeframe (default M1)
        - atr_period: ATR calculation period
        - atr_mult: multiplier for ATR distance
        - profit_trigger_pips: only trail if profit ≥ this threshold
        - step_pips: only move SL if profit increased by this much since last SL
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.atr_period = atr_period
        self.atr_mult = atr_mult
        self.profit_trigger_pips = profit_trigger_pips
        self.step_pips = step_pips

    def calculate_atr(self, rates):
        """Calculate ATR from OHLC rates."""
        if rates is None or len(rates) < self.atr_period:
            return None

        df = pd.DataFrame(rates)
        df["high_low"] = df["high"] - df["low"]
        df["high_close"] = abs(df["high"] - df["close"].shift())
        df["low_close"] = abs(df["low"] - df["close"].shift())
        tr = df[["high_low", "high_close", "low_close"]].max(axis=1)
        atr = tr.rolling(self.atr_period).mean()

        return atr.iloc[-1] if not atr.empty else None

    def run(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if not positions:
            return

        # Fetch ATR
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, self.atr_period + 2)
        if rates is None or len(rates) < self.atr_period:
            return

        atr_raw = self.calculate_atr(rates)
        if atr_raw is None:
            return

        atr_val = atr_raw * self.atr_mult
        point = mt5.symbol_info(self.symbol).point
        tick = mt5.symbol_info_tick(self.symbol)

        for pos in positions:
            if pos.type == 0:  # BUY
                profit_pips = (tick.bid - pos.price_open) / point
                if profit_pips >= self.profit_trigger_pips:
                    # Minimum SL level based on ATR
                    new_sl = tick.bid - atr_val

                    # Only move if at least `step_pips` above old SL
                    if new_sl > (pos.sl or 0) + self.step_pips * point:
                        update_order_sl_tp(pos.ticket, new_sl, pos.tp)
                        st.session_state.execution_logs.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "msg": f"🔵 Trailing BUY {self.symbol}: SL → {new_sl:.5f} ({profit_pips:.1f} pips profit)",
                            "color": "blue"
                        })

            elif pos.type == 1:  # SELL
                profit_pips = (pos.price_open - tick.ask) / point
                if profit_pips >= self.profit_trigger_pips:
                    # Minimum SL level based on ATR
                    new_sl = tick.ask + atr_val

                    # Only move if at least `step_pips` below old SL
                    if pos.sl == 0 or new_sl < pos.sl - self.step_pips * point:
                        update_order_sl_tp(pos.ticket, new_sl, pos.tp)
                        st.session_state.execution_logs.append({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "msg": f"🔴 Trailing SELL {self.symbol}: SL → {new_sl:.5f} ({profit_pips:.1f} pips profit)",
                            "color": "red"
                        })
