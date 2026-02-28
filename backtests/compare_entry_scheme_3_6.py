import argparse
import os
import sys
import glob
import re
from datetime import timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtests.backtest_chan_realtime import discover_cached_a_share_symbols, load_stock_data
from indicators.chan.chan_theory_realtime import ChanTheoryRealtime


COMMISSION = 0.001
SLIPPAGE = 0.0005
VOL_WINDOW = 20
VOL_MULTIPLIER = 1.5
WEEKLY_BOLL_WINDOW = 20
WEEKLY_BOLL_STD = 2.0


def get_backtest_window(data: pd.DataFrame) -> pd.DataFrame:
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10 * 365)
    return data[data.index >= start_date].copy()


def discover_cached_a_share_symbols_minute(period: str = "15") -> List[str]:
    pattern = os.path.join("data_cache", "a_stock_minute", f"*_{period}min.csv")
    files = glob.glob(pattern)
    symbols = set()
    for f in files:
        name = os.path.basename(f)
        m = re.match(r"^(\d{6}\.(?:SZ|SS|SH|BJ))", name)
        if m:
            symbols.add(m.group(1))
    return sorted(symbols)


def load_stock_data_minute(symbol: str, period: str = "15") -> Optional[pd.DataFrame]:
    # 兼容历史命名（例如 000001.SZ.SZ_15min.csv）
    pattern = os.path.join("data_cache", "a_stock_minute", f"{symbol}*_{period}min.csv")
    files = glob.glob(pattern)
    if not files:
        return None

    path = files[0]
    try:
        df = pd.read_csv(path)
        time_col = "datetime" if "datetime" in df.columns else ("day" if "day" in df.columns else None)
        if time_col is None:
            return None

        # 统一为 OHLCV 列名
        col_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume",
        }
        df = df.rename(columns=col_map)
        if not {"Open", "High", "Low", "Close", "Volume"}.issubset(df.columns):
            return None

        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col])
        df = df.set_index(time_col).sort_index()
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception:
        return None


def find_current_zs(xd: dict, zs_sorted: List[dict]) -> Optional[dict]:
    current_zs = None
    for zs in zs_sorted:
        if xd["start"] >= zs["start"] and xd["end"] <= zs["end"]:
            current_zs = zs
            break
    if current_zs is None:
        for zs in reversed(zs_sorted):
            if xd["start"] >= zs["end"]:
                current_zs = zs
                break
    return current_zs


def first_break_date(
    data: pd.DataFrame, start_idx, end_idx, threshold: float, direction: str
) -> Optional[pd.Timestamp]:
    window = data[(data.index >= start_idx) & (data.index <= end_idx)]
    if window.empty:
        return None

    if direction == "up":
        hit = window[window["High"] > threshold]
    else:
        hit = window[window["Low"] < threshold]

    if hit.empty:
        return None
    return hit.index[0]


def volume_spike_ok(data: pd.DataFrame, idx, window: int = VOL_WINDOW, mult: float = VOL_MULTIPLIER) -> bool:
    if idx not in data.index:
        return False
    loc = data.index.get_loc(idx)
    if isinstance(loc, slice):
        return False
    if loc < window:
        return False
    vol = float(data.iloc[loc]["Volume"])
    vol_ma = float(data.iloc[loc - window:loc]["Volume"].mean())
    if vol_ma <= 0:
        return False
    return vol > vol_ma * mult


def build_weekly_boll_lower_daily(data: pd.DataFrame) -> pd.Series:
    """
    计算周线BOLL下轨，并映射到日线索引（用最近已完成周线值前向填充）。
    这样不会在周中使用未来周线收盘数据。
    """
    weekly_close = data["Close"].resample("W-FRI").last()
    weekly_ma = weekly_close.rolling(WEEKLY_BOLL_WINDOW).mean()
    weekly_std = weekly_close.rolling(WEEKLY_BOLL_WINDOW).std()
    weekly_lower = weekly_ma - WEEKLY_BOLL_STD * weekly_std
    return weekly_lower.reindex(data.index, method="ffill")


