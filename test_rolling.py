"""
滚动窗口验证 - 检查是否存在未来函数

问题：缠论分型、笔、线段的确认都需要后续K线
如果在当天收盘时无法确认分型，那么买卖点也不能被立即识别

这个脚本使用滚动窗口模拟实际交易场景：
- 每天只使用当天及之前的数据
- 检查当天是否能识别出买卖点
"""
import pandas as pd
import numpy as np
from datetime import timedelta
from chan_theory import ChanTheory


def rolling_backtest(data, window_days=252):
    """
    滚动回测：每天只用过去window_days天的数据
    检查当天收盘后是否能识别出买卖点
    """
    print("Rolling window backtest (simulating real-time trading)...")
    print(f"Window size: {window_days} days")
    
    signals = []
    
    # 从第window_days天开始滚动
    for i in range(window_days, len(data)):
        current_date = data.index[i]
        
        # 只使用过去window_days天的数据
        hist_data = data.iloc[i-window_days:i+1].copy()
        
        # 运行缠论分析
        chan = ChanTheory(k_type='day')
        chan.analyze(hist_data)
        
        # 检查当天是否有买卖点
        for bp in chan.buy_points:
            if bp['date'] == current_date:
                signals.append({
                    'date': current_date,
                    'type': 'buy',
                    'bp_type': bp['type'],
                    'price': bp['price']
                })
        
        for sp in chan.sell_points:
            if sp['date'] == current_date:
                signals.append({
                    'date': current_date,
                    'type': 'sell',
                    'sp_type': sp['type'],
                    'price': sp['price']
                })
        
        if i % 252 == 0:
            print(f"  Processed {i}/{len(data)} days, found {len(signals)} signals")
    
    return signals


def compare_with_full_data(data, rolling_signals):
    """
    对比滚动窗口和完整数据的买卖点
    """
    print("\nComparing with full data analysis...")
    
    # 完整数据分析
    chan = ChanTheory(k_type='day')
    chan.analyze(data)
    
    full_signals = []
    for bp in chan.buy_points:
        full_signals.append({'date': bp['date'], 'type': 'buy', 'bp_type': bp['type'], 'price': bp['price']})
    for sp in chan.sell_points:
        full_signals.append({'date': sp['date'], 'type': 'sell', 'sp_type': sp['type'], 'price': sp['price']})
    
    print(f"Full data signals: {len(full_signals)}")
    print(f"Rolling window signals: {len(rolling_signals)}")
    
    # 检查差异
    rolling_dates = set(s['date'] for s in rolling_signals)
    full_dates = set(s['date'] for s in full_signals)
    
    missing = full_dates - rolling_dates
    extra = rolling_dates - full_dates
    
    print(f"Signals in full but not in rolling: {len(missing)}")
    print(f"Signals in rolling but not in full: {len(extra)}")
    
    if missing:
        print("\nSample missing signals (future bias):")
        for d in sorted(list(missing))[:5]:
            sig = [s for s in full_signals if s['date'] == d][0]
            print(f"  {d.strftime('%Y-%m-%d')}: {sig['type']} type {sig.get('bp_type', sig.get('sp_type', 0))} @ {sig['price']:.2f}")
    
    return rolling_signals, full_signals


def simple_backtest(signals, data, initial_capital=100000):
    """
    简单回测
    """
    capital = initial_capital
    position = 0
    
    for sig in sorted(signals, key=lambda x: x['date']):
        if sig['type'] == 'buy' and position == 0:
            price = sig['price']
            shares = capital / price
            capital = 0
            position = shares
        elif sig['type'] == 'sell' and position > 0:
            price = sig['price']
            capital = position * price
            position = 0
    
    final_value = capital + position * data['Close'].iloc[-1]
    return (final_value - initial_capital) / initial_capital * 100


def main():
    # 加载数据
    data = pd.read_csv('data_cache/000001.SZ_20y_1d_forward.csv')
    data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
    data = data.set_index('datetime')
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    
    # 只使用近3年数据（加快计算）
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=3*365)
    data = data[data.index >= start_date].copy()
    
    print("="*70)
    print("Rolling Window Validation")
    print("="*70)
    print(f"Data: 000001.SZ ({len(data)} days from {data.index[0].date()} to {data.index[-1].date()})")
    
    # 方法1：滚动窗口（正确做法）
    rolling_signals = rolling_backtest(data, window_days=252)
    
    # 方法2：完整数据（可能存在未来函数）
    rolling_signals, full_signals = compare_with_full_data(data, rolling_signals)
    
    # 回测对比
    print("\n" + "="*70)
    print("Backtest Comparison")
    print("="*70)
    
    ret_rolling = simple_backtest(rolling_signals, data)
    ret_full = simple_backtest(full_signals, data)
    
    print(f"Rolling window return: {ret_rolling:.2f}%")
    print(f"Full data return: {ret_full:.2f}%")
    
    # 买入持有
    bh_return = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0] * 100
    print(f"Buy & Hold return: {bh_return:.2f}%")
    
    print("\n" + "="*70)
    if len(rolling_signals) != len(full_signals):
        print("WARNING: Different number of signals detected!")
        print("This indicates lookahead bias (future function) in the full data analysis.")
    else:
        print("Signal counts match. May not have significant lookahead bias.")
    print("="*70)


if __name__ == '__main__':
    main()
