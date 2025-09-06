import MetaTrader5 as mt5
import pandas as pd
import streamlit as st
import pandas as pd


def safe_symbol_info(symbol):
    return mt5.symbol_info(symbol)

# def analyze_symbol(symbol, timeframe, num_candles):
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
#     if rates is None or len(rates) == 0:
#         return None, None
#     df = pd.DataFrame(rates)
#     df["time"] = pd.to_datetime(df["time"], unit="s")

#     HH = df["high"].max()
#     LL = df["low"].min()
#     HL = df["low"].max()
#     sorted_highs = df["high"].sort_values(ascending=False).values
#     sorted_lows = df["low"].sort_values().values
#     PHH = sorted_highs[1] if len(sorted_highs) > 1 else None
#     PLL = sorted_lows[1] if len(sorted_lows) > 1 else None
#     RLL = sorted_lows[0] if len(sorted_lows) > 0 else None

#     dif = HH - LL
#     idm = dif / 2
#     factor = 1.4
#     Buy1 = HH - (factor * idm)
#     Buy2 = Buy1 - (factor * idm)
#     Buy3 = Buy2 - (factor * idm)
#     Resistance1 = HH + (factor * idm)
#     Resistance2 = Resistance1 + (factor * idm)
#     Resistance3 = Resistance2 + (factor * idm)

#     if (PLL is not None) and (RLL is not None):
#         dif_sell = PLL - RLL
#         Sell1 = HH + dif_sell
#         Sell2 = Sell1 + dif_sell
#         Sell3 = Sell2 + dif_sell
#     else:
#         Sell1 = Sell2 = Sell3 = None

#     levels = {
#         "HH": HH, "LL": LL, "HL": HL, "PHH": PHH, "PLL": PLL, "RLL": RLL,
#         "Buy1": Buy1, "Buy2": Buy2, "Buy3": Buy3,
#         "Resistance1": Resistance1, "Resistance2": Resistance2, "Resistance3":Resistance3,
#         "Sell1": Sell1, "Sell2": Sell2, "Sell3": Sell3
#     }
#     return levels, df
def analyze_symbol(symbol, timeframe, num_candles):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    if rates is None or len(rates) == 0:
        return None, None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # --- Basic Highs & Lows ---
    HH = df["high"].max()   # Highest High
    LL = df["low"].min()    # Lowest Low
    HL = df["low"].max()    # Highest Low

    sorted_highs = df["high"].sort_values(ascending=False).values
    sorted_lows = df["low"].sort_values().values

    PHH = sorted_highs[1] if len(sorted_highs) > 1 else None  # Previous High
    PLL = sorted_lows[1] if len(sorted_lows) > 1 else None    # Previous Low
    RLL = sorted_lows[0] if len(sorted_lows) > 0 else None    # Recent Lowest Low

    # --- Range calculations ---
    dif = HH - LL
    idm = dif * 0.7
    factor = 1.4

    # --- Buy levels (unchanged) ---
    Buy1 = HH - (factor * idm)
    Buy2 = Buy1 - (factor * idm)
    Buy3 = Buy2 - (factor * idm)

    # --- Resistance levels (unchanged) ---
    Resistance1 = HH + (factor * idm)
    Resistance2 = Resistance1 + (factor * idm)
    Resistance3 = Resistance2 + (factor * idm)

    # --- Sell levels (old style, keep for reference) ---
    if (PLL is not None) and (RLL is not None):
        dif_sell = PLL - RLL
        Sell1 = HH + dif_sell
        Sell2 = Sell1 + dif_sell
        Sell3 = Sell2 + dif_sell
    else:
        Sell1 = Sell2 = Sell3 = None

    # --- NEW: Custom Sell Breakout Level ---
    if PHH is not None and PLL is not None and RLL is not None:
        SellBreakout = PHH + (PLL - RLL) + (HH - PHH)
    else:
        SellBreakout = Resistance1  # fallback

    levels = {
        "HH": HH, "LL": LL, "HL": HL,
        "PHH": PHH, "PLL": PLL, "RLL": RLL,
        "Buy1": Buy1, "Buy2": Buy2, "Buy3": Buy3,
        "Resistance1": Resistance1, "Resistance2": Resistance2, "Resistance3": Resistance3,
        "Sell1": Sell1, "Sell2": Sell2, "Sell3": Sell3,
        "SellBreakout": SellBreakout  # <-- NEW
    }
    return levels, df

