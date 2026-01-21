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
LEVELS = [20, 80]  # まずは厳選（あとで30/70も足せる）
PERIOD_H1 = os.environ.get("PERIOD_H1", "60d")
PERIOD_H4 = os.environ.get("PERIOD_H4", "180d")

LOCK_PATH = Path(os.environ.get("RSI_LOCK_PATH", str(Path.home() / ".cache" / "eurjpy_rsi_lock.json")))
LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

MAX_RETRY = int(os.environ.get("MAX_RETRY", "3"))
RETRY_SLEEP = float(os.environ.get("RETRY_SLEEP", "1.5"))

JST = timezone(timedelta(hours=9))

def now_jst_str() -> str:
    return datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M:%S JST")

def safe(s: str) -> str:
    return s.replace('"', '\\"')

def ntfy_send(title: str, msg: str, priority: int = 3, tags: str = "info") -> None:
    title_s = safe(title)
    msg_s = safe(msg)
    cmd = (
        f'curl -s '
        f'-H "Title: {title_s}" '
        f'-H "Priority: {priority}" '
        f'-H "Tags: {tags}" '
        f'-d "{msg_s}" '
        f'{NTFY_URL.rstrip("/")}/{TOPIC} > /dev/null'
    )
    os.system(cmd)

def load_lock() -> dict:
    if not LOCK_PATH.exists():
        return {"sent": {}}
    try:
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"sent": {}}

def save_lock(lock: dict) -> None:
    LOCK_PATH.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.bfill()

def fetch(interval: str, period: str) -> pd.DataFrame:
    last_err = None
    for _ in range(MAX_RETRY):
        try:
            df = yf.download(PAIR, interval=interval, period=period, progress=False, auto_adjust=False, threads=False)
            if isinstance(df, pd.DataFrame) and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                return df
            last_err = RuntimeError("empty dataframe")
        except Exception as e:
            last_err = e
        time.sleep(RETRY_SLEEP)
    raise RuntimeError(f"fetch failed: {last_err}")

def candle_ts_str(idx) -> str:
    dt = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")

def check_cross(prev_val: float, now_val: float, level: int) -> tuple[bool, str]:
    if prev_val < level <= now_val:
        return True, "上抜け"
    if prev_val > level >= now_val:
        return True, "下抜け"
    return False, ""

def lock_key(tf: str, level: int, direction: str, candle_ts: str) -> str:
    return f"{tf}|{level}|{direction}|{candle_ts}"

def run_for_tf(tf_name: str, interval: str, period: str) -> None:
    try:
        df = fetch(interval, period)
    except Exception as e:
        print(f"[{now_jst_str()}] WARN {tf_name} fetch error: {e}")
        return

    if len(df) < 3:
        print(f"[{now_jst_str()}] WARN {tf_name} not enough bars")
        return

    close = df["Close"].astype(float).copy()
    df["RSI"] = rsi(close, RSI_PERIOD)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    rsi_now = float(last["RSI"])
    rsi_prev = float(prev["RSI"])
    price = float(last["Close"])
    candle_ts = candle_ts_str(df.index[-1])

    # テスト送信（成立しなくても現状を1回だけ送る）
    if os.environ.get("NTFY_TEST", "0") == "1":
        ntfy_send(
            f"🧪 EURJPY RSI {tf_name} テスト",
            f"価格: {price:.3f}\nRSI({RSI_PERIOD}): {rsi_prev:.1f} → {rsi_now:.1f}\n足時刻: {candle_ts}\n送信: {now_jst_str()}",
            priority=2,
            tags="info,test"
        )

    lock = load_lock()
    sent = lock.get("sent", {})

    for lvl in LEVELS:
        ok, direction = check_cross(rsi_prev, rsi_now, int(lvl))
        if not ok:
            continue

        k = lock_key(tf_name, int(lvl), direction, candle_ts)
        if sent.get(k):
            continue

        prio = 4
        ntfy_send(
            f"📊 EURJPY RSI {tf_name} {lvl}{direction}",
            f"価格: {price:.3f}\nRSI({RSI_PERIOD}): {rsi_prev:.1f} → {rsi_now:.1f}\n判定: {lvl}{direction}\n足時刻: {candle_ts}\n送信: {now_jst_str()}",
            priority=prio,
            tags="info,chart"
        )
        sent[k] = True

    lock["sent"] = sent
    save_lock(lock)

def main() -> None:
    run_for_tf("H1", "60m", PERIOD_H1)
    run_for_tf("H4", "4h", PERIOD_H4)

if __name__ == "__main__":
    main()
