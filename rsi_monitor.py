#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

PAIR = os.environ.get("PAIR", "EURJPY=X")
JST = timezone(timedelta(hours=9))

def update_html(rsi_h1, rsi_h4, price):
    now = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>RSI Monitor</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>EUR/JPY RSI 監視ボード</h1>
    <p>現在の価格: <strong>{price:.3f}</strong></p>
    <p>H1 RSI: {rsi_h1:.2f}</p>
    <p>H4 RSI: {rsi_h4:.2f}</p>
    <p>最終更新: {now}</p>
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
    
    # 列名のクリーニング
    df_h1.columns = [c[0] if isinstance(c, tuple) else c for c in df_h1.columns]
    df_h4.columns = [c[0] if isinstance(c, tuple) else c for c in df_h4.columns]

    val_h1 = rsi(df_h1["Close"]).iloc[-1]
    val_h4 = rsi(df_h4["Close"]).iloc[-1]
    price = float(df_h1["Close"].iloc[-1])

    update_html(val_h1, val_h4, price)
    print(f"Success: HTML updated. Price: {price}")

if __name__ == "__main__":
    main()
