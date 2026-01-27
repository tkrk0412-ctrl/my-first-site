#!/usr/bin/env python3
import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

SYMBOL = "EURJPY=X"
TIMEFRAMES = [("M15", "15m", "5d"), ("H1", "60m", "30d"), ("H4", "4h", "90d"), ("D1", "1d", "1y"), ("W1", "1wk", "2y")]
JST = timezone(timedelta(hours=9))
HISTORY_FILE = "history.json"

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

def get_signal_data(df):
    last = df.iloc[-1]
    p, r, l, u = float(last["Close"]), float(last["RSI"]), float(last["Lower"]), float(last["Upper"])
    if r <= 30 and p <= l: return "🔥 激アツ買い", "sig-buy"
    if r >= 70 and p >= u: return "🔥 激アツ売り", "sig-sell"
    if r <= 35: return "買い狙い", "sig-soft-buy"
    if r >= 65: return "売り狙い", "sig-soft-sell"
    return "静観", "sig-none"

def main():
    now_jst = datetime.now(tz=JST)
    now_str = now_jst.strftime("%H:%M")
    
    # 履歴の読み込み
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f: history = json.load(f)
    else:
        history = {}

    html_cards = ""
    new_history = {}

    for label, interval, period in TIMEFRAMES:
        df = yf.download(SYMBOL, interval=interval, period=period, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = calculate_indicators(df)
        sig_text, sig_class = get_signal_data(df)
        last_rsi = float(df.iloc[-1]["RSI"])
        prev_rsi = float(df.iloc[-2]["RSI"])
        trend = "↗️" if last_rsi > prev_rsi else "↘️"
        
        # 履歴処理
        past_logs = history.get(label, [])
        if not past_logs or past_logs[-1]["sig"] != sig_text:
            past_logs.append({"sig": sig_text, "time": now_str})
        
        # 直近3つに絞る
        display_logs = past_logs[-3:]
        new_history[label] = past_logs[-10:] # 保存用は10件

        # 履歴表示の組み立て
        history_html = " ↗️ ".join([f"{h['sig']}({h['time']})" for h in display_logs])

        html_cards += f"""
        <div class="card">
            <div class="card-header"><span class="label">{label}</span><span class="price">{float(df.iloc[-1]["Close"]):.3f}</span></div>
            <div class="indicators">
                <span class="signal {sig_class}">{sig_text}</span>
                <span style="font-size:0.8em; color:#8b949e;">({now_str}〜)</span>
            </div>
            <div style="font-size:0.75em; color:#6e7681; margin:8px 0; padding:5px; background:#0d1117; border-radius:4px;">
                🕒 履歴: {history_html} ↗️ 現時刻
            </div>
            <div class="reason" style="font-size:0.85em; color:#d1d5da; border-top:1px dashed #333; padding-top:5px;">
                💡 根拠: RSI {last_rsi:.1f}({trend})。{"安値圏から反発中" if trend == "↗️" and last_rsi < 40 else "高値圏から反落中" if trend == "↘️" and last_rsi > 60 else "レンジ内推移"}
            </div>
        </div>"""

    # 履歴保存
    with open(HISTORY_FILE, "w") as f: json.dump(new_history, f)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><link rel='stylesheet' href='style.css'></head><body><div class='container'><header><h1>EUR/JPY Ultimate</h1><p>{now_jst.strftime('%Y/%m/%d %H:%M')} Update</p></header>{html_cards}</div></body></html>")

if __name__ == "__main__": main()
