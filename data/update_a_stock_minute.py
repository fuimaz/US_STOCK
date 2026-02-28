"""
每天定时增量更新 A 股分钟数据（5/15/30/60 分钟）。

默认行为：
1. 仅更新 data_cache/a_stock_minute 中已存在的分钟文件；
2. 读取每个文件最后一根 K 线时间；
3. 从 AKShare 拉取对应周期数据并追加新增部分；
4. 去重、排序后写回原文件。
"""
from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

CACHE_DIR = "data_cache"
MINUTE_DIR = os.path.join(CACHE_DIR, "a_stock_minute")
TARGET_PERIODS = {"5", "15", "30", "60"}
FILE_PATTERN = re.compile(
    r"^(?P<symbol>\d{6}\.(?:SZ|SS))(?:\.(?:SZ|SS))?_(?P<period>\d+)min\.csv$",
    re.IGNORECASE,
)


@dataclass
class MinuteFile:
    path: str
    symbol: str
    period: str


def convert_to_akshare(symbol: str) -> str:
    if symbol.endswith(".SS"):
        return f"sh{symbol.replace('.SS', '')}"
    if symbol.endswith(".SZ"):
        return f"sz{symbol.replace('.SZ', '')}"
    return symbol


def discover_minute_files() -> list[MinuteFile]:
    if not os.path.exists(MINUTE_DIR):
        return []

    items: list[MinuteFile] = []
    for name in os.listdir(MINUTE_DIR):
        m = FILE_PATTERN.match(name)
        if not m:
            continue
        period = m.group("period")
        if period not in TARGET_PERIODS:
            continue
        items.append(
            MinuteFile(
                path=os.path.join(MINUTE_DIR, name),
                symbol=m.group("symbol").upper(),
                period=period,
            )
        )
    items.sort(key=lambda x: (x.symbol, int(x.period), x.path))
    return items


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "day" in df.columns and "datetime" not in df.columns:
        df = df.rename(columns={"day": "datetime"})

    keep_cols = ["datetime", "open", "high", "low", "close", "volume"]
    missing = [c for c in keep_cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必要列: {missing}")

    out = df[keep_cols].copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    out = out.dropna(subset=["datetime"]).sort_values("datetime")
    return out


def read_existing(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

    unnamed = [c for c in df.columns if c.startswith("Unnamed:")]
    if unnamed:
        df = df.drop(columns=unnamed)

    return normalize_columns(df)


def fetch_minute(ak_symbol: str, period: str, retries: int = 3, adjust: str = "qfq") -> pd.DataFrame | None:
    """获取分钟级数据
    
    Args:
        adjust: ''=不复权, 'qfq'=前复权(默认), 'hfq'=后复权
    """
    for i in range(retries):
        try:
            df = ak.stock_zh_a_minute(symbol=ak_symbol, period=period, adjust=adjust)
            if df is None or df.empty:
                return None
            return normalize_columns(df)
        except Exception as e:
            if i == retries - 1:
                print(f"  [失败] 拉取 {ak_symbol} {period}min 出错: {e}")
                return None
            time.sleep(1)
    return None


def update_one_file(item: MinuteFile, adjust: str = "qfq", full_refresh: bool = False) -> tuple[bool, int]:
    ak_symbol = convert_to_akshare(item.symbol)
    try:
        old_df = read_existing(item.path)
    except Exception as e:
        print(f"[跳过] 读取失败 {os.path.basename(item.path)}: {e}")
        return False, 0

    last_dt = old_df["datetime"].max() if not old_df.empty else None
    new_df = fetch_minute(ak_symbol, item.period, adjust=adjust)
    if new_df is None or new_df.empty:
        return False, 0

    if full_refresh:
        new_df = new_df.drop_duplicates(subset=["datetime"], keep="last").sort_values("datetime")
        new_df.to_csv(item.path, index=False)
        return True, len(new_df)

    if last_dt is not None:
        add_df = new_df[new_df["datetime"] > last_dt].copy()
    else:
        add_df = new_df.copy()

    if add_df.empty:
        return True, 0

    merged = pd.concat([old_df, add_df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["datetime"], keep="last").sort_values("datetime")
    merged.to_csv(item.path, index=False)
    return True, len(add_df)


def run_once(sleep_sec: float = 0.2, adjust: str = "qfq", full_refresh: bool = False) -> None:
    files = discover_minute_files()
    if not files:
        print(f"未找到可更新文件: {MINUTE_DIR}")
        return

    print("=" * 72)
    mode_name = "全量覆盖" if full_refresh else "增量更新"
    print(f"开始{mode_name}, 文件数: {len(files)}, 复权: {adjust}, 时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 72)

    ok, fail, add_total = 0, 0, 0
    for i, item in enumerate(files, start=1):
        print(f"[{i}/{len(files)}] {os.path.basename(item.path)}", end=" ... ")
        success, added = update_one_file(item, adjust=adjust, full_refresh=full_refresh)
        if success:
            ok += 1
            add_total += added
            if full_refresh:
                print(f"完成, 重写 {added} 条")
            else:
                print(f"完成, 新增 {added} 条")
        else:
            fail += 1
            print("失败")
        time.sleep(sleep_sec)

    print("-" * 72)
    print(f"更新完成: 成功 {ok}, 失败 {fail}, 新增总条数 {add_total}")
    print("=" * 72)


def parse_run_time(run_time: str) -> tuple[int, int]:
    try:
        hh, mm = run_time.split(":")
        h, m = int(hh), int(mm)
        if h < 0 or h > 23 or m < 0 or m > 59:
            raise ValueError
        return h, m
    except Exception as e:
        raise ValueError(f"--run-time 格式应为 HH:MM, 当前: {run_time}") from e


def get_next_run(run_time: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    h, m = parse_run_time(run_time)
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return target


def run_daemon(run_time: str, sleep_sec: float = 0.2, adjust: str = "qfq") -> None:
    print(f"定时模式已启动，每天 {run_time} 执行一次（复权: {adjust}）。按 Ctrl+C 退出。")
    while True:
        next_run = get_next_run(run_time)
        wait_s = max(1, int((next_run - datetime.now()).total_seconds()))
        print(f"下次执行时间: {next_run:%Y-%m-%d %H:%M:%S} (约 {wait_s // 60} 分钟后)")

        while wait_s > 0:
            chunk = min(wait_s, 60)
            time.sleep(chunk)
            wait_s -= chunk

        run_once(sleep_sec=sleep_sec, adjust=adjust, full_refresh=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="A 股分钟数据定时增量更新工具")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="开启每日定时循环模式（默认单次执行）",
    )
    parser.add_argument(
        "--run-time",
        default="17:10",
        help="每日执行时间，格式 HH:MM，默认 17:10",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=0.2,
        help="每个文件更新之间的等待秒数，默认 0.2",
    )
    parser.add_argument(
        "--adjust",
        default="qfq",
        choices=["", "qfq", "hfq"],
        help="复权类型: '' 不复权, qfq 前复权(默认), hfq 后复权",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="全量重写已有分钟文件（适合把历史不复权数据整体转换为前复权）",
    )
    args = parser.parse_args()

    if args.daemon:
        run_daemon(run_time=args.run_time, sleep_sec=args.sleep_sec, adjust=args.adjust)
    else:
        run_once(
            sleep_sec=args.sleep_sec,
            adjust=args.adjust,
            full_refresh=args.full_refresh,
        )


if __name__ == "__main__":
    main()
