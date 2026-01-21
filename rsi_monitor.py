#!/usr/bin/env python3
from __future__ import annotations
import json, os, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

PAIR = os.environ.get("PAIR", "EURJPY=X")
NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh")
TOPIC = os.environ.get("NTFY_TOPIC", "makura_rsi_202512")
RSI_PERIOD = int(os.environ.get("RSI_PERIOD", "14"))
LEVELS = [20, 80]
JST = timezone(timedelta(hours=9))

def now_jst_str() -> str:
    return datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")

def ntfy_send(title: str, msg: str) -> None:
    cmd = f'curl -s -H "Title: {title}" -d "{msg}" {NTFY_URL.rstrip("/")}/{TOPIC} > /dev/null'
    os.system(cmd)

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
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
        <p>H1 RSI: <span style="font-size: 1.2em; color: red;">{rsi_h1:.2f}</span></p>
        <p>H4 RSI: <span style="font-size: 1.2em; color: red;">{rsi_h4:.2f}</span></p>
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
    
    # 列名の調整
    if isinstance(df_h1.columns, pd.MultiIndex):
        df_h1.columns = [c[0] for c in df_h1.columns]
    if isinstance(df_h4.columns, pd.MultiIndex):
        df_h4.columns = [c[0] for c in df_h4.columns]

    rsi_h1 = rsi(df_h1["Close"], RSI_PERIOD).iloc[-1]
    rsi_h4 = rsi(df_h4["Close"], RSI_PERIOD).iloc[-1]
    price = float(df_h1["Close"].iloc[-1])

    # HTML更新
    update_html(rsi_h1, rsi_h4, price)
    print(f"HTML updated. Price: {price}, H1 RSI: {rsi_h1}")

    # 通知（20/80を超えた場合のみ）
    if rsi_h1 < 20 or rsi_h1 > 80:
        ntfy_send("RSI Alert H1", f"Price: {price:.3f}\nRSI: {rsi_h1:.2f}")

if __name__ == "__main__":
    main()
