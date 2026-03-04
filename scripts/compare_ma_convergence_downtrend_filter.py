import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import mplfinance as mpf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtests.backtest_ma_convergence import backtest_on_stock  # noqa: E402
from indicators.ma_convergence_strategy import calculate_indicators, generate_signals  # noqa: E402


@dataclass(frozen=True)
class Pick:
    symbol: str
    baseline_total_return_pct: float


def _pick_top_bottom(baseline_csv: Path, top_n: int, bottom_n: int) -> list[Pick]:
    df = pd.read_csv(baseline_csv)
    df = df[df["total_trades"] > 0].copy()
    top = df.nlargest(top_n, "total_return_pct")
    bottom = df.nsmallest(bottom_n, "total_return_pct")
    picks = pd.concat([top, bottom], ignore_index=True)
    return [
        Pick(symbol=r["symbol"], baseline_total_return_pct=float(r["total_return_pct"]))
        for r in picks.to_dict(orient="records")
    ]


def _load_daily(symbol: str, data_dir: Path) -> pd.DataFrame:
    csv_path = data_dir / f"{symbol}_20y_1d_forward.csv"
    df = pd.read_csv(csv_path, index_col="datetime", parse_dates=True).sort_index()
    cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    return df[cols]


def _last_years(df: pd.DataFrame, years: int) -> pd.DataFrame:
    if df.empty:
        return df
    end_ts = df.index.max()
    start_ts = end_ts - pd.DateOffset(years=years)
    return df.loc[df.index >= start_ts]


