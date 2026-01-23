#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

# 監視したいペアをリストにする
PAIRS = ["EURJPY=X", "USDJPY=X", "BTC-JPY"]
JST = timezone(timedelta(hours=9))

def get_signal(rsi_val):
    if rsi_val >= 70: return "🔥 売り検討", "signal-sell"
    elif rsi_val <= 30: return "🚀 買い検討", "signal-buy"
    return "💎 待機", "signal-none"

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def main():
    now = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")
    html_cards = ""

    for symbol in PAIRS:
        df = yf.download(symbol, interval="60m", period="60d", progress=False)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        
        # RSI計算
        rsi_series = rsi(df["Close"])
        current_rsi = rsi_series.iloc[-1]
        last_rsi = rsi_series.iloc[-2] # 1時間前のRSI
        price = float(df["Close"].iloc[-1])
        
        sig, sig_class = get_signal(current_rsi)
        # 上がってるか下がってるかの矢印
        trend = "📈" if current_rsi > last_rsi else "📉"

        html_cards += f"""
        <div class="card">
            <h2>{symbol.replace('=X', '')}</h2>
            <p class="price-val">{price:.3f}</p>
            <p class="rsi-val">RSI: {current_rsi:.2f} {trend}</p>
            <p class="{sig_class}">{sig}</p>
            <p style="font-size:0.7em; color:#666;">前回のRSI: {last_rsi:.2f}</p>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Monitor</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Market Monitor</h1>
        <p class="update-time">最終更新: {now}</p>
        {html_cards}
    </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
