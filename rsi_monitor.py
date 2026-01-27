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
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1/14, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / loss.replace(0, 1e-9))))
    # Bollinger Bands
    df["MA20"] = close.rolling(window=20).mean()
    df["STD"] = close.rolling(window=20).std()
    df["Upper"] = df["MA20"] + (df["STD"] * 2)
    df["Lower"] = df["MA20"] - (df["STD"] * 2)
    # %B (Bollinger Band Position)
    df["PctB"] = (close - df["Lower"]) / (df["Upper"] - df["Lower"])
    # Volatility (ATR simple)
    df["Vol"] = df["High"].rolling(10).max() - df["Low"].rolling(10).min()
    return df

def get_comprehensive_judgment(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    p_last, p_prev = float(last["Close"]), float(prev["Close"])
    rsi = float(last["RSI"])
    pb = float(last["PctB"]) * 100
    
    # 1. ボリバン位置
    bb_pos = "上限" if pb > 90 else "下限" if pb < 10 else "中央"
    
    # 2. 勢い (直近10本の値幅比較)
    vol_now = float(last["Vol"])
    vol_avg = float(df["Vol"].mean())
    momentum = "🔥 激しい" if vol_now > vol_avg * 1.5 else "🧊 静か"
    
    # 3. 形状 (安値/高値切り上げ)
    low_now, low_prev = float(last["Low"]), float(prev["Low"])
    high_now, high_prev = float(last["High"]), float(prev["High"])
    shape = "↗️ 切り上げ" if low_now > low_prev else "↘️ 切り下げ" if high_now < high_prev else "平坦"

    # 総合判断
    if rsi < 35 and pb < 20:
        judg, color = "💎 絶好の買い場", "sig-buy"
    elif rsi > 65 and pb > 80:
        judg, color = "⚠️ 売り警戒領域", "sig-sell"
    elif rsi < 45 and shape == "↗️ 切り上げ":
        judg, color = "🏹 押し目買い狙い", "sig-soft-buy"
    elif rsi > 55 and shape == "↘️ 切り下げ":
        judg, color = "🛡️ 戻り売り狙い", "sig-soft-sell"
    else:
        judg, color = "🧘 待機（静観）", "sig-none"
        
    return judg, color, f"BB位置:{pb:.0f}%({bb_pos}) / 勢い:{momentum} / 形状:{shape}"

def main():
    now_jst = datetime.now(tz=JST)
    now_str = now_jst.strftime("%H:%M")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f: history = json.load(f)
    else: history = {}

    html_cards = ""
    new_history = {}

    for label, interval, period in TIMEFRAMES:
        df = yf.download(SYMBOL, interval=interval, period=period, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = calculate_indicators(df)
        sig_text, sig_class, detail_text = get_comprehensive_judgment(df)
        
        past_logs = history.get(label, [])
        if not past_logs or past_logs[-1]["sig"] != sig_text:
            past_logs.append({"sig": sig_text, "time": now_str})
        display_logs = past_logs[-3:]
        new_history[label] = past_logs[-10:]
        history_html = " ➔ ".join([f"{h['sig']}" for h in display_logs])

        html_cards += f"""
        <div class="card">
            <div class="card-header"><span class="label">{label}</span><span class="price">{float(df.iloc[-1]["Close"]):.3f}</span></div>
            <div class="indicators">
                <span class="signal {sig_class}">{sig_text}</span>
            </div>
            <div style="font-size:0.75em; color:#8b949e; margin-bottom:8px;">🕒 履歴: {history_html}</div>
            <div class="reason" style="font-size:0.85em; color:#d1d5da; border-top:1px solid #333; padding-top:8px;">
                {detail_text}<br>
                <strong style="color:#58a6ff;">📊 RSI: {float(df.iloc[-1]["RSI"]):.1f}</strong>
            </div>
        </div>"""

    with open(HISTORY_FILE, "w") as f: json.dump(new_history, f)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><link rel='stylesheet' href='style.css'><style>.sig-buy{{background:#1f6feb}} .sig-sell{{background:#da3633}} .sig-soft-buy{{background:#238636}} .sig-soft-sell{{background:#9e6a03}} .sig-none{{background:#30363d}}</style></head><body><div class='container'><header><h1>EUR/JPY Strategy Monitor</h1><p>{now_jst.strftime('%Y/%m/%d %H:%M')} Update</p></header>{html_cards}</div></body></html>")

if __name__ == "__main__": main()
