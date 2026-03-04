import argparse
import concurrent.futures as cf
import importlib
import inspect
import sys
from pathlib import Path

import mplfinance as mpf
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


STRATEGY_MODULES = {
    "ma_convergence": "indicators.ma_convergence_strategy",
    "ma60_pullback": "indicators.ma60_pullback_strategy",
}


def _resolve_strategy(strategy_key: str):
    key = str(strategy_key).strip().lower()
    if key not in STRATEGY_MODULES:
        raise ValueError(f"Unknown strategy: {strategy_key}")
    module = importlib.import_module(STRATEGY_MODULES[key])
    if not hasattr(module, "calculate_indicators") or not hasattr(module, "generate_signals"):
        raise ValueError(f"Strategy module missing required functions: {STRATEGY_MODULES[key]}")
    return module.calculate_indicators, module.generate_signals


def _call_with_supported_kwargs(func, base_kwargs: dict):
    sig = inspect.signature(func)
    allowed = set(sig.parameters.keys())
    kwargs = {k: v for k, v in base_kwargs.items() if k in allowed}
    return func(**kwargs)


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


def _load_results(results_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(results_csv)
    if "total_trades" in df.columns:
        total_trades = pd.to_numeric(df["total_trades"], errors="coerce")
    elif "trades" in df.columns:
        total_trades = pd.to_numeric(df["trades"], errors="coerce")
    else:
        total_trades = pd.Series([0] * len(df))
    df["total_trades"] = total_trades.fillna(0).astype(int)

    df["total_return_pct"] = pd.to_numeric(df.get("total_return_pct", np.nan), errors="coerce")
    df["annualized_return_pct"] = pd.to_numeric(df.get("annualized_return_pct", np.nan), errors="coerce")
    df["win_rate_pct"] = pd.to_numeric(df.get("win_rate_pct", np.nan), errors="coerce")
    if "status" in df.columns:
        df = df[df["status"] == "ok"].copy()
    df = df[df["total_trades"] > 0].copy()
    return df


def _pick_symbols(results_csv: Path, mode: str, top_n: int, bottom_n: int, limit: int) -> pd.DataFrame:
    df = _load_results(results_csv)
    mode = str(mode).strip().lower()

    if mode == "topbottom":
        df = df.sort_values("total_return_pct", ascending=False)
        top = df.head(top_n).copy()
        top["rank"] = "TOP"
        bottom = df.tail(bottom_n).copy()
        bottom["rank"] = "BOTTOM"
        picks = pd.concat([top, bottom], ignore_index=True)
        picks = picks.drop_duplicates(subset=["symbol"], keep="first").reset_index(drop=True)
        return picks

    if mode == "losers":
        losers = df[df["total_return_pct"] < 0].sort_values("total_return_pct", ascending=True).copy()
        if int(limit) > 0:
            losers = losers.head(int(limit))
        losers["rank"] = "LOSER"
        return losers.reset_index(drop=True)

    raise ValueError(f"Unknown mode: {mode}")


def _write_index(out_dir: Path, title: str, rows: list[dict]) -> Path:
    items_js = []
    for r in rows:
        png_name = Path(r["png"]).name
        items_js.append(
            "{"
            f"symbol:{repr(str(r['symbol']))},"
            f"rank:{repr(str(r['rank']))},"
            f"total:{float(r['total_return_pct']):.6f},"
            f"ann:{float(r['annualized_return_pct']):.6f},"
            f"win:{float(r['win_rate_pct']):.6f},"
            f"trades:{int(r['total_trades'])},"
            f"png:{repr(png_name)}"
            "}"
        )

    html = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{title}</title>"
        "<style>"
        "body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f4f6f8;color:#1f2937}"
        ".wrap{display:flex;height:100vh;overflow:hidden}"
        ".side{width:360px;min-width:320px;max-width:420px;background:#fff;border-right:1px solid #e5e7eb;display:flex;flex-direction:column}"
        ".side-head{padding:14px 14px 10px;border-bottom:1px solid #eef2f7}"
        ".title{font-size:16px;font-weight:700;line-height:1.35;margin:0 0 6px}"
        ".sub{font-size:12px;color:#6b7280;margin:0 0 10px}"
        ".tools{display:flex;gap:8px}"
        ".tools input{flex:1;padding:8px 10px;border:1px solid #d1d5db;border-radius:8px;font-size:13px}"
        ".tools button{padding:8px 10px;border:1px solid #d1d5db;background:#fff;border-radius:8px;cursor:pointer}"
        ".list{overflow:auto;padding:8px}"
        ".item{padding:10px;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:8px;background:#fff;cursor:pointer}"
        ".item.active{border-color:#2563eb;background:#eff6ff}"
        ".row{display:flex;justify-content:space-between;gap:8px;font-size:13px}"
        ".symbol{font-weight:700}"
        ".meta{font-size:12px;color:#6b7280;margin-top:4px}"
        ".main{flex:1;display:flex;flex-direction:column;min-width:0}"
        ".viewer-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 14px;background:#fff;border-bottom:1px solid #e5e7eb}"
        ".viewer-title{font-size:14px;font-weight:700}"
        ".viewer-meta{font-size:12px;color:#6b7280}"
        ".nav{display:flex;gap:8px}"
        ".nav button{padding:8px 10px;border:1px solid #d1d5db;background:#fff;border-radius:8px;cursor:pointer}"
        ".canvas{flex:1;overflow:auto;padding:10px;text-align:center}"
        ".canvas img{max-width:100%;height:auto;border:1px solid #d1d5db;border-radius:8px;background:#fff}"
        "</style>"
        "</head><body>"
        "<div class='wrap'>"
        "<aside class='side'>"
        "<div class='side-head'>"
        f"<p class='title'>{title}</p>"
        "<p class='sub'>点击左侧股票切换K线图；支持键盘 ←/→ 切换。</p>"
        "<div class='tools'><input id='search' placeholder='搜索代码...'><button id='reset'>重置</button></div>"
        "</div>"
        "<div id='list' class='list'></div>"
        "</aside>"
        "<main class='main'>"
        "<div class='viewer-head'>"
        "<div>"
        "<div id='viewerTitle' class='viewer-title'></div>"
        "<div id='viewerMeta' class='viewer-meta'></div>"
        "</div>"
        "<div class='nav'><button id='prevBtn'>上一张</button><button id='nextBtn'>下一张</button>"
        "<a id='openLink' target='_blank' style='padding:8px 10px;border:1px solid #d1d5db;background:#fff;border-radius:8px;text-decoration:none;color:#111827'>新窗口</a></div>"
        "</div>"
        "<div class='canvas'><img id='chartImg' src='' alt='kline'></div>"
        "</main></div>"
        "<script>"
        f"const items=[{','.join(items_js)}];"
        "let filtered=items.slice();let idx=0;"
        "const listEl=document.getElementById('list');"
        "const imgEl=document.getElementById('chartImg');"
        "const titleEl=document.getElementById('viewerTitle');"
        "const metaEl=document.getElementById('viewerMeta');"
        "const openEl=document.getElementById('openLink');"
        "const searchEl=document.getElementById('search');"
        "function fmt(v){return Number(v).toFixed(2);}"
        "function renderList(){"
        "listEl.innerHTML='';"
        "filtered.forEach((x,i)=>{"
        "const d=document.createElement('div');d.className='item'+(i===idx?' active':'');"
        "d.innerHTML=`<div class='row'><span class='symbol'>${x.symbol}</span><span>${x.rank}</span></div>"
        "<div class='meta'>Total ${fmt(x.total)}% | Ann ${fmt(x.ann)}% | Win ${fmt(x.win)}% | Trades ${x.trades}</div>`;"
        "d.onclick=()=>{idx=i;renderList();renderViewer();};listEl.appendChild(d);"
        "});"
        "}"
        "function renderViewer(){"
        "if(!filtered.length){imgEl.removeAttribute('src');titleEl.textContent='无匹配结果';metaEl.textContent='';openEl.removeAttribute('href');return;}"
        "const x=filtered[idx];"
        "imgEl.src=x.png;"
        "titleEl.textContent=`${x.symbol} (${x.rank})`;"
        "metaEl.textContent=`Total ${fmt(x.total)}% | Ann ${fmt(x.ann)}% | Win ${fmt(x.win)}% | Trades ${x.trades}`;"
        "openEl.href=x.png;"
        "}"
        "function move(step){if(!filtered.length)return;idx=(idx+step+filtered.length)%filtered.length;renderList();renderViewer();}"
        "document.getElementById('prevBtn').onclick=()=>move(-1);"
        "document.getElementById('nextBtn').onclick=()=>move(1);"
        "document.getElementById('reset').onclick=()=>{searchEl.value='';filtered=items.slice();idx=0;renderList();renderViewer();};"
        "searchEl.addEventListener('input',()=>{const q=searchEl.value.trim().toUpperCase();filtered=items.filter(x=>x.symbol.toUpperCase().includes(q));idx=0;renderList();renderViewer();});"
        "window.addEventListener('keydown',(e)=>{if(e.key==='ArrowLeft')move(-1);if(e.key==='ArrowRight')move(1);});"
        "renderList();renderViewer();"
        "</script>"
        "</body></html>"
    )
    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    return index_path