def _markers(df: pd.DataFrame, signals: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    buy_mask = (signals.get("signal", 0) == 1).reindex(df.index, fill_value=False)
    sell_mask = (signals.get("signal", 0) == -1).reindex(df.index, fill_value=False)

    buy_y = pd.Series(index=df.index, data=np.nan, dtype="float64")
    sell_y = pd.Series(index=df.index, data=np.nan, dtype="float64")

    if buy_mask.any():
        buy_y.loc[buy_mask] = (df.loc[buy_mask, "Low"] * 0.99).astype(float)
    if sell_mask.any():
        sell_y.loc[sell_mask] = (df.loc[sell_mask, "High"] * 1.01).astype(float)

    return buy_y, sell_y


def _plot_symbol(
    symbol: str,
    df_5y: pd.DataFrame,
    signals_5y: pd.DataFrame,
    out_png: Path,
    title: str,
    style: str,
    mav: tuple[int, ...],
    dpi: int,
):
    addplots = []
    buy_y, sell_y = _markers(df_5y, signals_5y)
    if buy_y.notna().any():
        addplots.append(
            mpf.make_addplot(
                buy_y,
                type="scatter",
                markersize=60,
                marker="^",
                color="g",
                panel=0,
            )
        )
    if sell_y.notna().any():
        addplots.append(
            mpf.make_addplot(
                sell_y,
                type="scatter",
                markersize=60,
                marker="v",
                color="r",
                panel=0,
            )
        )

    mpf.plot(
        df_5y,
        type="candle",
        style=style,
        volume=True,
        mav=mav,
        title=title,
        ylabel="Price",
        ylabel_lower="Volume",
        addplot=addplots if addplots else None,
        warn_too_much_data=len(df_5y) + 500,
        figsize=(16, 10),
        tight_layout=True,
        savefig=dict(fname=str(out_png), dpi=dpi, bbox_inches="tight"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare downtrend-only filter on top/bottom symbols and plot trades.")
    parser.add_argument(
        "--baseline-results",
        default="results/ma_convergence_backtest/ma_convergence_backtest.csv",
        help="Baseline backtest results CSV (used to pick top/bottom symbols).",
    )
    parser.add_argument("--data-dir", default="data_cache", help="Directory containing daily CSVs.")
    parser.add_argument("--out-dir", default="results/ma_convergence_downtrend_filter_compare", help="Output directory.")
    parser.add_argument("--years", type=int, default=5, help="Years of data to plot from last bar.")
    parser.add_argument("--top", type=int, default=8, help="Number of top symbols to pick.")
    parser.add_argument("--bottom", type=int, default=8, help="Number of bottom symbols to pick.")
    parser.add_argument("--style", default="charles", help="mplfinance style.")
    parser.add_argument("--mav", default="5,10,20,60", help="MA periods, comma-separated.")
    parser.add_argument("--dpi", type=int, default=160, help="PNG dpi.")
    args = parser.parse_args()

    baseline_csv = Path(args.baseline_results)
    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mav = tuple(int(x.strip()) for x in str(args.mav).split(",") if x.strip())

    picks = _pick_top_bottom(baseline_csv, args.top, args.bottom)
    print(f"[INFO] picks={len(picks)} baseline={baseline_csv}")

    compare_rows: list[dict] = []
    html_rows: list[str] = []

    for p in picks:
        df = _load_daily(p.symbol, data_dir)
        result = backtest_on_stock(df, p.symbol)
        if not result:
            continue

        df_ind = calculate_indicators(df)
        signals = generate_signals(df_ind)
        df_5y = _last_years(df, args.years)
        signals_5y = signals.reindex(df_5y.index)

        new_total = float(result["total_return_pct"])
        delta = new_total - p.baseline_total_return_pct

        out_png = out_dir / f"{p.symbol}.png"
        title = f"{p.symbol}  baseline={p.baseline_total_return_pct:.1f}%  new={new_total:.1f}%  Δ={delta:.1f}%"
        _plot_symbol(p.symbol, df_5y, signals_5y, out_png, title, args.style, mav, args.dpi)

        compare_rows.append(
            {
                "symbol": p.symbol,
                "baseline_total_return_pct": p.baseline_total_return_pct,
                "new_total_return_pct": new_total,
                "delta_total_return_pct": delta,
                "new_annualized_return_pct": float(result["annualized_return_pct"]),
                "new_max_drawdown_pct": float(result["max_drawdown_pct"]),
                "new_win_rate_pct": float(result["win_rate_pct"]),
                "new_total_trades": int(result["total_trades"]),
                "png": str(out_png),
            }
        )

        png_name = out_png.name
        html_rows.append(
            "<tr>"
            f"<td>{p.symbol}</td>"
            f"<td>{p.baseline_total_return_pct:.2f}</td>"
            f"<td>{new_total:.2f}</td>"
            f"<td>{delta:.2f}</td>"
            f"<td><a href=\"{png_name}\">{png_name}</a></td>"
            f"<td><img src=\"{png_name}\" style=\"max-width:520px; height:auto;\"></td>"
            "</tr>"
        )

    if compare_rows:
        compare_df = pd.DataFrame(compare_rows).sort_values("delta_total_return_pct", ascending=False)
        compare_path = out_dir / "compare.csv"
        compare_df.to_csv(compare_path, index=False, encoding="utf-8-sig")
        print(f"[OK] compare saved: {compare_path}")

        index_path = out_dir / "index.html"
        html = (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>MA Convergence - Downtrend Filter Compare</title>"
            "<style>body{font-family:Arial,Helvetica,sans-serif} table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #ddd;padding:6px;vertical-align:top} th{background:#f5f5f5}"
            "</style></head><body>"
            "<h2>MA Convergence - Downtrend-only Filter Compare</h2>"
            f"<p>Plot window: last {args.years} years. MA({','.join(str(x) for x in mav)}). "
            "Green ^ = buy, Red v = sell.</p>"
            "<table><thead><tr>"
            "<th>Symbol</th><th>Baseline %</th><th>New %</th><th>Δ %</th><th>PNG</th><th>Preview</th>"
            "</tr></thead><tbody>"
            + "\n".join(html_rows)
            + "</tbody></table></body></html>"
        )
        index_path.write_text(html, encoding="utf-8")
        print(f"[OK] index saved: {index_path}")

    print("[OK] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

