"""
Compare MA Convergence backtest results across multiple fixed stop-loss percentages.

Why this script:
- On some Windows setups, spawning many Python processes is expensive (heavy pandas imports).
- This script keeps a single Python process and uses a thread pool per stop-loss setting.

Example:
  python backtests/compare_stop_loss_pcts.py ^
    --data-dir data_cache --years 3 --a-share-only ^
    --symbols-file results\\a_share_codes_total_mv_ge_269_388yi_excl_sina_20260302_144411.txt ^
    --start-date 2023-03-02 --end-date 2026-03-02 ^
    --stop-loss-pcts 0.15,0.20,0.30 --workers 8
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_ma_convergence import (
    backtest_on_stock,
    filter_by_date_range,
    get_all_stock_files,
)


def _load_symbols_file(symbols_file: str) -> set[str] | None:
    p = Path(symbols_file)
    if not str(symbols_file).strip():
        return None
    if not p.exists():
        raise SystemExit(f"--symbols-file not found: {symbols_file}")

    # One symbol per line; allow "600000 招商银行" and take first token.
    out: set[str] = set()
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = str(line).strip()
        if not s or s.startswith("#"):
            continue
        out.add(s.split()[0].strip().upper())
    return out or None


def _worker(args):
    filepath, start_date, end_date, signal_params = args
    filename = os.path.basename(filepath)
    symbol = filename.split("_")[0]
    try:
        data = pd.read_csv(filepath, index_col="datetime", parse_dates=True)
        if len(data) < 50:
            return None
        if start_date or end_date:
            data = filter_by_date_range(data, start_date, end_date)
        if len(data) < 50:
            return None
        return backtest_on_stock(data, symbol, signal_params=signal_params)
    except Exception:
        return None


def _save_results(out_dir: Path, results: list[dict]) -> tuple[Path, Path | None]:
    out_dir.mkdir(parents=True, exist_ok=True)

    valid_results = []
    all_trades = []
    for r in results:
        if r is None or np.isnan(r.get("total_return_pct", np.nan)):
            continue
        valid_results.append(r)
        if "trades" in r:
            all_trades.extend(r["trades"])

    df = pd.DataFrame(valid_results)
    backtest_csv = out_dir / "ma_convergence_backtest.csv"
    if df.empty:
        df.to_csv(backtest_csv, index=False, encoding="utf-8-sig")
        return backtest_csv, None

    df[
        [
            "symbol",
            "final_capital",
            "total_return_pct",
            "annualized_return_pct",
            "sharpe_ratio",
            "max_drawdown_pct",
            "win_rate_pct",
            "total_trades",
        ]
    ].to_csv(backtest_csv, index=False, encoding="utf-8-sig")

    trades_csv = None
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_csv = out_dir / "ma_convergence_trades.csv"
        trades_df.to_csv(trades_csv, index=False, encoding="utf-8-sig")

    return backtest_csv, trades_csv


def _summarize_from_csv(backtest_csv: Path, trades_csv: Path | None, stop_loss_pct: float) -> dict:
    out = {
        "stop_loss_pct": float(stop_loss_pct),
        "n_symbols": 0,
        "n_symbols_with_trades": 0,
        "avg_total_return_pct": np.nan,
        "avg_annualized_return_pct": np.nan,
        "avg_win_rate_pct": np.nan,
        "avg_max_drawdown_pct": np.nan,
        "avg_total_trades": np.nan,
        "avg_sharpe_ratio": np.nan,
        "n_trades": 0,
        "trade_win_rate_pct": np.nan,
        "trade_avg_return_pct": np.nan,
        "trade_median_return_pct": np.nan,
        "trade_avg_holding_days": np.nan,
        "trade_min_return_pct": np.nan,
        "trade_max_return_pct": np.nan,
        "stop_loss_trade_pct": np.nan,
        "take_profit_trade_pct": np.nan,
        "time_exit_trade_pct": np.nan,
        "out_dir": str(backtest_csv.parent),
    }

    df = pd.read_csv(backtest_csv, dtype={"symbol": str})
    if df.empty:
        return out

    out["n_symbols"] = int(len(df))
    df_with = df[df["total_trades"].fillna(0) > 0].copy()
    out["n_symbols_with_trades"] = int(len(df_with))
    if not df_with.empty:
        for k, c in [
            ("avg_total_return_pct", "total_return_pct"),
            ("avg_annualized_return_pct", "annualized_return_pct"),
            ("avg_win_rate_pct", "win_rate_pct"),
            ("avg_max_drawdown_pct", "max_drawdown_pct"),
            ("avg_total_trades", "total_trades"),
            ("avg_sharpe_ratio", "sharpe_ratio"),
        ]:
            out[k] = float(pd.to_numeric(df_with[c], errors="coerce").mean())

    if trades_csv is None or (not Path(trades_csv).exists()):
        return out

    tr = pd.read_csv(trades_csv)
    if tr.empty or "return_pct" not in tr.columns:
        return out

    tr["return_pct"] = pd.to_numeric(tr["return_pct"], errors="coerce")
    tr["holding_days"] = pd.to_numeric(tr.get("holding_days"), errors="coerce")
    out["n_trades"] = int(len(tr))
    out["trade_win_rate_pct"] = float((tr["return_pct"] > 0).mean() * 100.0)
    out["trade_avg_return_pct"] = float(tr["return_pct"].mean())
    out["trade_median_return_pct"] = float(tr["return_pct"].median())
    out["trade_avg_holding_days"] = float(tr["holding_days"].mean())
    out["trade_min_return_pct"] = float(tr["return_pct"].min())
    out["trade_max_return_pct"] = float(tr["return_pct"].max())
    if "exit_reason" in tr.columns:
        s = tr["exit_reason"].astype(str)
        out["stop_loss_trade_pct"] = float(s.str.contains("stop_loss").mean() * 100.0)
        out["take_profit_trade_pct"] = float((s == "take_profit_ma5").mean() * 100.0)
        out["time_exit_trade_pct"] = float((s == "time_exit").mean() * 100.0)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare stop-loss percentages for MA Convergence backtest (threaded).")
    parser.add_argument("--data-dir", default="data_cache")
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--a-share-only", action="store_true")
    parser.add_argument("--symbols-file", default="")
    parser.add_argument("--exclude-symbols", default="")
    parser.add_argument("--workers", type=int, default=8, help="Thread workers per stop-loss run.")
    parser.add_argument("--stop-loss-pcts", default="0.15,0.20,0.30", help="Comma-separated, e.g. 0.15,0.2,0.3")
    parser.add_argument("--out-dir", default="", help="Output dir (default: results/stop_loss_compare_<ts>).")
    args = parser.parse_args()

    pcts = []
    for x in str(args.stop_loss_pcts).split(","):
        x = x.strip()
        if not x:
            continue
        v = float(x)
        if not (0 < v < 1):
            raise SystemExit(f"Invalid stop-loss pct: {x} (expected 0~1)")
        pcts.append(v)
    if not pcts:
        raise SystemExit("--stop-loss-pcts is empty")

    include_symbols = _load_symbols_file(args.symbols_file) if str(args.symbols_file).strip() else None
    exclude_symbols = [s.strip().upper() for s in str(args.exclude_symbols).split(",") if s.strip()]

    stock_files = get_all_stock_files(
        data_dir=str(args.data_dir),
        years=int(args.years),
        a_share_only=bool(args.a_share_only),
        exclude_symbols=exclude_symbols,
        include_symbols=include_symbols,
    )
    if not stock_files:
        print("[WARN] no stock files found")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else Path("results") / f"stop_loss_compare_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    workers = max(1, int(args.workers))
    summaries = []

    for pct in pcts:
        run_dir = out_dir / f"sl{int(round(pct * 100)):02d}"
        signal_params = {"stop_loss_enabled": True, "stop_loss_pct": float(pct)}

        print("=" * 80)
        print(f"[INFO] stop_loss_pct={pct:.2%} files={len(stock_files)} workers={workers} out={run_dir}")

        tasks = [(fp, args.start_date, args.end_date, signal_params) for fp in stock_files]
        results: list[dict] = []
        if workers > 1:
            with cf.ThreadPoolExecutor(max_workers=workers) as ex:
                futs = [ex.submit(_worker, t) for t in tasks]
                for idx, fut in enumerate(cf.as_completed(futs), 1):
                    r = fut.result()
                    if r is not None:
                        results.append(r)
                    if idx % 50 == 0 or idx == len(futs):
                        print(f"[INFO] progress {idx}/{len(futs)}")
        else:
            for idx, t in enumerate(tasks, 1):
                r = _worker(t)
                if r is not None:
                    results.append(r)
                if idx % 50 == 0 or idx == len(tasks):
                    print(f"[INFO] progress {idx}/{len(tasks)}")

        backtest_csv, trades_csv = _save_results(run_dir, results)
        summaries.append(_summarize_from_csv(backtest_csv, trades_csv, stop_loss_pct=pct))
        print(f"[OK] saved: {backtest_csv}")
        if trades_csv:
            print(f"[OK] saved: {trades_csv}")

    sum_df = pd.DataFrame(summaries).sort_values("stop_loss_pct")
    sum_csv = out_dir / "summary.csv"
    sum_df.to_csv(sum_csv, index=False, encoding="utf-8-sig")
    print("=" * 80)
    print(f"[OK] saved: {sum_csv}")
    print(sum_df.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
