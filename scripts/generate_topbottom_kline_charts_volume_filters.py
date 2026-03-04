import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import mplfinance as mpf
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from indicators.ma_convergence_strategy import calculate_indicators, generate_signals  # noqa: E402


@dataclass(frozen=True)
class RunConfig:
    name: str
    results_dir: Path
    signal_params: dict


def _load_daily(symbol: str, data_dir: Path, years: int) -> pd.DataFrame:
    csv_path = data_dir / f"{symbol}_{years}y_1d_forward.csv"
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

    mpf.plot(
        df_view,
        type="candle",
        style=style,
        volume=True,
        mav=mav,
        title=title,
        ylabel="Price",
        ylabel_lower="Volume",
        addplot=addplots if addplots else None,
        warn_too_much_data=len(df_view) + 500,
        figsize=(16, 10),
        tight_layout=True,
        savefig=dict(fname=str(out_png), dpi=dpi, bbox_inches="tight"),
    )


def _pick_top_bottom(results_csv: Path, top_n: int, bottom_n: int) -> pd.DataFrame:
    df = pd.read_csv(results_csv)
    df["total_trades"] = pd.to_numeric(df.get("total_trades", 0), errors="coerce").fillna(0).astype(int)
    df["total_return_pct"] = pd.to_numeric(df.get("total_return_pct", np.nan), errors="coerce")
    df = df[df["total_trades"] > 0].copy()
    df = df.sort_values("total_return_pct", ascending=False)

    top = df.head(top_n).copy()
    top["rank"] = "TOP"
    bottom = df.tail(bottom_n).copy()
    bottom["rank"] = "BOTTOM"
    picks = pd.concat([top, bottom], ignore_index=True)
    picks = picks.drop_duplicates(subset=["symbol"], keep="first").reset_index(drop=True)
    return picks


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _run_index_html(title: str, rows: list[dict], out_dir: Path) -> Path:
    rows_html = []
    for r in rows:
        png_name = Path(r["png"]).name
        rows_html.append(
            "<tr>"
            f"<td>{r['symbol']}</td>"
            f"<td>{r['rank']}</td>"
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
        "<p>Green ^ = buy, Red v = sell. Volume + moving averages included.</p>"
        "<table><thead><tr>"
        "<th>Symbol</th><th>Rank</th><th>Total %</th><th>Ann %</th><th>Win %</th><th>Trades</th><th>PNG</th><th>Preview</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows_html)
        + "</tbody></table></body></html>"
    )
    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    return index_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate top/bottom K-line charts with buy/sell markers for volume-filter runs.")
    parser.add_argument("--data-dir", default="data_cache", help="Directory containing daily CSVs.")
    parser.add_argument("--data-years", type=int, default=20, help="Which data file suffix to use (e.g. 20 -> *_20y_1d_forward.csv).")
    parser.add_argument("--plot-years", type=int, default=5, help="Years to plot from last bar.")
    parser.add_argument("--top", type=int, default=10, help="Top N symbols per run.")
    parser.add_argument("--bottom", type=int, default=10, help="Bottom N symbols per run.")
    parser.add_argument("--out-dir", default="results/ma_convergence_volume_filter_topbottom_charts", help="Output directory root.")
    parser.add_argument("--style", default="charles", help="mplfinance style.")
    parser.add_argument("--mav", default="5,10,20,60", help="MA periods to draw, comma-separated.")
    parser.add_argument("--dpi", type=int, default=160, help="PNG dpi.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_root = Path(args.out_dir)
    _ensure_dir(out_root)

    mav = tuple(int(x.strip()) for x in str(args.mav).split(",") if x.strip())
    if not mav:
        raise SystemExit("--mav must contain at least one integer period")

    runs: list[RunConfig] = [
        RunConfig(
            name="none",
            results_dir=Path("results/ma_convergence_backtest_vol_none"),
            signal_params={
                "volume_filter_enabled": False,
                "volume_filter_mode": "none",
                "volume_ma_period": 20,
            },
        ),
        RunConfig(
            name="contraction",
            results_dir=Path("results/ma_convergence_backtest_vol_contraction"),
            signal_params={
                "volume_filter_enabled": True,
                "volume_filter_mode": "contraction",
                "volume_ma_period": 20,
                "volume_ratio_max": 0.8,
            },
        ),
        RunConfig(
            name="expansion",
            results_dir=Path("results/ma_convergence_backtest_vol_expansion"),
            signal_params={
                "volume_filter_enabled": True,
                "volume_filter_mode": "expansion",
                "volume_ma_period": 20,
                "volume_ratio_min": 1.2,
            },
        ),
        RunConfig(
            name="contraction_then_expansion",
            results_dir=Path("results/ma_convergence_backtest_vol_contraction_then_expansion"),
            signal_params={
                "volume_filter_enabled": True,
                "volume_filter_mode": "contraction_then_expansion",
                "volume_ma_period": 20,
                "volume_ratio_min": 1.2,
                "volume_setup_lookback": 5,
                "volume_setup_ratio_max": 0.8,
            },
        ),
    ]

    master_links: list[str] = []

    for run in runs:
        results_csv = run.results_dir / "ma_convergence_backtest.csv"
        if not results_csv.exists():
            print(f"[WARN] missing results: {results_csv}")
            continue

        picks = _pick_top_bottom(results_csv, args.top, args.bottom)
        if picks.empty:
            print(f"[WARN] no picks: {results_csv}")
            continue

        out_dir = _ensure_dir(out_root / run.name)

        chart_rows: list[dict] = []
        failures = 0

        for _, r in picks.iterrows():
            symbol = str(r["symbol"])
            try:
                df = _load_daily(symbol, data_dir, args.data_years)
                if df.empty or not {"Open", "High", "Low", "Close", "Volume"}.issubset(df.columns):
                    continue

                df_ind = calculate_indicators(df, volume_ma_period=int(run.signal_params.get("volume_ma_period", 20)))
                signals = generate_signals(df_ind, **run.signal_params)

                df_view = _last_years(df, args.plot_years)
                if len(df_view) < 60:
                    continue

                signals_view = signals.reindex(df_view.index)

                out_png = out_dir / f"{symbol}.png"
                title = (
                    f"{symbol}  run={run.name}  total={float(r['total_return_pct']):.1f}%  "
                    f"ann={float(r['annualized_return_pct']):.1f}%  "
                    f"win={float(r['win_rate_pct']):.1f}%  trades={int(r['total_trades'])}"
                )
                _plot_symbol(symbol, df_view, signals_view, out_png, title, args.style, mav, args.dpi)

                chart_rows.append(
                    {
                        "symbol": symbol,
                        "rank": str(r.get("rank", "")) or "",
                        "total_return_pct": float(r["total_return_pct"]),
                        "annualized_return_pct": float(r["annualized_return_pct"]),
                        "win_rate_pct": float(r["win_rate_pct"]),
                        "total_trades": int(r["total_trades"]),
                        "png": str(out_png),
                    }
                )
            except Exception as e:
                failures += 1
                if failures <= 5:
                    print(f"[WARN] {run.name} failed {symbol}: {e}")
                continue

        if chart_rows:
            charts_df = pd.DataFrame(chart_rows).sort_values(["rank", "total_return_pct"], ascending=[True, False])
            charts_csv = out_dir / "charts.csv"
            charts_df.to_csv(charts_csv, index=False, encoding="utf-8-sig")
            index_path = _run_index_html(
                title=f"MA Convergence - {run.name} (Top {args.top} / Bottom {args.bottom})",
                rows=charts_df.to_dict(orient="records"),
                out_dir=out_dir,
            )
            print(f"[OK] {run.name}: charts={len(chart_rows)} csv={charts_csv} index={index_path}")
            master_links.append(f"<li><a href=\"{run.name}/index.html\">{run.name}</a></li>")

    if master_links:
        master_html = (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>MA Convergence - Top/Bottom Charts</title>"
            "<style>body{font-family:Arial,Helvetica,sans-serif}</style></head><body>"
            "<h2>MA Convergence - Top/Bottom Charts (Volume Filter Runs)</h2>"
            "<ul>"
            + "\n".join(master_links)
            + "</ul></body></html>"
        )
        (out_root / "index.html").write_text(master_html, encoding="utf-8")
        print(f"[OK] master index: {out_root / 'index.html'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
