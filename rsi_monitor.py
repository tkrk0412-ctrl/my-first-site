#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
import json
import requests
from datetime import datetime, timezone, timedelta

PAIRS = ["EURJPY=X", "USDJPY=X", "BTC-JPY"]
JST = timezone(timedelta(hours=9))
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")

def get_divergence(df, rsi_series):
    # 直近5時間の動きで簡易判定
    price_recent = df["Close"].tail(5)
    rsi_recent = rsi_series.tail(5)
    
    # 強気のダイバージェンス（価格は下落、RSIは上昇）
    if price_recent.iloc[-1] < price_recent.iloc[0] and rsi_recent.iloc[-1] > rsi_recent.iloc[0]:
        if rsi_recent.iloc[-1] < 40: return "📈 強気ダイバージェンス発生中"
    
    # 弱気のダイバージェンス（価格は上昇、RSIは下落）
    if price_recent.iloc[-1] > price_recent.iloc[0] and rsi_recent.iloc[-1] < rsi_recent.iloc[0]:
        if rsi_recent.iloc[-1] > 60: return "📉 弱気ダイバージェンス発生中"
    
    return None

def send_ntfy(message):
    if NTFY_TOPIC:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", 
                      data=message.encode('utf-8'),
                      headers={"Title": "FX Alert", "Priority": "high"})

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))

def main():
    now = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")
    html_cards = ""
    chart_data_js = ""

    for symbol in PAIRS:
        df = yf.download(symbol, interval="60m", period="60d", progress=False)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        
        rsi_series = rsi(df["Close"])
        current_rsi = rsi_series.iloc[-1]
        price = float(df["Close"].iloc[-1])
        
        # ダイバージェンス検知
        div_msg = get_divergence(df, rsi_series)
        
        # 通知判定 (RSIが極端な値、またはダイバージェンス発生時)
        if div_msg:
            send_ntfy(f"{symbol}: {div_msg}\nPrice: {price:.3f}\nRSI: {current_rsi:.2f}")
        elif current_rsi <= 30 or current_rsi >= 70:
            send_ntfy(f"{symbol} RSI Alert: {current_rsi:.2f}\nPrice: {price:.3f}")

        history_list = rsi_series.tail(24).tolist()
        safe_name = symbol.replace('=X', '').replace('-', '')
        chart_data_js += f"const data_{safe_name} = {json.dumps(history_list)};\n"

        div_html = f'<p class="div-msg" style="color: #ffcc00; font-weight: bold;">{div_msg}</p>' if div_msg else ""
        
        html_cards += f"""
        <div class="card">
            <h2>{symbol.replace('=X', '')}</h2>
            <p class="price-val">{price:.3f}</p>
            <p class="rsi-val">RSI: {current_rsi:.2f}</p>
            {div_html}
            <div id="chart_{safe_name}" style="width: 100%; height: 100px;"></div>
        </div>
        """

    # (以下、HTML生成部分は前回と同様なので中略)
    # ※ containerの中に div-msg のスタイルを追加するとより良いです。