def build_weekly_boll_middle_daily(data: pd.DataFrame) -> pd.Series:
    """计算周线BOLL中轨，并映射到日线/分钟线索引。"""
    weekly_close = data["Close"].resample("W-FRI").last()
    weekly_ma = weekly_close.rolling(WEEKLY_BOLL_WINDOW).mean()
    return weekly_ma.reindex(data.index, method="ffill")


def build_local_boll_middle(data: pd.DataFrame, window: int = WEEKLY_BOLL_WINDOW) -> pd.Series:
    """计算当前数据频率下的BOLL中轨（例如15分钟线）。"""
    return data["Close"].rolling(window).mean()


def weekly_boll_ok(data: pd.DataFrame, idx, weekly_boll_lower_daily: pd.Series) -> bool:
    if idx not in data.index:
        return False
    lower = weekly_boll_lower_daily.loc[idx]
    if pd.isna(lower):
        return False
    close = float(data.loc[idx, "Close"])
    return close >= float(lower)


def boll_mid_ok(data: pd.DataFrame, idx, boll_middle: pd.Series) -> bool:
    if idx not in data.index:
        return False
    mid = boll_middle.loc[idx]
    if pd.isna(mid):
        return False
    close = float(data.loc[idx, "Close"])
    return close >= float(mid)


def build_signals_for_scheme_6(
    data: pd.DataFrame, chan: ChanTheoryRealtime, boll_middle: pd.Series
) -> List[dict]:
    """方案6：突破中枢边界即触发（用线段内首次突破日期）。"""
    signals = []
    xd_sorted = sorted(chan.xianduan_list, key=lambda x: x["start"])
    zs_sorted = sorted(chan.zhongshu_list, key=lambda x: x["start"])

    last_buy_price = None
    last_sell_price = None

    for i, xd in enumerate(xd_sorted):
        if i == 0:
            continue
        prev_xd = xd_sorted[i - 1]
        current_zs = find_current_zs(xd, zs_sorted)
        if current_zs is None:
            continue

        zs_high = current_zs["high"]
        zs_low = current_zs["low"]

        # Type 1 buy
        if prev_xd["type"] == -1 and xd["type"] == 1 and xd["high"] > zs_high:
            event_date = first_break_date(data, xd["start"], xd["end"], zs_high, "up") or xd["end"]
            # scheme6 买入：仅保留放量条件，不使用BOLL中轨过滤
            if volume_spike_ok(data, event_date):
                price = float(data.loc[event_date, "Close"])
                signals.append({"date": event_date, "type": "buy", "price": price, "tag": "t1"})
                last_buy_price = price

        # Type 1 sell
        if prev_xd["type"] == 1 and xd["type"] == -1 and xd["low"] < zs_low:
            event_date = first_break_date(data, xd["start"], xd["end"], zs_low, "down") or xd["end"]
            if volume_spike_ok(data, event_date):
                price = float(data.loc[event_date, "Close"])
                signals.append({"date": event_date, "type": "sell", "price": price, "tag": "t1"})
                last_sell_price = price

        # Type 2 buy
        if last_buy_price is not None and prev_xd["type"] == 1 and xd["type"] == -1 and xd["low"] >= last_buy_price:
            event_date = xd["end"]
            price = float(data.loc[event_date, "Close"])
            signals.append({"date": event_date, "type": "buy", "price": price, "tag": "t2"})

        # Type 2 sell
        if last_sell_price is not None and prev_xd["type"] == -1 and xd["type"] == 1 and xd["high"] <= last_sell_price:
            event_date = xd["end"]
            price = float(data.loc[event_date, "Close"])
            signals.append({"date": event_date, "type": "sell", "price": price, "tag": "t2"})

    # 同日先处理卖点，避免同日反向穿仓导致乐观偏差
    signals.sort(key=lambda x: (x["date"], 0 if x["type"] == "sell" else 1))
    return signals


