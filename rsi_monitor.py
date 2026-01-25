#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
import numpy as np

SYMBOL = "EURJPY=X"
# 5つの時間足を設定
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
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1/14, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / loss.replace(0, 1e-9))))
    # BB
    df["MA20"] = close.rolling(window=20).mean()
    df["STD"] = close.rolling(window=20).std()
    df["Upper"] = df["MA20"] + (df["STD"] * 2)
    df["Lower"] = df["MA20"] - (df["STD"] * 2)
    # 傾き (直近3本のMA20の差分)
    df["MA_Slope"] = df["MA20"].diff()
    return df

def create_chart(df, label):
    plt.figure(figsize=(6, 2.5), facecolor='#0d0d0d')
    ax = plt.axes()
    ax.set_facecolor('#0d0d0d')
    d = df.tail(40)
    plt.plot(d.index, d['Close'], color='#00ff88', lw=2)
    plt.plot(d.index, d['Upper'], color='#ff4444', lw=1, ls=':', alpha=0.4)
    plt.plot(d.index, d['Lower'], color='#44aaff', lw=1, ls=':', alpha=0.4)
    plt.axis('off')
    filename = f"chart_{label}.png"
    plt.savefig(filename, bbox_inches='tight', pad_inches=0)
    plt.close()
    return filename

def get_signal(row):
    p, r, l, u, slope = row["Close"], row["RSI"], row["Lower"], row["Upper"], row["MA_Slope"]
    # 究極ロジック
    if r <= 30 and p <= l and slope > 0: return "💎 反転開始(超鉄板買い)", "sig-strong-buy"
    if r <= 30 and p <= l: return "🔥 激アツ買い", "sig-buy"
    if r >= 70 and p >= u and slope < 0: return "🌋 反転開始(超鉄板売り)", "sig-strong-sell"
    if r >= 70 and p >= u: return "🔥 激アツ売り", "sig-sell"
    if r <= 35: return "買い狙い", "sig-soft-buy"
    if r >= 65: return "売り狙い", "sig-soft-sell"
    return "静観", "sig-none"

def main():
    now = datetime.now(tz=JST).strftime("%Y/%m/%d %H:%M")
    html_cards = ""
    all_sigs = []

    for label, interval, period in TIMEFRAMES:
        df = yf.download(SYMBOL, interval=interval, period=period, progress=False)
        # カラム名の整理（MultiIndex対策）
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        sig_text, sig_class = get_signal(last)
        all_sigs.append(sig_class)
        chart_file = create_chart(df, label)
        
        # 過去24時間レンジ
        high_24 = df["High"].tail(24 if "m" in interval or "h" in interval else 1).max()
        low_24 = df["Low"].tail(24 if "m" in interval or "h" in interval else 1).min()

        html_cards += f"""
        <div class="card">
            <div class="card-header">
                <span class="label">{label}</span>
                <span class="price">{float(last['Close']):.3f}</span>
            </div>
            <div class="range-info">24h High: {float(high_24):.3f} / Low: {float(low_24):.3f}</div>
            <div class="indicators">
                <span class="rsi">RSI: {float(last['RSI']):.1f}</span>
                <span class="signal {sig_class}">{sig_text}</span>
            </div>
            <img src="{chart_file}?v={datetime.now().timestamp()}" class="chart-img">
        </div>"""

    resonation = ""
    if all("buy" in s for s in all_sigs[:3]): resonation = '<div class="alert buy">🚨 短中期一致：ロングチャンス</div>'
    if all("buy" in s for s in all_sigs): resonation = '<div class="alert hyper">👑 全時間足一致：伝説の買い場</div>'

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EURJPY Ultimate</title><link rel="stylesheet" href="style.css"></head>
    <body><div class="container"><header><h1>EUR/JPY Ultimate</h1><p>{now} Update</p></header>
    {resonation}{html_cards}</div></body></html>""")

if __name__ == "__main__": main()
