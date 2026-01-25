#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
import numpy as np

SYMBOL = "EURJPY=X"
TIMEFRAMES = [
    ("M15", "15m", "5d"), 
    ("H1", "60m", "30d"), 
    ("H4", "4h", "90d"), 
    ("D1", "1d", "1y"), 
    ("W1", "1wk", "2y")
]
JST = timezone(timedelta(hours=9))

def calculate_indicators(df):
    close = df["Close"]
    delta = close.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1/14, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / loss.replace(0, 1e-9))))
    df["MA20"] = close.rolling(window=20).mean()
    df["STD"] = close.rolling(window=20).std()
    df["Upper"] = df["MA20"] + (df["STD"] * 2)
    df["Lower"] = df["MA20"] - (df["STD"] * 2)
    df["MA_Slope"] = df["MA20"].diff()
    return df

def get_detailed_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    p, r, l, u = float(last["Close"]), float(last["RSI"]), float(last["Lower"]), float(last["Upper"])
    r_prev = float(prev["RSI"])
    trend = "↗️" if r > r_prev else "↘️"
    
    if r <= 30 and p <= l: return "🔥 激アツ買い", "sig-buy", f"RSI{r:.1f}({trend}) & BB下限到達"
    if r >= 70 and p >= u: return "🔥 激アツ売り", "sig-sell", f"RSI{r:.1f}({trend}) & BB上限到達"
    if r <= 35:
        reason = f"RSI低域({r:.1f}↘️) 下落中" if trend == "↘️" else f"RSI底打ち反転({r:.1f}↗️)"
        return "買い狙い", "sig-soft-buy", reason
    if r >= 65:
        reason = f"RSI高域({r:.1f}↗️) 上昇中" if trend == "↗️" else f"RSI天井からの反落({r:.1f}↘️)"
        return "売り狙い", "sig-soft-sell", reason
    return "静観", "sig-none", f"RSI {r:.1f}({trend})。中立圏内"

def main():
    now = datetime.now(tz=JST).strftime("%Y/%m/%d %H:%M")
    html_cards = ""
    for label, interval, period in TIMEFRAMES:
        df = yf.download(SYMBOL, interval=interval, period=period, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = calculate_indicators(df)
        sig_text, sig_class, reason = get_detailed_signal(df)
        last = df.iloc[-1]
        html_cards += f'<div class="card"><div class="card-header"><span class="label">{label}</span><span class="price">{float(last["Close"]):.3f}</span></div><div class="indicators"><span class="signal {sig_class}">{sig_text}</span></div><div class="reason" style="font-size:0.8em; color:#8b949e; margin-top:5px; border-top:1px dashed #333; padding-top:5px;">💡 {reason}</div></div>'
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><link rel='stylesheet' href='style.css'></head><body><div class='container'><header><h1>EUR/JPY Analysis</h1><p>{now} Update</p></header>{html_cards}</div></body></html>")

if __name__ == "__main__": main()
