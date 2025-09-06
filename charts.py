import plotly.graph_objects as go
import streamlit as st

def plot_candlestick(symbol, df, levels, last_price, timeframe_choice, key):
    fig = go.Figure(data=[go.Candlestick(
        x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"], name=symbol
    )])
    for lvl_name in ["Buy1","Buy2","Buy3"]:
        fig.add_hline(y=levels[lvl_name], line=dict(color="green", dash="dash"), annotation_text=lvl_name, annotation_position="top left")
    for lvl_name in ["Resistance1","Resistance2","Resistance3"]:
        fig.add_hline(y=levels[lvl_name], line=dict(color="orange", dash="dot"), annotation_text=lvl_name, annotation_position="top right")
    if levels["Sell1"] is not None:
        fig.add_hline(y=levels["Sell1"], line=dict(color="red", dash="dash"), annotation_text="Sell1", annotation_position="bottom left")
    fig.add_hline(y=last_price, line=dict(color="blue", width=2), annotation_text="Last Price", annotation_position="bottom right")
    fig.update_layout(title=f"{symbol} — {timeframe_choice}", xaxis_rangeslider_visible=False, height=520)
    st.plotly_chart(fig, use_container_width=True, key=key)
