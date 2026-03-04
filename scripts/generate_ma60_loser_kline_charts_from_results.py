import argparse
import concurrent.futures as cf
import sys
from datetime import datetime
from pathlib import Path

import mplfinance as mpf
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from indicators.ma60_pullback_strategy import calculate_indicators, generate_signals  # noqa: E402


def _load_daily(symbol: str, data_dir: Path, years: int) -> pd.DataFrame:
    csv_path = data_dir / f"{symbol}_{years}y_1d_forward.csv"
    df = pd.read_csv(csv_path)
    if "datetime" not in df.columns:
        return pd.DataFrame()
    dt = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    mask = dt.notna()
    df = df.loc[mask].copy()
    df.index = dt.loc[mask]
    df = df.sort_index()
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
    df_view: pd.DataFrame,
    signals_view: pd.DataFrame,
    out_png: Path,
    title: str,
    style: str,
    mav: tuple[int, ...],
    dpi: int,
):
    addplots = []
    buy_y, sell_y = _markers(df_view, signals_view)
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

    plot_kwargs = dict(
        type="candle",
        style=style,
        volume=True,
        mav=mav,
        title=title,
        ylabel="Price",
        ylabel_lower="Volume",
        warn_too_much_data=len(df_view) + 500,
        figsize=(16, 10),
        tight_layout=True,
        savefig=dict(fname=str(out_png), dpi=dpi, bbox_inches="tight"),
    )
    if addplots:
        plot_kwargs["addplot"] = addplots

    mpf.plot(df_view, **plot_kwargs)


def _pick_losers(results_csv: Path, limit: int) -> pd.DataFrame:
    df = pd.read_csv(results_csv)
    if "symbol" not in df.columns:
        raise ValueError("results csv missing symbol column")

    df["total_return_pct"] = pd.to_numeric(df.get("total_return_pct", np.nan), errors="coerce")
    df["annualized_return_pct"] = pd.to_numeric(df.get("annualized_return_pct", np.nan), errors="coerce")
    df["win_rate_pct"] = pd.to_numeric(df.get("win_rate_pct", np.nan), errors="coerce")

    if "total_trades" in df.columns:
        df["total_trades"] = pd.to_numeric(df["total_trades"], errors="coerce").fillna(0).astype(int)
    elif "trades" in df.columns:
        df["total_trades"] = pd.to_numeric(df["trades"], errors="coerce").fillna(0).astype(int)
    else:
        df["total_trades"] = 0

    if "status" in df.columns:
        df = df[df["status"] == "ok"].copy()

    df = df[(df["total_trades"] > 0) & (df["total_return_pct"] < 0)].copy()
    df = df.sort_values("total_return_pct", ascending=True)
    if limit > 0:
        df = df.head(limit)
    df["rank"] = "LOSER"
    return df.reset_index(drop=True)


def _write_index(out_dir: Path, title: str, rows: list[dict]) -> Path:
    rows_html = []
    for r in rows:
        png_name = Path(r["png"]).name
        rows_html.append(
            "<tr>"
            f"<td>{r['symbol']}</td>"
            f"<td>{r['total_return_pct']:.2f}</td>"
            f"<td>{r['annualized_return_pct']:.2f}</td>"
            f"<td>{r['win_rate_pct']:.2f}</td>"
            f"<td>{int(r['total_trades'])}</td>"
            f"<td><a href=\"{png_name}\">{png_name}</a></td>"
            f"<td><img src=\"{png_name}\" style=\"max-width:520px; height:auto;\"></td>"
            "</tr>"
        )

    html = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{title}</title>"
        "<style>body{font-family:Arial,Helvetica,sans-serif} table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ddd;padding:6px;vertical-align:top} th{background:#f5f5f5}"
        "</style></head><body>"
        f"<h2>{title}</h2>"
        "<p>Green ^ = buy, Red v = sell. MA60 pullback strategy signals.</p>"
        "<table><thead><tr>"
        "<th>Symbol</th><th>Total %</th><th>Ann %</th><th>Win %</th><th>Trades</th><th>PNG</th><th>Preview</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows_html)
        + "</tbody></table></body></html>"
    )
    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    return index_path