def build_signals_for_scheme_3(
    data: pd.DataFrame, chan: ChanTheoryRealtime, weekly_boll_lower_daily: pd.Series
) -> List[dict]:
    """方案3：先手小仓位 + 确认后加仓。"""
    signals = []
    xd_sorted = sorted(chan.xianduan_list, key=lambda x: x["start"])
    zs_sorted = sorted(chan.zhongshu_list, key=lambda x: x["start"])

    for i, xd in enumerate(xd_sorted):
        if i == 0:
            continue
        prev_xd = xd_sorted[i - 1]
        current_zs = find_current_zs(xd, zs_sorted)
        if current_zs is None:
            continue

        zs_high = current_zs["high"]
        zs_low = current_zs["low"]

        if prev_xd["type"] == -1 and xd["type"] == 1 and xd["high"] > zs_high:
            early_date = first_break_date(data, xd["start"], xd["end"], zs_high, "up") or xd["end"]
            confirm_date = xd["end"]
            if volume_spike_ok(data, early_date) and weekly_boll_ok(data, early_date, weekly_boll_lower_daily):
                signals.append({"date": early_date, "type": "buy_early", "price": float(data.loc[early_date, "Close"])})
                signals.append({"date": confirm_date, "type": "buy_confirm", "price": float(data.loc[confirm_date, "Close"])})

        if prev_xd["type"] == 1 and xd["type"] == -1 and xd["low"] < zs_low:
            sell_date = first_break_date(data, xd["start"], xd["end"], zs_low, "down") or xd["end"]
            if volume_spike_ok(data, sell_date):
                signals.append({"date": sell_date, "type": "sell", "price": float(data.loc[sell_date, "Close"])})

    priority = {"sell": 0, "buy_confirm": 1, "buy_early": 2}
    signals.sort(key=lambda x: (x["date"], priority.get(x["type"], 9)))
    return signals


