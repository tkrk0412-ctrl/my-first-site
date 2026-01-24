#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
import json
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

def get_entry_signal(row):
    p, r, l, u = row["Close"], row["RSI"], row["Lower"], row["Upper"]
    if r <= 30 and p <= l: return "🔥 鉄板買い (BB下抜+RSI)", "signal-buy"
    if r >= 70 and p >= u: return "🌋 鉄板売り (BB上抜+RSI)", "signal-sell"
    if r <= 35: return "🚀 買い検討", "signal-buy-soft"
    if r >= 65: return "🔥 売り検討", "signal-sell-soft"
    return "💎 待機", "signal-none"

def main():
    now = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")
    html_cards, chart_js = "", ""
    for label, interval, period in TIMEFRAMES:
        df = yf.download(SYMBOL, interval=interval, period=period, progress=False)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = calculate_indicators(df)
        last = df.iloc[-1]
        sig, s_class = get_entry_signal(last)
        hist = df["RSI"].tail(24).tolist()
        chart_js += f"const data_{label} = {json.dumps(hist)};\n"
        html_cards += f"""
        <div class="card">
            <h2>EUR/JPY ({label})</h2>
            <p class="price-val">{last['Close']:.3f}</p>
            <p class="bb-info">Lower: {last['Lower']:.3f} / Upper: {last['Upper']:.3f}</p>
            <p class="rsi-val">RSI: {last['RSI']:.2f}</p>
            <p class="{s_class}">{sig}</p>
            <div id="chart_{label}" style="width: 100%; height: 80px;"></div>
        </div>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EURJPY Master</title><link rel="stylesheet" href="style.css">
    <script src="https://www.gstatic.com/charts/loader.js"></script>
    <script>
      google.charts.load('current', {{packages: ['corechart']}});
      google.charts.setOnLoadCallback(() => {{
        { "".join([f"drawChart('{l}', data_{l});" for l, _, _ in TIMEFRAMES]) }
      }});
      {chart_js}
      function drawChart(name, dRaw) {{
        const data = new google.visualization.DataTable();
        data.addColumn('number', 'T'); data.addColumn('number', 'RSI');
        dRaw.forEach((v, i) => data.addRow([i, v]));
        new google.visualization.LineChart(document.getElementById('chart_'+name)).draw(data, {{
          backgroundColor: 'transparent', colors: ['#00ff88'], legend: 'none',
          hAxis: {{textPosition: 'none', gridlines: {{color: 'transparent'}}}},
          vAxis: {{textPosition: 'none', gridlines: {{color: '#333'}}, minValue: 0, maxValue: 100}},
          chartArea: {{width: '100%', height: '80%'}}
        }});
      }}
    </script>
</head>
<body><div class="container"><h1>EUR/JPY Master</h1><p class="update-time">{now}</p>{html_cards}</div></body></html>""")

if __name__ == "__main__": main()
