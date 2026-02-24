"""
对比3个改进方案与原版的性能
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入所有版本
from chan_theory_realtime import ChanTheoryRealtime
from chan_theory_improved_a import ChanTheoryImprovedA
from chan_theory_improved_b import ChanTheoryImprovedB
from chan_theory_improved_c import ChanTheoryImprovedC


def load_cached_data(symbol, period='20y'):
    """加载股票数据"""
    cache_file = f'data_cache/{symbol}_{period}_1d_forward.csv'
    if not os.path.exists(cache_file):
        return None
    
    try:
        data = pd.read_csv(cache_file)
        if 'datetime' in data.columns:
            data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
            data = data.set_index('datetime')
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        data = data.dropna()
        return data
    except:
        return None


def backtest_strategy(data, symbol, strategy_class, strategy_name, **kwargs):
    """
    回测单个策略
    
    Args:
        data: 股票数据
        symbol: 股票代码
        strategy_class: 策略类
        strategy_name: 策略名称
        **kwargs: 策略参数
    """
    if data is None or len(data) < 252 * 2:
        return None
    
    # 只使用近2年数据（加快测试速度）
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=2*365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 100:
        return None
    
    # 创建策略实例
    strategy = strategy_class(**kwargs)
    result = strategy.analyze(data)
    
    # 获取回测区间内的买卖点
    buy_points = [bp for bp in strategy.buy_points 
                  if bp['index'] in data_backtest.index and bp['type'] in [1, 2]]
    sell_points = [sp for sp in strategy.sell_points 
                   if sp['index'] in data_backtest.index and sp['type'] in [1, 2]]
    
    # 回测交易
    initial_capital = 100000
    capital = initial_capital
    position = 0
    trades = []
    
    # 合并信号
    all_signals = []
    for bp in buy_points:
        all_signals.append({'date': bp['index'], 'type': 'buy', 'price': bp['price']})
    for sp in sell_points:
        all_signals.append({'date': sp['index'], 'type': 'sell', 'price': sp['price']})
    
    all_signals.sort(key=lambda x: x['date'])
    
    commission = 0.001
    slippage = 0.0005
    
    for signal in all_signals:
        current_price = signal['price']
        
        if signal['type'] == 'buy' and position == 0:
            shares = capital / (current_price * (1 + slippage))
            cost = shares * current_price * (1 + slippage) * (1 + commission)
            capital -= cost
            position = shares
            trades.append({'type': 'buy', 'date': signal['date'], 'price': current_price})
        
        elif signal['type'] == 'sell' and position > 0:
            proceeds = position * current_price * (1 - slippage) * (1 - commission)
            capital += proceeds
            trades.append({'type': 'sell', 'date': signal['date'], 'price': current_price})
            position = 0
    
    # 计算最终价值
    final_price = data_backtest['Close'].iloc[-1]
    if position > 0:
        final_value = capital + position * final_price * (1 - slippage) * (1 - commission)
    else:
        final_value = capital
    
    # 计算收益
    total_return = (final_value - initial_capital) / initial_capital * 100
    years = len(data_backtest) / 252
    annualized = ((final_value / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # 买入持有收益
    first_price = data_backtest['Close'].iloc[0]
    buyhold_return = (final_price - first_price) / first_price * 100
    
    # 胜率
    profits = []
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    
    for i, buy in enumerate(buy_trades):
        if i < len(sell_trades):
            profit = (sell_trades[i]['price'] - buy['price']) / buy['price']
            profits.append(profit)
    
    win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100 if profits else 0
    
    return {
        'symbol': symbol,
        'strategy': strategy_name,
        'total_return': total_return,
        'annualized_return': annualized,
        'buyhold_return': buyhold_return,
        'excess_return': total_return - buyhold_return,
        'win_rate': win_rate,
        'trade_count': len(profits),
        'buy_signal_count': len(buy_points),
        'sell_signal_count': len(sell_points),
    }


def compare_strategies(test_stocks):
    """对比所有策略"""
    
    strategies = [
        (ChanTheoryRealtime, 'Original', {}),
        (ChanTheoryImprovedA, 'Improved-A (Volatility)', {'volatility_threshold': 1.5}),
        (ChanTheoryImprovedB, 'Improved-B (Volume)', {'volume_threshold': 1.2}),
        (ChanTheoryImprovedC, 'Improved-C (Multi-TF)', {'trend_strength_threshold': 0.03, 'ma_confirmation': True}),
    ]
    
    all_results = {name: [] for _, name, _ in strategies}
    
    print("=" * 120)
    print("STRATEGY COMPARISON - 4 Versions")
    print("=" * 120)
    print(f"Testing {len(test_stocks)} stocks with 2-year backtest...")
    print()
    
    for i, (symbol, name) in enumerate(test_stocks, 1):
        print(f"[{i}/{len(test_stocks)}] Testing: {name} ({symbol})")
        
        data = load_cached_data(symbol)
        if data is None:
            print(f"  No data, skipping")
            continue
        
        for strategy_class, strategy_name, kwargs in strategies:
            result = backtest_strategy(data, symbol, strategy_class, strategy_name, **kwargs)
            if result:
                all_results[strategy_name].append(result)
                print(f"  {strategy_name:<25} Return: {result['total_return']:>7.1f}% | "
                      f"WinRate: {result['win_rate']:>5.1f}% | Trades: {result['trade_count']:>2}")
        
        print()
    
    # 汇总统计
    print("=" * 120)
    print("SUMMARY STATISTICS")
    print("=" * 120)
    print()
    
    summary_data = []
    
    for strategy_name, results in all_results.items():
        if not results:
            continue
        
        df = pd.DataFrame(results)
        
        summary = {
            'Strategy': strategy_name,
            'Stocks': len(results),
            'Avg_Return': df['total_return'].mean(),
            'Avg_Excess': df['excess_return'].mean(),
            'Avg_WinRate': df['win_rate'].mean(),
            'Avg_Trades': df['trade_count'].mean(),
            'Positive_Excess': (df['excess_return'] > 0).sum(),
            'Positive_Rate': (df['excess_return'] > 0).mean() * 100,
        }
        summary_data.append(summary)
        
        print(f"[{strategy_name}]")
        print(f"  Stocks tested: {summary['Stocks']}")
        print(f"  Avg Return: {summary['Avg_Return']:.2f}%")
        print(f"  Avg Excess: {summary['Avg_Excess']:+.2f}%")
        print(f"  Avg Win Rate: {summary['Avg_WinRate']:.2f}%")
        print(f"  Avg Trades: {summary['Avg_Trades']:.1f}")
        print(f"  Positive Excess: {summary['Positive_Excess']}/{summary['Stocks']} ({summary['Positive_Rate']:.1f}%)")
        print()
    
    # 对比表
    print("=" * 120)
    print("COMPARISON TABLE")
    print("=" * 120)
    print(f"{'Strategy':<25} {'Avg Return':<12} {'Avg Excess':<12} {'Win Rate':<10} {'Trades':<8} {'Positive %':<10}")
    print("-" * 120)
    
    for s in summary_data:
        print(f"{s['Strategy']:<25} {s['Avg_Return']:>10.2f}% {s['Avg_Excess']:>+10.2f}% "
              f"{s['Avg_WinRate']:>8.2f}% {s['Avg_Trades']:>6.1f} {s['Positive_Rate']:>8.1f}%")
    
    print("-" * 120)
    print()
    
    # 排名
    print("=" * 120)
    print("RANKING BY METRIC")
    print("=" * 120)
    
    metrics = ['Avg_Return', 'Avg_Excess', 'Avg_WinRate', 'Positive_Rate']
    
    for metric in metrics:
        print(f"\n[{metric}]")
        sorted_data = sorted(summary_data, key=lambda x: x[metric], reverse=True)
        for rank, s in enumerate(sorted_data, 1):
            print(f"  {rank}. {s['Strategy']:<25} {s[metric]:.2f}")
    
    print()
    print("=" * 120)
    
    return summary_data


def main():
    """主函数"""
    # 测试股票（选择一些有代表性的）
    test_stocks = [
        ('000001.SZ', 'Ping An Bank'),
        ('000333.SZ', 'Midea Group'),
        ('000625.SZ', 'Changan Auto'),
        ('002475.SZ', 'Luxshare'),
        ('002594.SZ', 'BYD'),
        ('600276.SS', 'Hengrui Medicine'),
        ('600519.SS', 'Moutai'),
        ('601012.SS', 'LONGi'),
        ('601899.SS', 'Zijin Mining'),
        ('000858.SZ', 'Wuliangye'),
    ]
    
    results = compare_strategies(test_stocks)
    
    return results


if __name__ == '__main__':
    main()
