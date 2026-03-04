import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pandas as pd
import mplfinance as mpf
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from indicators.ma_convergence_strategy import calculate_indicators, generate_signals


@dataclass(frozen=True)
class ChartJob:
    symbol: str
    csv_path: Path


_A_SHARE_RE = re.compile(r"^\d{6}\.(SZ|SS|BJ)$", re.IGNORECASE)


def _load_ohlcv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, index_col="datetime", parse_dates=True)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.sort_index()
    return df


def _select_last_years(df: pd.DataFrame, years: int) -> pd.DataFrame:
    if df.empty:
        return df
    end_ts = df.index.max()
    start_ts = end_ts - pd.DateOffset(years=years)
    return df.loc[df.index >= start_ts]


def _make_buy_markers(df: pd.DataFrame, signals_df: pd.DataFrame) -> pd.Series:
    buy_mask = signals_df.get("signal", 0) == 1
    buy_mask = buy_mask.reindex(df.index, fill_value=False)
    marker_y = pd.Series(index=df.index, data=np.nan, dtype="float64")
    if buy_mask.any():
        marker_y.loc[buy_mask] = (df.loc[buy_mask, "Low"] * 0.99).astype(float)
    return marker_y


def _plot_one(
    df_5y: pd.DataFrame,
    signals_5y: pd.DataFrame,
    symbol: str,
    out_path: Path,
    style: str,
    mav: tuple[int, ...],
    dpi: int,
):
    addplots = []
    buy_markers = _make_buy_markers(df_5y, signals_5y)
    if buy_markers.notna().any():
        addplots.append(
            mpf.make_addplot(
                buy_markers,
                type="scatter",
                markersize=60,
                marker="^",
                color="g",
                panel=0,
            )
        )

    plot_kwargs = dict(
        type="candle",
        style=style,
        volume=True,
        mav=mav,
        title=f"{symbol} - MA Convergence Buy Points (Last 5y)",
        ylabel="Price",
        ylabel_lower="Volume",
        addplot=addplots if addplots else None,
        warn_too_much_data=len(df_5y) + 500,
        figsize=(16, 10),
        tight_layout=True,
        savefig=dict(fname=str(out_path), dpi=dpi, bbox_inches="tight"),
    )

    mpf.plot(df_5y, **plot_kwargs)


def _build_jobs(data_dir: Path, pattern: str) -> list[ChartJob]:
    return _build_jobs_filtered(data_dir=data_dir, pattern=pattern, a_share_only=False)


def _build_jobs_filtered(data_dir: Path, pattern: str, a_share_only: bool) -> list[ChartJob]:
    jobs: list[ChartJob] = []
    for csv_path in sorted(data_dir.glob(pattern)):
        symbol = csv_path.name.split("_")[0]
        if a_share_only and not _A_SHARE_RE.match(symbol):
            continue
        jobs.append(ChartJob(symbol=symbol, csv_path=csv_path))
    return jobs


