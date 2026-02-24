import os
import sys
from typing import List

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtests.backtest_chan_realtime import load_stock_data
from indicators.chan.chan_theory_realtime import ChanTheoryRealtime
from visualization.kline_plotter import KLinePlotter


def pick_symbols(csv_path: str, top_n: int = 3, bottom_n: int = 3) -> List[str]:
    df = pd.read_csv(csv_path)
    if df.empty:
        return []
    df = df.sort_values("total_return", ascending=False)
    selected = pd.concat([df.head(top_n), df.tail(bottom_n)], axis=0)
    selected = selected.drop_duplicates(subset=["symbol"], keep="first")
    return selected["symbol"].tolist()


def build_signal_series(plot_data: pd.DataFrame, chan: ChanTheoryRealtime):
    buy_signals = pd.Series(0.0, index=plot_data.index, dtype=float)
    sell_signals = pd.Series(0.0, index=plot_data.index, dtype=float)

    for bp in chan.buy_points:
        if bp["type"] in [1, 2] and bp["index"] in plot_data.index:
            buy_signals.loc[bp["index"]] = float(bp["price"])

    for sp in chan.sell_points:
        if sp["type"] in [1, 2] and sp["index"] in plot_data.index:
            sell_signals.loc[sp["index"]] = float(sp["price"])

    return buy_signals, sell_signals


def main():
    input_csv = "results/chan_backtest_realtime/backtest_realtime_hot_stocks.csv"
    output_dir = "results/chan_backtest_realtime/hot_stock_kline"
    os.makedirs(output_dir, exist_ok=True)

    symbols = pick_symbols(input_csv, top_n=3, bottom_n=3)
    if not symbols:
        print(f"No symbols found in {input_csv}")
        return

    print(f"Selected symbols: {symbols}")
    plotter = KLinePlotter(style="charles")

    for symbol in symbols:
        print(f"Plotting {symbol} ...")
        data = load_stock_data(symbol, period="20y")
        if data is None or len(data) < 120:
            print(f"  Skip {symbol}: insufficient data")
            continue

        chan = ChanTheoryRealtime(k_type="day")
        chan.analyze(data)

        # Keep the chart readable: only display recent 2 years of candles.
        plot_data = data.tail(500).copy()
        buy_signals, sell_signals = build_signal_series(plot_data, chan)

        save_path = os.path.join(output_dir, f"{symbol}_kline_boll.png")
        plotter.plot_with_signals_and_indicators(
            data=plot_data,
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            title=f"{symbol} Realtime Buy/Sell Timing with BOLL",
            show_boll=True,
            show_rsi=False,
            show_volume=True,
            boll_period=20,
            boll_std=2,
            save_path=save_path,
        )
        print(f"  Saved: {save_path}")

    print(f"Done. Output dir: {output_dir}")


if __name__ == "__main__":
    main()

