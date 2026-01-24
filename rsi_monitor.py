#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta

SYMBOL = "EURJPY=X"
TIMEFRAMES = [("M15", "15m", "5d"), ("H1", "60m", "30d"), ("H4", "4h", "90d")]
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
    return df

def create_chart(df, label):
    plt.figure(figsize=(6, 3), facecolor='#1a1a1a')
    ax = plt.axes()
    ax.set_facecolor('#1a1a1a')
    
    # 直近30件を表示
    d = df.tail(30)
    plt.plot(d.index, d['Close'], color='#00ff88', lw=2, label='Price')
    plt.plot(d.index, d['Upper'], color='#ff4444', lw=1, ls='--', alpha=0.5)
    plt.plot(d.index, d['Lower'], color='#44aaff', lw=1, ls='--', alpha=0.5)
    plt.fill_between(d.index, d['Lower'], d['Upper'], color='#ffffff', alpha=0.05)
    
    plt.axis('off')
    filename = f"chart_{label}.png"
    plt.savefig(filename, bbox_inches='tight', pad_inches=0)
    plt.close()
    return filename

def get_signal(row):
    p, r, l, u = row["Close"], row["RSI"], row["Lower"], row["Upper"]
    if r <= 30 and p <= l: return "激アツ買いチャンス", "signal-buy-strong"
    if r >= 70 and p >= u: return "激アツ売りチャンス", "signal-sell-strong"
    if r <= 35: return "買い狙い", "signal-buy"
    if r >= 65: return "売り狙い", "signal-sell"
    return "静観", "signal-none"

def main():
    now = datetime.now(tz=JST).strftime("%Y/%m/%d %H:%M")
    html_cards = ""
    signals = []

    for label, interval, period in TIMEFRAMES:
        df = yf.download(SYMBOL, interval=interval, period=period, progress=False)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        sig_text, sig_class = get_signal(last)
        signals.append(sig_class)
        chart_file = create_chart(df, label)
        
        html_cards += f"""
        <div class="card">
            <div class="card-header">
                <span class="label">{label}足</span>
                <span class="price">{last['Close']:.3f}</span>
            </div>
            <div class="indicators">
                <span>RSI: {last['RSI']:.1f}</span>
                <span class="{sig_class}">{sig_text}</span>
            </div>
            <img src="{chart_file}?v={datetime.now().timestamp()}" class="chart-img">
        </div>"""

    # 全時間足で方向が一致した時のスペシャル表示
    resonation = ""
    if all("buy" in s for s in signals): resonation = '<div class="alert-box buy">🚨 全足一致：ロング推奨</div>'
    if all("sell" in s for s in signals): resonation = '<div class="alert-box sell">🚨 全足一致：ショート推奨</div>'

    with open("index.html", "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EURJPY Master Pro</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>EUR/JPY Master Pro</h1>
            <p class="time">{now} 更新</p>
        </header>
        {resonation}
        {html_cards}
    </div>
</body>
</html>""")

if __name__ == "__main__": main()