def get_positions_df():
    positions = mt5.positions_get()
    if not positions:
        return pd.DataFrame()
    pos_list = [p._asdict() for p in positions]
    return pd.DataFrame(pos_list)

def get_positions_for_symbol(symbol):
    df_pos = get_positions_df()
    if df_pos.empty:
        return df_pos
    col_sym = "symbol" if "symbol" in df_pos.columns else None
    if col_sym:
        df_sym = df_pos[df_pos["symbol"] == symbol].copy()
        cols_of_interest = [c for c in ["ticket","symbol","volume","type","price_open","sl","tp","price_current","profit"] if c in df_sym.columns]
        df_sym = df_sym[cols_of_interest]
        if "type" in df_sym.columns:
            df_sym["type"] = df_sym["type"].map({0: "BUY", 1: "SELL"}).fillna(df_sym["type"])
        return df_sym
    return pd.DataFrame()

def pip_and_point(symbol):
    info = mt5.symbol_info(symbol)
    if not info:
        return None, None
    point = info.point
    pip = 10*point if info.digits>=5 else point
    return point, pip

def estimate_profit_usd(symbol, tp_points, lot):
    info = mt5.symbol_info(symbol)
    if not info:
        return 0.0
    tick_value = getattr(info, "trade_tick_value", None) or 1.0
    return tp_points * tick_value * lot

def place_order_safe(symbol, lot, order_type, sl_points=0, tp_price=None):
    if "trade_logs" not in st.session_state:
        st.session_state.trade_logs = []

    info = mt5.symbol_info(symbol)
    if not info:
        st.error("Symbol info not available.")
        st.session_state.trade_logs.append({"symbol": symbol, "msg": f"❌ {order_type} {symbol} failed — no symbol info"})
        return None

    trade_allowed = getattr(info, "trade_allowed", True)
    if not trade_allowed:
        st.warning(f"Trading not allowed for {symbol}.")
        st.session_state.trade_logs.append({"symbol": symbol, "msg": f"⚠️ {order_type} {symbol} not allowed"})
        return None

    tick = mt5.symbol_info_tick(symbol)
    price = tick.ask if order_type == "BUY" else tick.bid

    # SL (currently you had sl=0.0 anyway)
    sl = 0.0 if sl_points > 0 else 0.0

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp_price if tp_price is not None else 0.0,
        "deviation": 20,
        "magic": 123456,
        "comment": f"Streamlit Auto {order_type}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    # Log trade attempt
    attempt_msg = f"⏳ Sending {order_type} {symbol} @ {price:.5f} | TP={tp_price:.5f}" if tp_price else f"⏳ Sending {order_type} {symbol} @ {price:.5f}"
    st.session_state.trade_logs.append({"symbol": symbol, "msg": attempt_msg})

    result = mt5.order_send(request)

    # Log trade result
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        success_msg = f"✅ Executed {order_type} {symbol} @ {price:.5f} | Ticket={result.order}"
        st.session_state.trade_logs.append({"symbol": symbol, "msg": success_msg})
    else:
        fail_msg = f"❌ Failed {order_type} {symbol} @ {price:.5f} | RetCode={getattr(result, 'retcode', 'N/A')}"
        st.session_state.trade_logs.append({"symbol": symbol, "msg": fail_msg})

    return result

    return mt5.order_send(request)




def calculate_atr(symbol, timeframe, period=14):
    """Calculate ATR (Average True Range) for given symbol & timeframe."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period + 1)
    if rates is None or len(rates) < period:
        return None

    df = pd.DataFrame(rates)
    df["high_low"] = df["high"] - df["low"]
    df["high_close"] = abs(df["high"] - df["close"].shift())
    df["low_close"] = abs(df["low"] - df["close"].shift())
    df["tr"] = df[["high_low", "high_close", "low_close"]].max(axis=1)

    atr = df["tr"].rolling(window=period).mean().iloc[-1]
    return atr


def update_order_sl_tp(ticket, new_sl=None, new_tp=None):
    """Modify SL/TP of an existing position safely."""
    position = mt5.positions_get(ticket=ticket)
    if not position:
        return None

    pos = position[0]
    sl = pos.sl if new_sl is None else float(new_sl)
    tp = pos.tp if new_tp is None else float(new_tp)

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": pos.symbol,
        "position": pos.ticket,
        "sl": sl if sl else 0.0,
        "tp": tp if tp else 0.0,
        "magic": 123456,
        "comment": "Update SL/TP"
    }

    return mt5.order_send(request)
