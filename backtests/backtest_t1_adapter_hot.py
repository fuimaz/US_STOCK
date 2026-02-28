"""
15分钟信号 + A股T+1(日线开盘执行)回测

使用本地缓存:
- 15分钟: data_cache/a_stock_minute/{symbol}*_15min.csv
- 日线:   data_cache/{symbol}_20y_1d_forward.csv
"""

import glob
import os
import sys
import argparse
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indicators.chan.chan_theory_realtime import ChanTheoryRealtime


@dataclass
class Trade:
    date: pd.Timestamp
    action: str
    price: float
    reason: str


class ChanTheory15minT1Adapter:
    def __init__(
        self,
        min_hold_days: int = 2,
        max_hold_days: int = 5,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.10,
        volume_threshold: float = 1.5,
        signal_lookback_bars: int = 8,
    ):
        self.min_hold_days = min_hold_days
        self.max_hold_days = max_hold_days
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.volume_threshold = volume_threshold
        self.signal_lookback_bars = signal_lookback_bars
        self.reset()

    def reset(self):
        self.position = 0
        self.entry_date = None
        self.entry_price = 0.0
        self.hold_days = 0
        self.trades: List[Trade] = []

    def analyze_15min_signal(self, df_15min: pd.DataFrame) -> Dict:
        if df_15min is None or len(df_15min) < 80:
            return {"buy": False, "sell": False}

        chan = ChanTheoryRealtime(k_type="minute")
        chan.analyze(df_15min)

        latest_buy = chan.buy_points[-1] if chan.buy_points else None
        latest_sell = chan.sell_points[-1] if chan.sell_points else None
        last_ts = df_15min.index[-1]

        def _is_recent(point: Optional[dict]) -> bool:
            if not point:
                return False
            ts = point.get("index", point.get("date"))
            try:
                ts = pd.Timestamp(ts)
                # 进一步放宽：只要信号出现在当前这一天的任意15分钟K线上即可
                return ts.date() == last_ts.date()
            except Exception:
                return False

        vol_ma20 = df_15min["Volume"].rolling(20).mean().iloc[-1]
        current_vol = float(df_15min["Volume"].iloc[-1])
        volume_ok = pd.notna(vol_ma20) and current_vol > float(vol_ma20) * self.volume_threshold

        ma60 = df_15min["Close"].rolling(60).mean().iloc[-1]
        trend_ok = pd.notna(ma60) and float(df_15min["Close"].iloc[-1]) >= float(ma60)

        return {
            # 放宽: 买点在最近N根内，且满足量能或趋势任一条件即可
            "buy": _is_recent(latest_buy) and (volume_ok or trend_ok),
            "sell": _is_recent(latest_sell),
        }

    def intraday_risk_flag(self, prev_day_15min: pd.DataFrame) -> bool:
        if self.position == 0:
            return False
        sig = self.analyze_15min_signal(prev_day_15min)
        return bool(sig["sell"]) or self.hold_days >= self.max_hold_days

    def run_backtest(self, df_15min_full: pd.DataFrame, df_daily_full: pd.DataFrame) -> pd.DataFrame:
        self.reset()
        results = []
        dates = df_daily_full.index
        if len(dates) < 3:
            return pd.DataFrame()

        for i in range(1, len(dates)):
            prev_date = dates[i - 1]
            today = dates[i]
            today_bar = df_daily_full.loc[today]
            prev_bar = df_daily_full.loc[prev_date]

            # 用最近3个交易日的15分钟窗口做结构判断，避免单日数据过短导致无信号
            window_start = prev_date - pd.Timedelta(days=7)
            prev_15 = df_15min_full[
                (df_15min_full.index >= window_start) & (df_15min_full.index <= prev_date + pd.Timedelta(hours=23))
            ]
            decision = "wait"

            if self.position == 0:
                sig = self.analyze_15min_signal(prev_15)
                if sig["buy"]:
                    self.position = 1
                    self.entry_date = today
                    self.entry_price = float(today_bar["Open"])
                    self.hold_days = 0
                    self.trades.append(Trade(today, "buy", self.entry_price, "prev_15m_buy_signal"))
                    decision = "buy"
            else:
                profit_pct = (float(prev_bar["Close"]) - self.entry_price) / self.entry_price
                should_sell = (
                    profit_pct <= -self.stop_loss_pct
                    or profit_pct >= self.take_profit_pct
                    or self.intraday_risk_flag(prev_15)
                )
                if should_sell and self.hold_days >= self.min_hold_days:
                    exit_px = float(today_bar["Open"])
                    self.trades.append(Trade(today, "sell", exit_px, "risk_or_profit_or_signal"))
                    self.position = 0
                    self.entry_date = None
                    self.entry_price = 0.0
                    self.hold_days = 0
                    decision = "sell"
                else:
                    self.hold_days += 1
                    decision = "hold"

            results.append(
                {
                    "date": today,
                    "decision": decision,
                    "position": self.position,
                    "entry_price": self.entry_price if self.position else np.nan,
                    "close": float(today_bar["Close"]),
                }
            )

        if not results:
            return pd.DataFrame()
        return pd.DataFrame(results).set_index("date")


