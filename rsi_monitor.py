#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

PAIR = os.environ.get("PAIR", "EURJPY=X")
JST = timezone(timedelta(hours=9))

def get_signal(rsi_val):
    if rsi_val >= 70:
        return "🔥 売り検討 (買われすぎ)", "signal-sell"
    elif rsi_val <= 30:
        return "🚀 買い検討 (売られすぎ)", "signal-buy"
    else:
        return "💎 待機 (レンジ内)", "signal-none"

def update_html(rsi_h1, rsi_h4, price):
    now = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")
    sig_h1, class_h1 = get_signal(rsi_h1)
    sig_h4, class_h4 = get_signal(rsi_h4)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSI Trading Board</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>EUR/JPY 監視ボード</h1>
        <div class="price-box">
            <p>現在価格: <span class="price-val">{price:.3f}</span></p>
            <p class="update-time">最終更新: {now}</p>
        </div>
        
        <div class="card">
            <h2>1時間足 (H1)</h2>
            <p class="rsi-val">RSI: {rsi_h1:.2f}</p>
            <p class="{class_h1}">{sig_h1}</p>
        </div>

        <div class="card">
            <h2>4時間足 (H4)</h2>
            <p class="rsi-val">RSI: {rsi_h4:.2f}</p>
            <p class="{class_h4}">{sig_h4}</p>
        </div>
    </div>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def main():
    df_h1 = yf.download(PAIR, interval="60m", period="60d", progress=False)
    df_h4 = yf.download(PAIR, interval="4h", period="180d", progress=False)
    
    df_h1.columns = [c[0] if isinstance(c, tuple) else c for c in df_h1.columns]
    df_h4.columns = [c[0] if isinstance(c, tuple) else c for c in df_h4.columns]

    val_h1 = rsi(df_h1["Close"]).iloc[-1]
    val_h4 = rsi(df_h4["Close"]).iloc[-1]
    price = float(df_h1["Close"].iloc[-1])

    update_html(val_h1, val_h4, price)

if __name__ == "__main__":
    main()
