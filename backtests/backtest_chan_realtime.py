"""
Chan theory backtest - realtime approximation (scheme 3).

This version enforces information reveal over time:
- It does not precompute signals on the full dataset.
- It re-evaluates using data up to the current bar only.
- A signal is tradable only when it first becomes visible.
"""

import os
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indicators.chan.chan_theory_realtime import ChanTheoryRealtime


def discover_cached_a_share_symbols(period='20y'):
    """Discover cached A-share symbols under data_cache."""
    cache_dir = 'data_cache'
    if not os.path.exists(cache_dir):
        return []

    suffix = f'_{period}_1d_forward.csv'
    valid_market_suffixes = ('.SZ', '.SS', '.SH', '.BJ')
    symbols = []

    for filename in os.listdir(cache_dir):
        if not filename.endswith(suffix):
            continue
        symbol = filename[:-len(suffix)]
        if symbol.endswith(valid_market_suffixes):
            symbols.append(symbol)

    return sorted(set(symbols))


def load_stock_data(symbol, period='20y'):
    """Load OHLCV data from cache."""
    cache_file = f'data_cache/{symbol}_{period}_1d_forward.csv'
    if not os.path.exists(cache_file):
        return None

    try:
        data = pd.read_csv(cache_file)
        if 'datetime' in data.columns:
            data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
            data = data.set_index('datetime')
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy().dropna()
        return data
    except Exception:
        return None


def backtest_realtime(data, symbol, initial_capital=100000):
    """
    Realtime-style backtest with incremental information reveal.
    """
    if data is None or len(data) < 252:
        return None

    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10 * 365)
    data_backtest = data[data.index >= start_date].copy()

    if len(data_backtest) < 100:
        return None

    capital = initial_capital
    position = 0.0
    trades = []

    seen_buy_signals = set()
    seen_sell_signals = set()
    visible_buy_count = 0
    visible_sell_count = 0

    commission = 0.001
    slippage = 0.0005

    for i in range(len(data_backtest)):
        hist = data_backtest.iloc[: i + 1]
        current_date = hist.index[-1]
        current_price = float(hist['Close'].iloc[-1])

        chan = ChanTheoryRealtime(k_type='day')
        chan.analyze(hist)

        newly_visible_buys = []
        for bp in chan.buy_points:
            signal_date = bp.get('index', bp.get('date'))
            signal_type = int(bp.get('type', 0))
            signal_key = (pd.Timestamp(signal_date), signal_type)
            if signal_key not in seen_buy_signals:
                newly_visible_buys.append(bp)
                seen_buy_signals.add(signal_key)

        newly_visible_sells = []
        for sp in chan.sell_points:
            signal_date = sp.get('index', sp.get('date'))
            signal_type = int(sp.get('type', 0))
            signal_key = (pd.Timestamp(signal_date), signal_type)
            if signal_key not in seen_sell_signals:
                newly_visible_sells.append(sp)
                seen_sell_signals.add(signal_key)

        visible_buy_count += len(newly_visible_buys)
        visible_sell_count += len(newly_visible_sells)

        # If both appear on same bar, prioritize exit to avoid optimistic same-day flip.
        if newly_visible_sells and position > 0:
            proceeds = position * current_price * (1 - slippage) * (1 - commission)
            capital += proceeds
            trades.append(
                {
                    'type': 'sell',
                    'date': current_date,
                    'price': current_price,
                    'value': proceeds,
                    'signal_date': newly_visible_sells[-1].get('index', newly_visible_sells[-1].get('date')),
                }
            )
            position = 0.0
        elif newly_visible_buys and position == 0:
            shares = capital / (current_price * (1 + slippage))
            cost = shares * current_price * (1 + slippage) * (1 + commission)
            capital -= cost
            position = shares
            trades.append(
                {
                    'type': 'buy',
                    'date': current_date,
                    'price': current_price,
                    'value': cost,
                    'signal_date': newly_visible_buys[-1].get('index', newly_visible_buys[-1].get('date')),
                }
            )

    final_value = capital + position * data_backtest['Close'].iloc[-1] * (1 - slippage) * (1 - commission)

    total_return = (final_value - initial_capital) / initial_capital * 100
    years = len(data_backtest) / 252
    annualized = ((final_value / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    profits = []
    for i, buy in enumerate(buy_trades):
        if i < len(sell_trades):
            profit = (sell_trades[i]['value'] - buy['value']) / buy['value']
            profits.append(profit)

    win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100 if profits else 0

    return {
        'symbol': symbol,
        'strategy': 'realtime',
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized,
        'win_rate': win_rate,
        'trade_count': len(profits),
        'buy_count': visible_buy_count,
        'sell_count': visible_sell_count,
    }


def main():
    test_symbols = discover_cached_a_share_symbols(period='20y')

    print('=' * 80)
    print('Chan Theory Backtest - Realtime Approximation (Scheme 3)')
    print('=' * 80)
    print('\nRealtime incremental simulation: no full-data precompute, no lookahead.\n')

    print(f'Detected cached A-share symbols: {len(test_symbols)}')
    if not test_symbols:
        print('No cached A-share data found under data_cache/*_20y_1d_forward.csv')
        return

    results = []

    for symbol in test_symbols:
        print(f'Processing {symbol}...')
        data = load_stock_data(symbol, '20y')

        if data is None:
            continue

        result = backtest_realtime(data, symbol)
        if result:
            results.append(result)

    print('\n' + '=' * 80)
    print('Summary - Realtime Incremental Backtest')
    print('=' * 80)
    if results:
        returns = [r['total_return'] for r in results]
        print(f'Stocks tested: {len(results)}')
        print(f'Average total return: {np.mean(returns):.2f}%')
        print(f'Median return: {np.median(returns):.2f}%')
        print(f'Best: {np.max(returns):.2f}% | Worst: {np.min(returns):.2f}%')
        print(f'Positive: {sum(1 for r in returns if r > 0)}/{len(returns)}')
        print(f'Average annual: {np.mean([r["annualized_return"] for r in results]):.2f}%')
        print(f'Average win rate: {np.mean([r["win_rate"] for r in results]):.1f}%')

    if results:
        output_dir = 'results/chan_backtest_realtime'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'backtest_realtime_summary.csv')
        pd.DataFrame(results).to_csv(output_file, index=False, encoding='utf-8-sig')
        print('\n' + '=' * 80)
        print(f'Results saved: {output_file}')


if __name__ == '__main__':
    main()