def _render_one(args: tuple[dict, str, int, int, str, tuple[int, ...], int]) -> dict | None:
    row, data_dir_str, data_years, plot_years, style, mav, dpi = args
    symbol = str(row["symbol"])
    out_dir = Path(row["_out_dir"])
    try:
        df = _load_daily(symbol, Path(data_dir_str), data_years)
        if df.empty or not {"Open", "High", "Low", "Close", "Volume"}.issubset(df.columns):
            return None

        df_ind = calculate_indicators(df)
        signals = generate_signals(df_ind)

        df_view = _last_years(df, plot_years)
        if len(df_view) < 60:
            return None

        signals_view = signals.reindex(df_view.index)
        out_png = out_dir / f"{symbol}.png"
        title = (
            f"{symbol}  total={float(row['total_return_pct']):.1f}%  "
            f"ann={float(row['annualized_return_pct']):.1f}%  "
            f"win={float(row['win_rate_pct']):.1f}%  trades={int(row['total_trades'])}"
        )
        _plot_symbol(df_view, signals_view, out_png, title, style, mav, dpi)

        return {
            "symbol": symbol,
            "rank": "LOSER",
            "total_return_pct": float(row["total_return_pct"]),
            "annualized_return_pct": float(row["annualized_return_pct"]),
            "win_rate_pct": float(row["win_rate_pct"]),
            "total_trades": int(row["total_trades"]),
            "png": str(out_png),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate K-line charts for loser symbols from MA60 backtest results.")
    parser.add_argument("--results-csv", required=True, help="Backtest results CSV containing total_return_pct etc.")
    parser.add_argument("--data-dir", default="data_cache", help="Directory containing daily CSVs.")
    parser.add_argument("--data-years", type=int, default=20, help="Data file suffix (e.g. 20 -> *_20y_1d_forward.csv).")
    parser.add_argument("--plot-years", type=int, default=5, help="Years to plot from last bar.")
    parser.add_argument("--limit", type=int, default=0, help="Max loser symbols to draw; 0 means all losers.")
    parser.add_argument("--out-dir", default="", help="Output directory. Empty means auto-create in results/.")
    parser.add_argument("--style", default="charles", help="mplfinance style.")
    parser.add_argument("--mav", default="5,10,20,60", help="MA periods to draw, comma-separated.")
    parser.add_argument("--dpi", type=int, default=160, help="PNG dpi.")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers for chart rendering.")
    args = parser.parse_args()

    results_csv = Path(args.results_csv)
    data_dir = Path(args.data_dir)

    if not args.out_dir:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("results") / f"ma60_pullback_losers_charts_{ts}"
    else:
        out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mav = tuple(int(x.strip()) for x in str(args.mav).split(",") if x.strip())
    if not mav:
        raise SystemExit("--mav must contain at least one integer period")

    picks = _pick_losers(results_csv, args.limit)
    if picks.empty:
        print("[WARN] no losers found from results csv")
        return 0

    rows = picks.to_dict(orient="records")
    for r in rows:
        r["_out_dir"] = str(out_dir)

    tasks = [(r, str(data_dir), int(args.data_years), int(args.plot_years), args.style, mav, int(args.dpi)) for r in rows]

    chart_rows: list[dict] = []
    failures = 0
    workers = max(1, int(args.workers))
    if workers > 1:
        with cf.ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_render_one, t) for t in tasks]
            for idx, fut in enumerate(cf.as_completed(futs), 1):
                result = fut.result()
                if not result:
                    continue
                if "error" in result:
                    failures += 1
                    if failures <= 5:
                        print(f"[WARN] failed {result.get('symbol','')}: {result['error']}")
                else:
                    chart_rows.append(result)
                if idx % 10 == 0 or idx == len(futs):
                    print(f"[INFO] progress {idx}/{len(futs)}")
    else:
        for idx, t in enumerate(tasks, 1):
            result = _render_one(t)
            if not result:
                continue
            if "error" in result:
                failures += 1
                if failures <= 5:
                    print(f"[WARN] failed {result.get('symbol','')}: {result['error']}")
            else:
                chart_rows.append(result)
            if idx % 10 == 0 or idx == len(tasks):
                print(f"[INFO] progress {idx}/{len(tasks)}")

    if chart_rows:
        charts_df = pd.DataFrame(chart_rows).sort_values("total_return_pct", ascending=True)
        charts_csv = out_dir / "charts.csv"
        charts_df.to_csv(charts_csv, index=False, encoding="utf-8-sig")
        index_path = _write_index(
            out_dir=out_dir,
            title=f"MA60 Pullback Losers - {results_csv.name}",
            rows=charts_df.to_dict(orient="records"),
        )
        print(f"[OK] charts={len(chart_rows)} csv={charts_csv} index={index_path} failures={failures}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
