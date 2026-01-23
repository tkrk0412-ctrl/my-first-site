#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
import json
from datetime import datetime, timezone, timedelta

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
    chart_data_js = ""

    for symbol in PAIRS:
        df = yf.download(symbol, interval="60m", period="60d", progress=False)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        
        rsi_series = rsi(df["Close"])
        current_rsi = rsi_series.iloc[-1]
        price = float(df["Close"].iloc[-1])
        
        # 過去24時間のRSI推移をリスト化 (グラフ用)
        history_list = rsi_series.tail(24).tolist()
        safe_name = symbol.replace('=X', '').replace('-', '')
        chart_data_js += f"const data_{safe_name} = {json.dumps(history_list)};\n"

        sig, sig_class = get_signal(current_rsi)

        html_cards += f"""
        <div class="card">
            <h2>{symbol.replace('=X', '')}</h2>
            <p class="price-val">{price:.3f}</p>
            <p class="rsi-val">RSI: {current_rsi:.2f}</p>
            <p class="{sig_class}">{sig}</p>
            <div id="chart_{safe_name}" style="width: 100%; height: 100px;"></div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Monitor</title>
    <link rel="stylesheet" href="style.css">
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <script type="text/javascript">
      google.charts.load('current', {{packages: ['corechart']}});
      google.charts.setOnLoadCallback(drawCharts);
      {chart_data_js}
      function drawCharts() {{
        { "".join([f"drawSheet('{s.replace('=X','').replace('-','')}', data_{s.replace('=X','').replace('-','')});" for s in PAIRS]) }
      }}
      function drawSheet(name, dataRaw) {{
        const data = new google.visualization.DataTable();
        data.addColumn('number', 'Time');
        data.addColumn('number', 'RSI');
        dataRaw.forEach((v, i) => data.addRow([i, v]));
        const options = {{
          backgroundColor: 'transparent',
          colors: ['#00ff88'],
          legend: 'none',
          hAxis: {{ textPosition: 'none', gridlines: {{color: 'transparent'}} }},
          vAxis: {{ textPosition: 'none', gridlines: {{color: '#333'}}, minValue: 0, maxValue: 100 }},
          chartArea: {{width: '100%', height: '80%'}}
        }};
        const chart = new google.visualization.LineChart(document.getElementById('chart_' + name));
        chart.draw(data, options);
      }}
    </script>
</head>
<body>
    <div class="container">
        <h1>Market Monitor Pro</h1>
        <p class="update-time">最終更新: {now}</p>
        {html_cards}
    </div>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