class T1BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital

    def run(self, strategy: ChanTheory15minT1Adapter, df_15min: pd.DataFrame, df_daily: pd.DataFrame) -> Dict:
        daily_states = strategy.run_backtest(df_15min, df_daily)
        if daily_states.empty:
            return {}

        capital = self.initial_capital
        shares = 0.0
        for t in strategy.trades:
            if t.action == "buy" and shares == 0:
                shares = capital / t.price
                capital = 0.0
            elif t.action == "sell" and shares > 0:
                capital = shares * t.price
                shares = 0.0

        if shares > 0:
            capital = shares * float(df_daily["Close"].iloc[-1])

        total_return = (capital - self.initial_capital) / self.initial_capital
        buyhold_return = float(df_daily["Close"].iloc[-1] / df_daily["Close"].iloc[0] - 1.0)
        return {
            "total_return": total_return,
            "buyhold_return": buyhold_return,
            "excess_return": total_return - buyhold_return,
            "trade_count": len([x for x in strategy.trades if x.action == "buy"]),
            "daily_states": daily_states,
        }


def load_15min(symbol: str) -> Optional[pd.DataFrame]:
    files = glob.glob(os.path.join("data_cache", "a_stock_minute", f"{symbol}*_15min.csv"))
    if not files:
        return None
    df = pd.read_csv(files[0])
    time_col = "datetime" if "datetime" in df.columns else ("day" if "day" in df.columns else None)
    if not time_col:
        return None
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    try:
        if getattr(df[time_col].dt, "tz", None) is not None:
            df[time_col] = df[time_col].dt.tz_localize(None)
    except Exception:
        pass
    df = df.dropna(subset=[time_col]).set_index(time_col).sort_index()
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    if not {"Open", "High", "Low", "Close", "Volume"}.issubset(df.columns):
        return None
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def load_daily(symbol: str) -> Optional[pd.DataFrame]:
    path = os.path.join("data_cache", f"{symbol}_20y_1d_forward.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    time_col = "datetime" if "datetime" in df.columns else None
    if not time_col:
        return None
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    try:
        if getattr(df[time_col].dt, "tz", None) is not None:
            df[time_col] = df[time_col].dt.tz_localize(None)
    except Exception:
        pass
    df = df.dropna(subset=[time_col]).set_index(time_col).sort_index()
    if not {"Open", "High", "Low", "Close", "Volume"}.issubset(df.columns):
        return None
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def main():
    parser = argparse.ArgumentParser(description="15min T+1 adapter backtest")
    parser.add_argument("--universe", choices=["hot", "cached"], default="hot")
    parser.add_argument(
        "--input-csv",
        default="results/chan_backtest_realtime/backtest_realtime_hot_stocks.csv",
        help="Used when universe=hot",
    )
    parser.add_argument(
        "--output-csv",
        default="results/chan_backtest_realtime/backtest_t1_adapter_hot_15min.csv",
    )
    args = parser.parse_args()

    if args.universe == "hot":
        symbols = pd.read_csv(args.input_csv)["symbol"].dropna().astype(str).drop_duplicates().tolist()
    else:
        files = glob.glob(os.path.join("data_cache", "a_stock_minute", "*_15min.csv"))
        symbols = set()
        for f in files:
            name = os.path.basename(f)
            m = re.match(r"^(\d{6}\.(?:SZ|SS|SH|BJ))", name)
            if m:
                symbols.add(m.group(1))
        symbols = sorted(symbols)

    out_path = args.output_csv

    rows = []
    for s in symbols:
        print(f"Processing {s} ...")
        m15 = load_15min(s)
        d1 = load_daily(s)
        if m15 is None or d1 is None:
            continue

        # 对齐区间：只回测15分钟数据覆盖到的日线区间
        start = m15.index.min().normalize()
        end = m15.index.max().normalize()
        d1 = d1[(d1.index >= start) & (d1.index <= end)]
        if len(d1) < 30:
            continue

        strategy = ChanTheory15minT1Adapter()
        engine = T1BacktestEngine(initial_capital=100000)
        res = engine.run(strategy, m15, d1)
        if not res:
            continue

        rows.append(
            {
                "symbol": s,
                "strategy_return_pct": round(res["total_return"] * 100, 2),
                "buyhold_return_pct": round(res["buyhold_return"] * 100, 2),
                "excess_return_pct": round(res["excess_return"] * 100, 2),
                "trade_count": res["trade_count"],
            }
        )

    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {out_path}")
    if not out.empty:
        print(
            "Avg returns | strategy={:.2f}% buyhold={:.2f}% excess={:.2f}%".format(
                out["strategy_return_pct"].mean(),
                out["buyhold_return_pct"].mean(),
                out["excess_return_pct"].mean(),
            )
        )
        print(f"Symbols: {len(out)}")


if __name__ == "__main__":
    main()
