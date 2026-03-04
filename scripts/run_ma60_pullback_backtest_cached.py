"""Batch backtest MA60 pullback strategy on cached daily data."""

import argparse
import glob
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.ma60_pullback_strategy import calculate_indicators, generate_signals


def backtest_one(fp: str, initial_capital: float, stop_loss_enabled: bool):
    symbol = os.path.basename(fp).split("_")[0]
    try:
        df = pd.read_csv(fp)
    except Exception as e:
        return {"symbol": symbol, "status": f"read_error:{e}"}, []

    if "datetime" not in df.columns:
        return {"symbol": symbol, "status": "missing_datetime"}, []

    dt = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    mask = dt.notna()
    df = df.loc[mask].copy()
    dt = dt.loc[mask]
    df.index = dt

    keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    if "Close" not in keep_cols:
        return {"symbol": symbol, "status": "missing_close"}, []

    df = df[keep_cols].sort_index()
    if len(df) < 120:
        return {"symbol": symbol, "status": "too_short", "bars": len(df)}, []

    try:
        ind = calculate_indicators(df)
        sig = generate_signals(ind, stop_loss_enabled=bool(stop_loss_enabled))
    except Exception as e:
        return {"symbol": symbol, "status": f"strategy_error:{e}", "bars": len(df)}, []

    cash = float(initial_capital)
    position = 0
    entry_price = np.nan
    entry_date = None
    equity_curve = []
    trades = []

    for i in range(len(sig)):
        row = sig.iloc[i]
        date = sig.index[i]
        close_price = float(row["Close"])
        signal = int(row.get("signal", 0))

        equity_curve.append(cash + position * close_price)

        if signal == 1 and position == 0 and cash > 0:
            shares = int(cash / close_price)
            if shares > 0:
                position = shares
                cash -= shares * close_price
                entry_price = close_price
                entry_date = date

        elif signal == -1 and position > 0:
            exit_price = row.get("exit_price", np.nan)
            if pd.isna(exit_price):
                exit_price = close_price
            exit_price = float(exit_price)

            cash += position * exit_price
            trades.append(
                {
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "exit_date": date,
                    "entry_price": float(entry_price),
                    "exit_price": exit_price,
                    "return_pct": (exit_price - entry_price) / entry_price * 100.0,
                    "holding_days": int((date - entry_date).days) if entry_date is not None else 0,
                    "exit_reason": str(row.get("exit_reason", "")),
                }
            )
            position = 0
            entry_price = np.nan
            entry_date = None

    if position > 0:
        last_date = sig.index[-1]
        last_price = float(sig["Close"].iloc[-1])
        cash += position * last_price
        trades.append(
            {
                "symbol": symbol,
                "entry_date": entry_date,
                "exit_date": last_date,
                "entry_price": float(entry_price),
                "exit_price": last_price,
                "return_pct": (last_price - entry_price) / entry_price * 100.0,
                "holding_days": int((last_date - entry_date).days) if entry_date is not None else 0,
                "exit_reason": "final_bar",
            }
        )

    final_capital = float(cash)
    total_return_pct = (final_capital - initial_capital) / initial_capital * 100.0

    start_date = sig.index[0]
    end_date = sig.index[-1]
    days = max(int((end_date - start_date).days), 1)
    years = days / 365.0
    annualized_return_pct = (
        ((final_capital / initial_capital) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0
    )

    eq = pd.Series(equity_curve)
    dd = (eq.cummax() - eq) / eq.cummax().replace(0, np.nan)
    max_drawdown_pct = float(dd.max() * 100.0) if len(dd) else 0.0

    if trades:
        wins = sum(1 for t in trades if t["return_pct"] > 0)
        win_rate_pct = wins / len(trades) * 100.0
        avg_trade_return_pct = float(np.mean([t["return_pct"] for t in trades]))
        avg_holding_days = float(np.mean([t["holding_days"] for t in trades]))
    else:
        win_rate_pct = 0.0
        avg_trade_return_pct = 0.0
        avg_holding_days = 0.0

    summary = {
        "symbol": symbol,
        "status": "ok",
        "bars": len(sig),
        "start_date": start_date,
        "end_date": end_date,
        "buy_signals": int((sig["signal"] == 1).sum()),
        "sell_signals": int((sig["signal"] == -1).sum()),
        "trades": len(trades),
        "final_capital": final_capital,
        "total_return_pct": total_return_pct,
        "annualized_return_pct": annualized_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate_pct": win_rate_pct,
        "avg_trade_return_pct": avg_trade_return_pct,
        "avg_holding_days": avg_holding_days,
    }
    return summary, trades


def main():
    parser = argparse.ArgumentParser(description="Run MA60 pullback backtest on cached stocks.")
    parser.add_argument("--pattern", default="data_cache/*_20y_1d_forward.csv")
    parser.add_argument("--capital", type=float, default=100000.0)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    parser.add_argument("--no-stop-loss", action="store_true", help="Disable MA10-vs-MA60 stop loss.")
    args = parser.parse_args()

    files = sorted(glob.glob(args.pattern))
    if not files:
        raise SystemExit(f"No files matched pattern: {args.pattern}")

    results = []
    all_trades = []

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(backtest_one, fp, args.capital, (not args.no_stop_loss)): fp
            for fp in files
        }
        total = len(futures)
        done = 0
        for fut in as_completed(futures):
            done += 1
            summary, trades = fut.result()
            results.append(summary)
            all_trades.extend(trades)
            if done % 20 == 0 or done == total:
                print(f"progress {done}/{total}", flush=True)

    results_df = pd.DataFrame(results)
    ok_df = results_df[results_df["status"] == "ok"].copy()
    if not ok_df.empty:
        ok_df = ok_df.sort_values("total_return_pct", ascending=False)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("results", exist_ok=True)
    summary_path = os.path.join("results", f"ma60_pullback_backtest_summary_{now}.csv")
    trades_path = os.path.join("results", f"ma60_pullback_backtest_trades_{now}.csv")
    results_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(all_trades).to_csv(trades_path, index=False, encoding="utf-8-sig")

    print(f"workers={args.workers}")
    print(f"stop_loss_enabled={not args.no_stop_loss}")
    print(f"files_total={len(files)}")
    print(f"symbols_ok={len(ok_df)}")
    print(f"summary_path={summary_path}")
    print(f"trades_path={trades_path}")

    if not ok_df.empty:
        pos = int((ok_df["total_return_pct"] > 0).sum())
        print(f"mean_return_pct={ok_df['total_return_pct'].mean():.2f}")
        print(f"median_return_pct={ok_df['total_return_pct'].median():.2f}")
        print(f"positive_symbols={pos}/{len(ok_df)}")
        print(f"mean_annualized_pct={ok_df['annualized_return_pct'].mean():.2f}")
        print(f"mean_max_drawdown_pct={ok_df['max_drawdown_pct'].mean():.2f}")
        print(f"total_trades={int(ok_df['trades'].sum())}")

        cols = [
            "symbol",
            "total_return_pct",
            "annualized_return_pct",
            "max_drawdown_pct",
            "trades",
            "win_rate_pct",
        ]
        print("top5:")
        print(ok_df[cols].head(5).to_string(index=False))
        print("bottom5:")
        print(ok_df[cols].tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