def _render_one(args: tuple[dict, str, int, int, str, tuple[int, ...], int, str, dict, dict]) -> dict | None:
    row, data_dir_str, data_years, plot_years, style, mav, dpi, strategy_key, indicator_params, signal_params = args
    symbol = str(row["symbol"])
    out_dir = Path(row["_out_dir"])
    try:
        calculate_indicators, generate_signals = _resolve_strategy(strategy_key)
        df = _load_daily(symbol, Path(data_dir_str), data_years)
        if df.empty or not {"Open", "High", "Low", "Close", "Volume"}.issubset(df.columns):
            return None

        df_ind = _call_with_supported_kwargs(
            calculate_indicators,
            {"df": df, **(indicator_params or {})},
        )
        signals = _call_with_supported_kwargs(
            generate_signals,
            {"df": df_ind, **(signal_params or {})},
        )

        df_view = _last_years(df, plot_years)
        if len(df_view) < 60:
            return None

        signals_view = signals.reindex(df_view.index)
        out_png = out_dir / f"{symbol}.png"
        title = (
            f"{symbol}  rank={row.get('rank','')}  total={float(row['total_return_pct']):.1f}%  "
            f"ann={float(row['annualized_return_pct']):.1f}%  "
            f"win={float(row['win_rate_pct']):.1f}%  trades={int(row['total_trades'])}"
        )
        _plot_symbol(df_view, signals_view, out_png, title, style, mav, dpi)

        return {
            "symbol": symbol,
            "rank": str(row.get("rank", "")) or "",
            "total_return_pct": float(row["total_return_pct"]),
            "annualized_return_pct": float(row["annualized_return_pct"]),
            "win_rate_pct": float(row["win_rate_pct"]),
            "total_trades": int(row["total_trades"]),
            "png": str(out_png),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate charts from existing backtest results CSV.")
    parser.add_argument("--results-csv", required=True, help="Backtest results CSV containing total_return_pct etc.")
    parser.add_argument(
        "--strategy",
        default="ma_convergence",
        choices=sorted(STRATEGY_MODULES.keys()),
        help="Strategy used to recompute buy/sell markers.",
    )
    parser.add_argument(
        "--mode",
        default="topbottom",
        choices=["topbottom", "losers"],
        help="Pick mode: topbottom or losers only.",
    )
    parser.add_argument("--data-dir", default="data_cache", help="Directory containing daily CSVs.")
    parser.add_argument("--data-years", type=int, default=20, help="Data file suffix to use (e.g. 20 -> *_20y_1d_forward.csv).")
    parser.add_argument("--plot-years", type=int, default=5, help="Years to plot from last bar.")
    parser.add_argument("--top", type=int, default=15, help="Top N symbols to plot.")
    parser.add_argument("--bottom", type=int, default=15, help="Bottom N symbols to plot.")
    parser.add_argument("--limit", type=int, default=0, help="Limit symbols count in losers mode (0=all losers).")
    parser.add_argument("--out-dir", required=True, help="Output directory.")
    parser.add_argument("--style", default="charles", help="mplfinance style.")
    parser.add_argument("--mav", default="5,10,20,60", help="MA periods to draw, comma-separated.")
    parser.add_argument("--dpi", type=int, default=160, help="PNG dpi.")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers for chart rendering.")
    parser.add_argument("--no-stop-loss", action="store_true", help="Disable stop-loss in generate_signals.")
    parser.add_argument("--time-exit-days", type=int, default=0, help="Enable time-exit by days (0=disabled).")
    parser.add_argument("--disable-ma60-uptrend", action="store_true", help="Disable MA60 uptrend filter for ma60_pullback.")
    args = parser.parse_args()

    results_csv = Path(args.results_csv)
    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mav = tuple(int(x.strip()) for x in str(args.mav).split(",") if x.strip())
    if not mav:
        raise SystemExit("--mav must contain at least one integer period")

    picks = _pick_symbols(results_csv, args.mode, args.top, args.bottom, args.limit)
    if picks.empty:
        print("[WARN] no picks")
        return 0

    indicator_params: dict = {}
    signal_params: dict = {}

    if args.strategy == "ma_convergence":
        signal_params = {
            "stop_loss_enabled": (not args.no_stop_loss),
            "time_exit_enabled": int(args.time_exit_days) > 0,
            "max_holding_days": int(args.time_exit_days),
            "volume_filter_enabled": False,
            "volume_filter_mode": "none",
            "volume_ma_period": 20,
        }
    elif args.strategy == "ma60_pullback":
        indicator_params = {"ma60_uptrend_lookback": 5}
        signal_params = {
            "require_ma60_uptrend": (not args.disable_ma60_uptrend),
            "ma60_uptrend_lookback": 5,
        }

    rows = picks.to_dict(orient="records")
    for r in rows:
        r["_out_dir"] = str(out_dir)

    tasks = [
        (
            r,
            str(data_dir),
            int(args.data_years),
            int(args.plot_years),
            args.style,
            mav,
            int(args.dpi),
            args.strategy,
            indicator_params,
            signal_params,
        )
        for r in rows
    ]

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
        charts_df = pd.DataFrame(chart_rows)
        if args.mode == "topbottom":
            charts_df["_rank_order"] = charts_df["rank"].map({"TOP": 0, "BOTTOM": 1}).fillna(9).astype(int)
            charts_df["_sort_ret"] = np.where(
                charts_df["rank"] == "BOTTOM",
                charts_df["total_return_pct"],
                -charts_df["total_return_pct"],
            )
            charts_df = charts_df.sort_values(["_rank_order", "_sort_ret"], ascending=[True, True]).drop(
                columns=["_rank_order", "_sort_ret"]
            )
            title = f"Top {args.top} / Bottom {args.bottom} - {results_csv.name}"
        else:
            charts_df = charts_df.sort_values("total_return_pct", ascending=True)
            title = f"Losers ({len(charts_df)}) - {results_csv.name}"

        charts_csv = out_dir / "charts.csv"
        charts_df.to_csv(charts_csv, index=False, encoding="utf-8-sig")
        index_path = _write_index(
            out_dir=out_dir,
            title=title,
            rows=charts_df.to_dict(orient="records"),
        )
        print(f"[OK] charts={len(chart_rows)} csv={charts_csv} index={index_path} failures={failures}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
