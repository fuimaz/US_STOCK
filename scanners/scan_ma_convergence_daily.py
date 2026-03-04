"""
Daily scanner for MA Convergence strategy buy/sell points.

What it does:
1) Load daily OHLCV data from local cache (default: *_20y_1d_forward.csv).
2) Run MA Convergence strategy (calculate_indicators + generate_signals).
3) Report symbols that trigger buy/sell signals on the latest bar (or within a lookback window).

Usage examples:
    python scanners/scan_ma_convergence_daily.py --symbols-file scanners/稳定行业.txt
    python scanners/scan_ma_convergence_daily.py --stock-pool-file scanners/stock_pool.csv
    python scanners/scan_ma_convergence_daily.py --lookback-bars 3 --workers 8
    python scanners/scan_ma_convergence_daily.py --no-stop-loss --time-exit-days 90
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import concurrent.futures as cf
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from indicators.ma_convergence_strategy import calculate_indicators, generate_signals  # noqa: E402
from data.data_fetcher import DataFetcher  # noqa: E402


_A_SHARE_SYMBOL_RE = re.compile(r"^\d{6}\.(SZ|SS|BJ)$", re.IGNORECASE)


def normalize_symbol(s: str) -> Optional[str]:
    """Normalize to 000001.SZ / 600519.SS / 8xxxxx.BJ."""
    if not s:
        return None
    raw = str(s).strip().upper()

    m = re.match(r"^(\d{6})\.(SZ|SS|BJ)$", raw)
    if m:
        return f"{m.group(1)}.{m.group(2)}"

    m = re.match(r"^(SH|SZ|BJ)(\d{6})$", raw)
    if m:
        ex_map = {"SH": "SS", "SZ": "SZ", "BJ": "BJ"}
        return f"{m.group(2)}.{ex_map[m.group(1)]}"

    m = re.match(r"^(\d{6})$", raw)
    if m:
        code = m.group(1)
        if code.startswith("8"):
            ex = "BJ"
        elif code.startswith(("0", "3")):
            ex = "SZ"
        else:
            ex = "SS"
        return f"{code}.{ex}"

    return None


def load_symbols_from_stock_pool_csv(pool_file: str) -> list[str]:
    if not pool_file or not os.path.exists(pool_file):
        return []
    df = pd.read_csv(pool_file, dtype=str).fillna("")
    if "symbol" not in df.columns:
        return []
    if "enabled" in df.columns:
        enabled = df["enabled"].astype(str).str.strip().str.lower().isin(["1", "true", "yes", "y", "on"])
        df = df[enabled]
    syms = []
    for s in df["symbol"].tolist():
        ns = normalize_symbol(s)
        if ns:
            syms.append(ns)
    return sorted(set(syms))


def load_symbols_from_file(symbols_file: str) -> list[str]:
    """
    Load symbols from CSV/TSV/TXT.

    - CSV/TSV: prefer a 'symbol' column, else use first column
    - TXT: one symbol per line; also supports lines like "600000 招商银行" (take first token)
    """
    if not symbols_file:
        return []
    p = Path(symbols_file)
    if not p.exists():
        return []

    ext = p.suffix.lower()
    if ext in (".csv", ".tsv"):
        sep = "\t" if ext == ".tsv" else ","
        df = pd.read_csv(p, sep=sep, dtype=str).fillna("")
        col = "symbol" if "symbol" in df.columns else df.columns[0]
        syms = []
        for s in df[col].tolist():
            ns = normalize_symbol(s)
            if ns:
                syms.append(ns)
        return sorted(set(syms))

    # txt
    syms = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        first = t.split()[0]
        ns = normalize_symbol(first)
        if ns:
            syms.append(ns)
    return sorted(set(syms))


@dataclass(frozen=True)
class ScanJob:
    symbol: str
    csv_path: Path


def _load_ohlcv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, index_col="datetime", parse_dates=True)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.sort_index()
    cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    return df[cols].copy()


def _build_jobs(
    data_dir: Path,
    years: int,
    symbols: Optional[Iterable[str]],
    exclude_symbols: Optional[Iterable[str]],
    a_share_only: bool,
) -> tuple[list[ScanJob], list[str]]:
    suffix = f"_{years}y_1d_forward.csv"
    exclude = {str(s).upper() for s in (exclude_symbols or [])}
    include = {str(s).upper() for s in (symbols or [])} if symbols else None

    jobs: list[ScanJob] = []
    found: set[str] = set()
    for csv_path in sorted(data_dir.glob(f"*{suffix}")):
        symbol = csv_path.name.split("_")[0]
        if a_share_only and (not _A_SHARE_SYMBOL_RE.match(symbol)):
            continue
        if include is not None and symbol.upper() not in include:
            continue
        if symbol.upper() in exclude:
            continue
        jobs.append(ScanJob(symbol=symbol, csv_path=csv_path))
        found.add(symbol.upper())

    missing: list[str] = []
    if include is not None:
        missing = sorted(s for s in include if s not in found and s not in exclude)
    return jobs, missing


def _trim_last_years(df: pd.DataFrame, years: int) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, errors="coerce")
    out = out.sort_index()
    end_ts = out.index.max()
    start_ts = end_ts - pd.DateOffset(years=years)
    out = out.loc[out.index >= start_ts]
    return out


def _read_cache_last_ts(csv_path: Path) -> Optional[pd.Timestamp]:
    """Read the last datetime value from cache CSV without loading the full file."""
    try:
        with open(csv_path, "rb") as f:
            f.seek(0, 2)
            end = f.tell()
            if end <= 0:
                return None

            data = b""
            chunk_size = 4096
            pos = end
            while pos > 0 and data.count(b"\n") < 3:
                pos = max(0, pos - chunk_size)
                f.seek(pos)
                data = f.read(end - pos)

        lines = [x for x in data.splitlines() if x.strip()]
        for raw in reversed(lines):
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line or line.startswith("datetime"):
                continue
            dt_str = line.split(",", 1)[0].strip().strip('"')
            ts = pd.to_datetime(dt_str, errors="coerce")
            if pd.isna(ts):
                continue
            return pd.Timestamp(ts)
    except Exception:
        return None
    return None


def _collect_stale_symbols(jobs: list[ScanJob], stale_days: int) -> list[str]:
    """
    Collect stale symbols from existing cache.

    stale_days:
      - 0: refresh if cache date is not today
      - N: refresh when lag_days > N
    """
    stale_days = max(0, int(stale_days))
    today = pd.Timestamp.now(tz="Asia/Shanghai").date()

    stale: list[str] = []
    for job in jobs:
        ts = _read_cache_last_ts(job.csv_path)
        if ts is None:
            stale.append(job.symbol)
            continue
        try:
            dt = pd.Timestamp(ts)
            if dt.tzinfo is not None:
                dt = dt.tz_convert("Asia/Shanghai")
            lag_days = (today - dt.date()).days
        except Exception:
            stale.append(job.symbol)
            continue
        if lag_days > stale_days:
            stale.append(job.symbol)

    return sorted(set(stale))


def _update_one_symbol(args):
    symbol, years, data_dir_str, proxy = args
    try:
        fetcher = DataFetcher(
            cache_dir=str(data_dir_str),
            cache_days=7,
            proxy=proxy or None,
            retry_count=3,
            retry_delay=2.0,
        )
        # yfinance does not officially document "20y", so use "max" then trim
        raw = fetcher.fetch_stock_data(
            symbol=symbol,
            period="max",
            interval="1d",
            use_cache=False,
            adjust="forward",
        )
        if raw is None or raw.empty:
            return (symbol, False, "empty")

        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in raw.columns]
        if len(cols) < 4:
            return (symbol, False, f"missing_cols:{cols}")
        df = raw[cols].copy()
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        idx = pd.to_datetime(df.index, errors="coerce", utc=True)
        df = df.loc[~idx.isna()].copy()
        df.index = idx[~idx.isna()].tz_convert("Asia/Shanghai")
        df.index.name = "datetime"

        df_trim = _trim_last_years(df, int(years))
        if df_trim.empty or len(df_trim) < 80:
            # still save, but warn via return message
            out_df = df_trim if not df_trim.empty else df
        else:
            out_df = df_trim

        out_path = Path(data_dir_str) / f"{symbol}_{int(years)}y_1d_forward.csv"
        out_df.to_csv(out_path, encoding="utf-8")
        return (symbol, True, str(out_path))
    except Exception as exc:
        return (symbol, False, str(exc))


def _scan_one(args):
    job, lookback_bars, signal_params = args
    try:
        df = _load_ohlcv(job.csv_path)
        if df.empty or len(df) < 140:
            return []

        df_ind = calculate_indicators(df, volume_ma_period=int(signal_params.get("volume_ma_period", 20)))
        sig = generate_signals(df_ind, **signal_params)

        lookback_bars = int(lookback_bars)
        if lookback_bars <= 0:
            lookback_bars = 1
        tail = sig.tail(lookback_bars)
        rows = []
        for dt, r in tail.iterrows():
            s = int(r.get("signal", 0))
            if s not in (1, -1):
                continue
            rows.append(
                {
                    "symbol": job.symbol,
                    "date": str(pd.Timestamp(dt)),
                    "signal": "BUY" if s == 1 else "SELL",
                    "close": float(r.get("Close", np.nan)),
                    "exit_reason": str(r.get("exit_reason", "")),
                    "ma5": float(r.get("ma5", np.nan)) if "ma5" in r else np.nan,
                    "ma10": float(r.get("ma10", np.nan)) if "ma10" in r else np.nan,
                    "ma20": float(r.get("ma20", np.nan)) if "ma20" in r else np.nan,
                    "volume": float(r.get("Volume", np.nan)) if "Volume" in r else np.nan,
                }
            )
        return rows
    except Exception:
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily MA Convergence scanner (buy/sell points).")
    parser.add_argument("--data-dir", default="data_cache")
    parser.add_argument("--years", type=int, default=20, help="Data suffix to scan (e.g. 20 -> *_20y_1d_forward.csv).")
    parser.add_argument("--a-share-only", action="store_true", help="Only scan A-share symbols.")
    parser.add_argument("--symbols-file", default="scanners/稳定行业.txt", help="CSV/TSV/TXT listing symbols/codes.")
    parser.add_argument("--stock-pool-file", default="", help="Optional scanners/stock_pool.csv (overrides symbols-file if provided).")
    parser.add_argument("--exclude-symbols", default="", help="Comma-separated symbols to exclude.")
    parser.add_argument("--lookback-bars", type=int, default=1, help="Scan signals within last N bars (default: latest bar only).")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers.")
    parser.add_argument("--out-dir", default="results/ma_convergence_daily_scan", help="Output directory for scan CSVs.")
    parser.add_argument(
        "--update-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch and cache missing symbols before scanning (default: enabled).",
    )
    parser.add_argument("--update-workers", type=int, default=4, help="Parallel workers for updating missing data.")
    parser.add_argument(
        "--update-missing-limit",
        type=int,
        default=200,
        help="Max number of missing symbols to update per run (0 = no limit).",
    )
    parser.add_argument(
        "--update-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refresh existing cache before scanning (default: enabled).",
    )
    parser.add_argument(
        "--update-existing-stale-days",
        type=int,
        default=0,
        help="Refresh existing cache when lag_days > this (0 means cache must be today's date).",
    )
    parser.add_argument(
        "--update-existing-limit",
        type=int,
        default=0,
        help="Max number of existing symbols to refresh per run (0 = no limit).",
    )
    parser.add_argument("--proxy", default="", help="Optional HTTP proxy for data fetch, e.g. http://127.0.0.1:7897")

    # Align with backtest CLI toggles commonly used
    parser.add_argument("--no-stop-loss", action="store_true")
    parser.add_argument("--time-exit-days", type=int, default=0)
    parser.add_argument(
        "--volume-filter-mode",
        default="none",
        choices=["none", "contraction", "expansion", "contraction_then_expansion"],
    )
    parser.add_argument("--vol-ma", type=int, default=20)
    parser.add_argument("--vol-ratio-max", type=float, default=0.8)
    parser.add_argument("--vol-ratio-min", type=float, default=1.2)
    parser.add_argument("--vol-setup-days", type=int, default=5)
    parser.add_argument("--vol-setup-max", type=float, default=0.8)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    exclude_symbols = [s.strip() for s in str(args.exclude_symbols).split(",") if s.strip()]

    if str(args.stock_pool_file).strip():
        pool_path = Path(args.stock_pool_file)
        if not pool_path.exists():
            raise SystemExit(f"--stock-pool-file not found: {args.stock_pool_file}")
        symbols = load_symbols_from_stock_pool_csv(args.stock_pool_file)
        if not symbols:
            raise SystemExit(f"No valid symbols loaded from --stock-pool-file: {args.stock_pool_file}")
    else:
        symbols_path = Path(args.symbols_file)
        if not symbols_path.exists():
            raise SystemExit(f"--symbols-file not found: {args.symbols_file}")
        symbols = load_symbols_from_file(args.symbols_file)
        if not symbols:
            raise SystemExit(f"No valid symbols loaded from --symbols-file: {args.symbols_file}")

    signal_params = {
        "stop_loss_enabled": (not args.no_stop_loss),
        "time_exit_enabled": int(args.time_exit_days) > 0,
        "max_holding_days": int(args.time_exit_days),
        "volume_filter_enabled": args.volume_filter_mode != "none",
        "volume_filter_mode": args.volume_filter_mode,
        "volume_ma_period": int(args.vol_ma),
        "volume_ratio_max": float(args.vol_ratio_max),
        "volume_ratio_min": float(args.vol_ratio_min),
        "volume_setup_lookback": int(args.vol_setup_days),
        "volume_setup_ratio_max": float(args.vol_setup_max),
    }

    jobs, missing = _build_jobs(
        data_dir=data_dir,
        years=int(args.years),
        symbols=symbols if symbols else None,
        exclude_symbols=exclude_symbols,
        a_share_only=bool(args.a_share_only),
    )
    if missing:
        print(f"[WARN] missing data for {len(missing)}/{len(symbols)} symbols (years={int(args.years)}). Example: {missing[:10]}")

    stale_symbols: list[str] = []
    if bool(args.update_missing) and bool(args.update_existing) and jobs:
        stale_symbols = _collect_stale_symbols(jobs, int(args.update_existing_stale_days))
        if stale_symbols:
            print(
                f"[INFO] stale cache for {len(stale_symbols)}/{len(jobs)} symbols "
                f"(stale_days={int(args.update_existing_stale_days)}). Example: {stale_symbols[:10]}"
            )

    if bool(args.update_missing) and (missing or stale_symbols):
        upd_workers = max(1, int(args.update_workers))
        proxy = str(args.proxy).strip()
        missing_limit = max(0, int(args.update_missing_limit))
        existing_limit = max(0, int(args.update_existing_limit))

        if missing_limit != 0 and len(missing) > missing_limit:
            print(
                f"[WARN] too many missing symbols ({len(missing)}). "
                f"Only updating first {missing_limit} missing symbols this run."
            )
            missing_to_update = missing[:missing_limit]
        else:
            missing_to_update = missing

        missing_set = set(missing_to_update)
        stale_only = [s for s in stale_symbols if s not in missing_set]
        if existing_limit != 0 and len(stale_only) > existing_limit:
            print(
                f"[WARN] too many stale symbols ({len(stale_only)}). "
                f"Only refreshing first {existing_limit} existing symbols this run."
            )
            stale_to_update = stale_only[:existing_limit]
        else:
            stale_to_update = stale_only

        symbols_to_update = missing_to_update + stale_to_update
        print(
            f"[INFO] updating symbols... workers={upd_workers} "
            f"total={len(symbols_to_update)} missing={len(missing_to_update)} stale={len(stale_to_update)}"
        )
        tasks = [(s, int(args.years), str(data_dir), proxy) for s in symbols_to_update]
        ok = 0
        fail = 0
        if upd_workers > 1:
            with cf.ThreadPoolExecutor(max_workers=upd_workers) as ex:
                futs = [ex.submit(_update_one_symbol, t) for t in tasks]
                for fut in cf.as_completed(futs):
                    sym, success, msg = fut.result()
                    if success:
                        ok += 1
                    else:
                        fail += 1
                        if fail <= 5:
                            print(f"[WARN] update failed: {sym}: {msg}")
        else:
            for t in tasks:
                sym, success, msg = _update_one_symbol(t)
                if success:
                    ok += 1
                else:
                    fail += 1
                    if fail <= 5:
                        print(f"[WARN] update failed: {sym}: {msg}")
        print(f"[OK] update done: success={ok}, failed={fail}")

        jobs, missing = _build_jobs(
            data_dir=data_dir,
            years=int(args.years),
            symbols=symbols if symbols else None,
            exclude_symbols=exclude_symbols,
            a_share_only=bool(args.a_share_only),
        )
        if missing:
            print(f"[WARN] still missing {len(missing)} symbols after update. Example: {missing[:10]}")

    print(f"[INFO] symbols={len(symbols)} jobs={len(jobs)} lookback_bars={int(args.lookback_bars)}")

    rows: list[dict] = []
    if int(args.workers) > 1:
        with cf.ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as ex:
            futs = [
                ex.submit(_scan_one, (job, int(args.lookback_bars), signal_params))
                for job in jobs
            ]
            for fut in cf.as_completed(futs):
                rows.extend(fut.result() or [])
    else:
        for job in jobs:
            rows.extend(_scan_one((job, int(args.lookback_bars), signal_params)) or [])

    if not rows:
        print("[OK] no signals found")
        return 0

    df_out = pd.DataFrame(rows)
    df_out = df_out.sort_values(["date", "signal", "symbol"], ascending=[False, True, True])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = out_dir / f"ma_convergence_scan_{ts}.csv"
    df_out.to_csv(out_csv, index=False, encoding="utf-8-sig")

    buy_n = int((df_out["signal"] == "BUY").sum())
    sell_n = int((df_out["signal"] == "SELL").sum())
    print(f"[OK] signals: BUY={buy_n}, SELL={sell_n}, saved={out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