def summarize_result(
    symbol: str,
    initial_capital: float,
    final_value: float,
    trades: List[dict],
    data_backtest: pd.DataFrame,
    strategy: str,
) -> Dict:
    total_return = (final_value - initial_capital) / initial_capital * 100
    years = len(data_backtest) / 252
    annualized = ((final_value / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

    buy_trades = [t for t in trades if t["type"] == "buy"]
    sell_trades = [t for t in trades if t["type"] == "sell"]
    profits = []
    for i, buy in enumerate(buy_trades):
        if i < len(sell_trades):
            profits.append((sell_trades[i]["value"] - buy["value"]) / buy["value"])
    win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100 if profits else 0

    return {
        "symbol": symbol,
        "strategy": strategy,
        "initial_capital": initial_capital,
        "final_value": final_value,
        "total_return": total_return,
        "annualized_return": annualized,
        "win_rate": win_rate,
        "trade_count": len(profits),
        "buy_count": len(buy_trades),
        "sell_count": len(sell_trades),
    }


def to_next_open_events(signals: List[dict], data: pd.DataFrame, valid_index: pd.Index) -> List[dict]:
    events = []
    for s in signals:
        sig_date = s["date"]
        if sig_date not in data.index:
            continue
        loc = data.index.get_loc(sig_date)
        if isinstance(loc, slice):
            continue
        exec_loc = loc + 1
        if exec_loc >= len(data):
            continue
        exec_date = data.index[exec_loc]
        if exec_date not in valid_index:
            continue
        event = dict(s)
        event["exec_date"] = exec_date
        event["exec_price"] = float(data.iloc[exec_loc]["Open"])
        events.append(event)
    return events


def build_incremental_events_scheme_6(
    data: pd.DataFrame, k_type: str, valid_index: pd.Index
) -> List[dict]:
    seen = set()
    events = []

    if len(data) < 2:
        return events

    for i in range(len(data) - 1):
        hist = data.iloc[: i + 1]
        chan = ChanTheoryRealtime(k_type=k_type)
        chan.analyze(hist)

        local_boll_middle = build_local_boll_middle(hist, window=WEEKLY_BOLL_WINDOW)
        signals = build_signals_for_scheme_6(hist, chan, local_boll_middle)

        for s in signals:
            key = (pd.Timestamp(s["date"]), s["type"], s.get("tag", ""))
            if key in seen:
                continue
            seen.add(key)

            exec_loc = i + 1
            if exec_loc >= len(data):
                continue
            exec_date = data.index[exec_loc]
            if exec_date not in valid_index:
                continue

            event = dict(s)
            event["signal_visible_date"] = hist.index[-1]
            event["exec_date"] = exec_date
            event["exec_price"] = float(data.iloc[exec_loc]["Open"])
            events.append(event)

    events.sort(key=lambda x: (x["exec_date"], 0 if x["type"] == "sell" else 1))
    return events


def run_scheme_6(
    data: pd.DataFrame, symbol: str, k_type: str, initial_capital: float = 100000.0
) -> Dict:
    data_backtest = get_backtest_window(data)
    if len(data_backtest) < 100:
        return {}

    events = build_incremental_events_scheme_6(data, k_type, data_backtest.index)

    capital = initial_capital
    position = 0.0
    trades = []

    for e in events:
        price = float(e["exec_price"])
        if e["type"] == "buy" and position == 0:
            shares = capital / (price * (1 + SLIPPAGE))
            cost = shares * price * (1 + SLIPPAGE) * (1 + COMMISSION)
            capital -= cost
            position = shares
            trades.append({"type": "buy", "date": e["exec_date"], "price": price, "value": cost})
        elif e["type"] == "sell" and position > 0:
            proceeds = position * price * (1 - SLIPPAGE) * (1 - COMMISSION)
            capital += proceeds
            trades.append({"type": "sell", "date": e["exec_date"], "price": price, "value": proceeds})
            position = 0.0

    final_value = capital + position * float(data_backtest["Close"].iloc[-1]) * (1 - SLIPPAGE) * (1 - COMMISSION)
    return summarize_result(symbol, initial_capital, final_value, trades, data_backtest, "scheme6_breakout_t1_open")


def build_incremental_events_scheme_3(
    data: pd.DataFrame, k_type: str, valid_index: pd.Index
) -> List[dict]:
    seen = set()
    events = []

    if len(data) < 2:
        return events

    for i in range(len(data) - 1):
        hist = data.iloc[: i + 1]
        chan = ChanTheoryRealtime(k_type=k_type)
        chan.analyze(hist)

        weekly_boll_lower_daily = build_weekly_boll_lower_daily(hist)
        signals = build_signals_for_scheme_3(hist, chan, weekly_boll_lower_daily)

        for s in signals:
            key = (pd.Timestamp(s["date"]), s["type"])
            if key in seen:
                continue
            seen.add(key)

            exec_loc = i + 1
            if exec_loc >= len(data):
                continue
            exec_date = data.index[exec_loc]
            if exec_date not in valid_index:
                continue

            event = dict(s)
            event["signal_visible_date"] = hist.index[-1]
            event["exec_date"] = exec_date
            event["exec_price"] = float(data.iloc[exec_loc]["Open"])
            events.append(event)

    priority = {"sell": 0, "buy_confirm": 1, "buy_early": 2}
    events.sort(key=lambda x: (x["exec_date"], priority.get(x["type"], 9)))
    return events


def run_scheme_3(
    data: pd.DataFrame, symbol: str, k_type: str, initial_capital: float = 100000.0
) -> Dict:
    data_backtest = get_backtest_window(data)
    if len(data_backtest) < 100:
        return {}

    events = build_incremental_events_scheme_3(data, k_type, data_backtest.index)

    cash = initial_capital
    position = 0.0
    tier = 0.0  # 0, 0.5, 1.0
    trades = []

    for e in events:
        px = float(e["exec_price"])
        equity = cash + position * px

        if e["type"] == "sell" and tier > 0 and position > 0:
            proceeds = position * px * (1 - SLIPPAGE) * (1 - COMMISSION)
            cash += proceeds
            trades.append({"type": "sell", "date": e["exec_date"], "price": px, "value": proceeds})
            position = 0.0
            tier = 0.0
            continue

        target_tier = None
        if e["type"] == "buy_early" and tier == 0.0:
            target_tier = 0.5
        elif e["type"] == "buy_confirm" and tier < 1.0:
            target_tier = 1.0

        if target_tier is None:
            continue

        target_value = equity * target_tier
        current_value = position * px
        buy_value = max(0.0, target_value - current_value)
        if buy_value <= 0:
            continue

        # 反推需要花费的现金（含滑点+手续费）
        cost = min(cash, buy_value * (1 + SLIPPAGE) * (1 + COMMISSION))
        if cost <= 0:
            continue
        shares = cost / (px * (1 + SLIPPAGE) * (1 + COMMISSION))
        cash -= cost
        position += shares
        tier = target_tier
        trades.append({"type": "buy", "date": e["exec_date"], "price": px, "value": cost})

    final_px = float(data_backtest["Close"].iloc[-1])
    final_value = cash + position * final_px * (1 - SLIPPAGE) * (1 - COMMISSION)
    return summarize_result(symbol, initial_capital, final_value, trades, data_backtest, "scheme3_half_then_confirm_t1_open")


def load_universe(args) -> List[str]:
    if args.universe == "cached":
        if args.data_source.startswith("minute"):
            minute_period = args.data_source.replace("minute", "")
            return discover_cached_a_share_symbols_minute(period=minute_period)
        return discover_cached_a_share_symbols(period="20y")
    df = pd.read_csv(args.input_csv)
    symbols = df["symbol"].dropna().astype(str).drop_duplicates().tolist()
    return symbols


def calc_buy_hold_return(data: pd.DataFrame) -> float:
    w = get_backtest_window(data)
    if len(w) < 2:
        return np.nan
    return (float(w["Close"].iloc[-1]) / float(w["Close"].iloc[0]) - 1.0) * 100.0


def main():
    parser = argparse.ArgumentParser(description="Compare entry scheme 3 and 6")
    parser.add_argument("--universe", choices=["cached", "hot"], default="hot")
    parser.add_argument(
        "--data-source",
        choices=["day", "minute15", "minute60"],
        default="day",
        help="day: data_cache/*_20y_1d_forward.csv; minute15/minute60: data_cache/a_stock_minute/*_{N}min.csv",
    )
    parser.add_argument(
        "--input-csv",
        default="results/chan_backtest_realtime/backtest_realtime_hot_stocks.csv",
        help="Used when universe=hot",
    )
    parser.add_argument(
        "--output-csv",
        default="results/chan_backtest_realtime/backtest_scheme3_scheme6_compare.csv",
    )
    args = parser.parse_args()

    symbols = load_universe(args)
    if not symbols:
        print("No symbols found.")
        return

    rows = []
    for symbol in symbols:
        print(f"Processing {symbol} ...")
        if args.data_source.startswith("minute"):
            minute_period = args.data_source.replace("minute", "")
            data = load_stock_data_minute(symbol, period=minute_period)
            k_type = "minute"
        else:
            data = load_stock_data(symbol, period="20y")
            k_type = "day"
        if data is None or len(data) < 252:
            continue

        s3 = run_scheme_3(data, symbol, k_type=k_type)
        s6 = run_scheme_6(data, symbol, k_type=k_type)
        bh = calc_buy_hold_return(data)
        if not s3 or not s6 or pd.isna(bh):
            continue

        rows.append(
            {
                "symbol": symbol,
                "scheme3_total_return": s3["total_return"],
                "scheme6_total_return": s6["total_return"],
                "buy_hold_total_return": bh,
                "scheme3_vs_buyhold": s3["total_return"] - bh,
                "scheme6_vs_buyhold": s6["total_return"] - bh,
                "scheme3_trade_count": s3["trade_count"],
                "scheme6_trade_count": s6["trade_count"],
                "scheme3_win_rate": s3["win_rate"],
                "scheme6_win_rate": s6["win_rate"],
            }
        )

    out_df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    out_df.to_csv(args.output_csv, index=False, encoding="utf-8-sig")

    if out_df.empty:
        print("No valid results generated.")
        return

    print(f"Saved: {args.output_csv}")
    print(f"Compared symbols: {len(out_df)}")
    print(
        "Avg returns | buyhold={:.2f}% scheme3={:.2f}% scheme6={:.2f}%".format(
            out_df["buy_hold_total_return"].mean(),
            out_df["scheme3_total_return"].mean(),
            out_df["scheme6_total_return"].mean(),
        )
    )


if __name__ == "__main__":
    main()
