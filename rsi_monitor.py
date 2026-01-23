#!/usr/bin/env python3
import os
from datetime import datetime, timezone, timedelta
import pandas as pd
import yfinance as yf

PAIR = os.environ.get("PAIR", "EURJPY=X")
RSI_PERIOD = 14
JST = timezone(timedelta(hours=9))

def now_jst_str():
    return datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def update_html(rsi_h1, rsi_h4, price):
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>EURJPY RSI Monitor</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>EUR/JPY RSI 監視ボード</h1>
    <div class="status">
        <p style="font-size: 1.5em;">現在の価格: <strong>{price:.3f}</strong></p>
        <hr>
        <p>H1 RSI: <span style="font-size: 1.2em; color: #e74c3c;">{rsi_h1:.2f}</span></p>
        <p>H4 RSI: <span style="font-size: 1.2em; color: #e74c3c;">{rsi_h4:.2f}</span></p>
        <p>最終更新: {now_jst_str()}</p>
    </div>
    <p><a href="https://github.com/tkrk0412-ctrl/my-first-site">GitHub Repository</a></p>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def main():
    df_h1 = yf.download(PAIR, interval="60m", period="60d", progress=False)
    df_h4 = yf.download(PAIR, interval="4h", period="180d", progress=False)
    
    if isinstance(df_h1.columns, pd.MultiIndex):
        df_h1.columns = [c[0] for c in df_h1.columns]
    if isinstance(df_h4.columns, pd.MultiIndex):
        df_h4.columns = [c[0] for c in df_h4.columns]

    rsi_h1 = rsi(df_h1["Close"], RSI_PERIOD).iloc[-1]
    rsi_h4 = rsi(df_h4["Close"], RSI_PERIOD).iloc[-1]
    price = float(df_h1["Close"].iloc[-1])

    update_html(rsi_h1, rsi_h4, price)
    print(f"Success: HTML updated at {now_jst_str()}")

if __name__ == "__main__":
    main()
