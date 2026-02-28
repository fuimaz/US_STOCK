from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    required = ["Open", "High", "Low", "Close"]
    if not all(col in df.columns for col in required):
        return pd.DataFrame()
    for col in required + (["Volume"] if "Volume" in df.columns else []):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    df = df[df["Close"] > 0]
    return df


def load_minute_60m(symbol: str, minute_dir: Path) -> pd.DataFrame:
    exact = minute_dir / f"{symbol}_60min.csv"
    if exact.exists():
        path = exact
    else:
        cands = sorted(minute_dir.glob(f"{symbol}*_60min.csv"))
        if not cands:
            return pd.DataFrame()
        path = cands[0]

    df = pd.read_csv(path)
    if "datetime" in df.columns:
        dt_col = "datetime"
    elif "day" in df.columns:
        dt_col = "day"
    else:
        return pd.DataFrame()
    df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
    try:
        if getattr(df[dt_col].dt, "tz", None) is not None:
            df[dt_col] = df[dt_col].dt.tz_localize(None)
    except Exception:
        pass
    df = df.dropna(subset=[dt_col]).set_index(dt_col).sort_index()
    df = _normalize_ohlcv(df)
    return df


def load_daily(symbol: str, daily_dir: Path) -> pd.DataFrame:
    exact = daily_dir / f"{symbol}_20y_1d_forward.csv"
    if exact.exists():
        path = exact
    else:
        cands = sorted(daily_dir.glob(f"{symbol}_*1d*.csv"))
        if not cands:
            return pd.DataFrame()
        path = cands[0]

    df = pd.read_csv(path)
    dt_col: Optional[str] = None
    for c in ("datetime", "day", "Date", "date"):
        if c in df.columns:
            dt_col = c
            break
    if dt_col is None:
        return pd.DataFrame()
    df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
    try:
        if getattr(df[dt_col].dt, "tz", None) is not None:
            df[dt_col] = df[dt_col].dt.tz_localize(None)
    except Exception:
        pass
    df = df.dropna(subset=[dt_col]).set_index(dt_col).sort_index()
    df = _normalize_ohlcv(df)
    return df


def plot_candles(ax: plt.Axes, df: pd.DataFrame, title: str) -> None:
    if df.empty:
        ax.text(0.5, 0.5, f"{title}\n(no data)", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return

    x = np.arange(len(df), dtype=float)
    o = df["Open"].values
    h = df["High"].values
    l = df["Low"].values
    c = df["Close"].values

    up = c >= o
    down = ~up
    color_up = "#d62728"
    color_down = "#2ca02c"
    width = max(0.2, 0.6 if len(df) < 300 else 0.45)

    ax.vlines(x[up], l[up], h[up], color=color_up, linewidth=0.6, alpha=0.9)
    ax.vlines(x[down], l[down], h[down], color=color_down, linewidth=0.6, alpha=0.9)

    for i in np.where(up)[0]:
        y = o[i]
        hgt = max(c[i] - o[i], 1e-6)
        ax.add_patch(
            patches.Rectangle((x[i] - width / 2, y), width, hgt, facecolor=color_up, edgecolor=color_up, linewidth=0.4)
        )
    for i in np.where(down)[0]:
        y = c[i]
        hgt = max(o[i] - c[i], 1e-6)
        ax.add_patch(
            patches.Rectangle((x[i] - width / 2, y), width, hgt, facecolor=color_down, edgecolor=color_down, linewidth=0.4)
        )

    ax.set_xlim(-1, len(df))
    ax.set_title(title, fontsize=10)
    ax.grid(alpha=0.2, linestyle="--")

    n_ticks = min(8, len(df))
    if n_ticks > 1:
        tick_pos = np.linspace(0, len(df) - 1, n_ticks).astype(int)
        tick_labels = [df.index[i].strftime("%Y-%m-%d") for i in tick_pos]
        ax.set_xticks(tick_pos)
        ax.set_xticklabels(tick_labels, rotation=30, ha="right", fontsize=8)
    else:
        ax.set_xticks([])


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot top-drawdown symbols with 60min and daily candlesticks in one figure.")
    parser.add_argument(
        "--drawdown-csv",
        default="results/volume_breakout_minute_60min_time_stop20_all/drawdown_detail_60min_time_stop20.csv",
        help="Drawdown detail csv path.",
    )
    parser.add_argument("--top-n", type=int, default=5, help="Top N symbols by drawdown.")
    parser.add_argument(
        "--output",
        default="results/volume_breakout_minute_60min_time_stop20_all/top_drawdown_klines_60m_daily.png",
        help="Output image path.",
    )
    args = parser.parse_args()

    drawdown_path = Path(args.drawdown_csv)
    if not drawdown_path.exists():
        raise FileNotFoundError(f"drawdown csv not found: {drawdown_path}")

    dd = pd.read_csv(drawdown_path)
    if dd.empty or "symbol" not in dd.columns:
        raise ValueError("drawdown csv has no symbol rows")

    top = dd.sort_values("max_drawdown_pct", ascending=False).head(args.top_n)
    symbols = top["symbol"].astype(str).tolist()

    minute_dir = Path("data_cache") / "a_stock_minute"
    daily_dir = Path("data_cache")

    fig, axes = plt.subplots(len(symbols), 2, figsize=(18, 3.8 * len(symbols)), constrained_layout=True)
    if len(symbols) == 1:
        axes = np.array([axes])

    for i, sym in enumerate(symbols):
        m60 = load_minute_60m(sym, minute_dir)
        d1 = load_daily(sym, daily_dir)

        if not m60.empty and not d1.empty:
            start = m60.index.min().normalize()
            end = m60.index.max().normalize()
            d1 = d1[(d1.index >= start) & (d1.index <= end)]

        dd_val = top[top["symbol"] == sym]["max_drawdown_pct"].iloc[0]
        plot_candles(axes[i, 0], m60, f"{sym} - 60min K  (MDD {dd_val:.2f}%)")
        plot_candles(axes[i, 1], d1, f"{sym} - Daily K")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.suptitle("Top Drawdown Symbols: 60min & Daily Candlesticks", fontsize=14)
    fig.savefig(out_path, dpi=150)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