def main():
    parser = argparse.ArgumentParser(description="Generate last-5y K-line charts with MA + volume + buy points.")
    parser.add_argument("--data-dir", default="data_cache", help="Directory containing daily CSV files.")
    parser.add_argument("--pattern", default="*20y_1d_forward.csv", help="Glob pattern for CSVs in data-dir.")
    parser.add_argument("--out-dir", default="results/ma_convergence_charts_5y", help="Output directory for PNGs.")
    parser.add_argument("--years", type=int, default=5, help="Number of years to plot from the latest bar.")
    parser.add_argument("--max-symbols", type=int, default=0, help="Limit number of symbols (0 = no limit).")
    parser.add_argument("--a-share-only", action="store_true", help="Only generate for A-share symbols (e.g. 000001.SZ).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing PNGs.")
    parser.add_argument("--style", default="charles", help="mplfinance style name.")
    parser.add_argument("--mav", default="5,10,20,60", help="Moving averages to draw, comma-separated (e.g. 5,10,20,60).")
    parser.add_argument("--dpi", type=int, default=160, help="PNG DPI.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = _build_jobs_filtered(data_dir, args.pattern, a_share_only=args.a_share_only)
    if args.max_symbols and args.max_symbols > 0:
        jobs = jobs[: args.max_symbols]

    try:
        mav = tuple(int(x.strip()) for x in str(args.mav).split(",") if x.strip())
    except ValueError:
        raise SystemExit(f"Invalid --mav: {args.mav}")
    if not mav:
        raise SystemExit("--mav must contain at least one integer period")

    summary_rows: list[dict] = []
    failures = 0
    skipped = 0

    print(f"[INFO] jobs={len(jobs)} data_dir={data_dir} out_dir={out_dir}")

    for idx, job in enumerate(jobs, 1):
        try:
            df = _load_ohlcv(job.csv_path)
            required_cols = {"Open", "High", "Low", "Close", "Volume"}
            if not required_cols.issubset(set(df.columns)):
                skipped += 1
                continue

            df_5y = _select_last_years(df, args.years)
            if len(df_5y) < 60:
                skipped += 1
                continue

            df_ind = calculate_indicators(df)
            signals = generate_signals(df_ind)
            signals_5y = signals.reindex(df_5y.index)

            out_path = out_dir / f"{job.symbol}.png"
            if args.overwrite or not out_path.exists():
                df_5y_plot = df_5y[["Open", "High", "Low", "Close", "Volume"]].copy()
                _plot_one(df_5y_plot, signals_5y, job.symbol, out_path, args.style, mav, args.dpi)

            buy_count = int((signals_5y.get("signal", 0) == 1).sum())
            summary_rows.append(
                {
                    "symbol": job.symbol,
                    "rows_5y": int(len(df_5y)),
                    "buy_signals_5y": buy_count,
                    "start": str(df_5y.index.min()),
                    "end": str(df_5y.index.max()),
                    "png": str(out_path),
                }
            )

            if idx % 20 == 0:
                print(f"[INFO] progress {idx}/{len(jobs)}")
        except Exception as e:
            failures += 1
            if failures <= 5:
                print(f"[WARN] failed: {job.symbol} ({job.csv_path.name}): {e}")
            continue

    if summary_rows:
        summary_path = out_dir / "summary.csv"
        summary_df = pd.DataFrame(summary_rows).sort_values(["buy_signals_5y", "symbol"], ascending=[False, True])
        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"[OK] summary saved: {summary_path}")

        index_path = out_dir / "index.html"
        rows_html = []
        for r in summary_df.to_dict(orient="records"):
            png_name = Path(r["png"]).name
            rows_html.append(
                "<tr>"
                f"<td>{r['symbol']}</td>"
                f"<td>{r['buy_signals_5y']}</td>"
                f"<td>{r['start']}</td>"
                f"<td>{r['end']}</td>"
                f"<td><a href=\"{png_name}\">{png_name}</a></td>"
                f"<td><img src=\"{png_name}\" style=\"max-width:520px; height:auto;\"></td>"
                "</tr>"
            )
        html = (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>MA Convergence Charts (Last 5y)</title>"
            "<style>body{font-family:Arial,Helvetica,sans-serif} table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #ddd;padding:6px;vertical-align:top} th{background:#f5f5f5}"
            "</style></head><body>"
            "<h2>MA Convergence Buy Points - Last 5 Years</h2>"
            f"<p>Green ^ markers are buy points (signal==1). Volume + MA({','.join(str(x) for x in mav)}) included.</p>"
            "<table><thead><tr>"
            "<th>Symbol</th><th>Buy Signals</th><th>Start</th><th>End</th><th>PNG</th><th>Preview</th>"
            "</tr></thead><tbody>"
            + "\n".join(rows_html)
            + "</tbody></table></body></html>"
        )
        index_path.write_text(html, encoding="utf-8")
        print(f"[OK] index saved: {index_path}")

    print(f"[OK] done (charts={len(summary_rows)} skipped={skipped} failures={failures})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
