"""
缠论策略对比测试
对比三种策略：
1. 所有买卖点（一买/二买/一卖/二卖）- 基准
2. 只忽略一卖（使用一买/二买/二卖）- 更激进的卖出
3. 忽略二买二卖（只使用一买/一卖）- 只抓主要趋势
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from datetime import timedelta
from chan_theory import ChanTheory


def load_stock_data(symbol, period='20y'):
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


def backtest_strategy(data, symbol, strategy_type='all', initial_capital=100000):
    """
    回测指定策略
    
    Args:
        strategy_type: 
            'all' - 使用所有买卖点（一买/二买/一卖/二卖）
            'no_first_sell' - 忽略一卖（使用一买/二买/二卖）
            'only_first' - 只使用一买/一卖（忽略二买/二卖）
    """
    if data is None or len(data) < 252:
        return None
    
    # 只使用近10年数据回测
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10*365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 100:
        return None
    
    # 运行缠论分析
    chan = ChanTheory(k_type='day')
    result = chan.analyze(data)
    
    # 根据策略类型筛选买卖点
    buy_points = []
    sell_points = []
    
    for bp in chan.buy_points:
        if bp['index'] not in data_backtest.index:
            continue
        if strategy_type == 'all':
            if bp['type'] in [1, 2]:
                buy_points.append(bp)
        elif strategy_type == 'no_first_sell':
            if bp['type'] in [1, 2]:  # 使用一买/二买
                buy_points.append(bp)
        elif strategy_type == 'only_first':
            if bp['type'] == 1:  # 只使用一买
                buy_points.append(bp)
    
    for sp in chan.sell_points:
        if sp['index'] not in data_backtest.index:
            continue
        if strategy_type == 'all':
            if sp['type'] in [1, 2]:
                sell_points.append(sp)
        elif strategy_type == 'no_first_sell':
            if sp['type'] == 2:  # 只使用二卖，忽略一卖
                sell_points.append(sp)
        elif strategy_type == 'only_first':
            if sp['type'] == 1:  # 只使用一卖
                sell_points.append(sp)
    
    # 回测
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
    
    # 执行交易
    commission = 0.001
    slippage = 0.0005
    
    for signal in all_signals:
        current_price = signal['price']
        
        if signal['type'] == 'buy' and position == 0:
            shares = capital / (current_price * (1 + slippage))
            cost = shares * current_price * (1 + slippage) * (1 + commission)
            capital -= cost
            position = shares
            trades.append({'type': 'buy', 'date': signal['date'], 'price': current_price, 'value': cost})
            
        elif signal['type'] == 'sell' and position > 0:
            proceeds = position * current_price * (1 - slippage) * (1 - commission)
            capital += proceeds
            trades.append({'type': 'sell', 'date': signal['date'], 'price': current_price, 'value': proceeds})
            position = 0
    
    # 计算最终价值
    final_value = capital + position * data_backtest['Close'].iloc[-1] * (1 - slippage) * (1 - commission)
    
    # 计算收益指标
    total_return = (final_value - initial_capital) / initial_capital * 100
    years = len(data_backtest) / 252
    annualized = ((final_value / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # 胜率
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
        'strategy': strategy_type,
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized,
        'win_rate': win_rate,
        'trade_count': len(profits),
        'buy_count': len(buy_points),
        'sell_count': len(sell_points)
    }


def test_stock(symbol):
    """测试单只股票的三种策略"""
    data = load_stock_data(symbol, '20y')
    if data is None:
        return None
    
    results = {}
    for strategy in ['all', 'no_first_sell', 'only_first']:
        result = backtest_strategy(data, symbol, strategy)
        if result:
            results[strategy] = result
    
    return results


def print_comparison(symbol, results):
    """打印对比结果"""
    if not results:
        return
    
    strategy_names = {
        'all': '全部买卖点(一买/二买/一卖/二卖)',
        'no_first_sell': '忽略一卖(一买/二买/二卖)',
        'only_first': '只使用一买一卖'
    }
    
    print(f"\n{'='*80}")
    print(f"股票: {symbol}")
    print(f"{'='*80}")
    print(f"{'策略':<25} {'总收益':>10} {'年化':>10} {'胜率':>8} {'交易数':>8} {'买/卖信号':>10}")
    print('-'*80)
    
    for strategy in ['all', 'no_first_sell', 'only_first']:
        if strategy in results:
            r = results[strategy]
            print(f"{strategy_names[strategy]:<20} {r['total_return']:>10.2f}% {r['annualized_return']:>10.2f}% {r['win_rate']:>8.1f}% {r['trade_count']:>8} {r['buy_count']}/{r['sell_count']:>5}")
    
    # 找出最佳策略
    best = max(results.items(), key=lambda x: x[1]['total_return'])
    print(f"\n最佳策略: {strategy_names[best[0]]} ({best[1]['total_return']:.2f}%)")


def main():
    """主函数"""
    test_symbols = [
        '000001.SZ', '000002.SZ', '000333.SZ', '000858.SZ', '002304.SZ',
        '002415.SZ', '002594.SZ', '300750.SZ', '600036.SS', '600276.SS',
        '600519.SS', '601186.SS', '601318.SS', '601888.SS', '603288.SS'
    ]
    
    print("="*80)
    print("缠论策略对比测试")
    print("="*80)
    print("\n策略说明:")
    print("1. 全部买卖点: 使用一买/二买/一卖/二卖")
    print("2. 忽略一卖: 使用一买/二买/二卖 (让利润奔跑)")
    print("3. 只使用一买一卖: 只抓主要趋势转折点")
    
    all_results = []
    
    for symbol in test_symbols:
        results = test_stock(symbol)
        if results:
            print_comparison(symbol, results)
            all_results.append(results)
    
    # 汇总统计
    if all_results:
        print("\n" + "="*80)
        print("汇总统计")
        print("="*80)
        
        for strategy in ['all', 'no_first_sell', 'only_first']:
            returns = [r[strategy]['total_return'] for r in all_results if strategy in r]
            annual = [r[strategy]['annualized_return'] for r in all_results if strategy in r]
            win_rates = [r[strategy]['win_rate'] for r in all_results if strategy in r]
            
            if returns:
                strategy_names = {
                    'all': '全部买卖点',
                    'no_first_sell': '忽略一卖',
                    'only_first': '只使用一买一卖'
                }
                print(f"\n{strategy_names[strategy]}:")
                print(f"  平均总收益: {np.mean(returns):.2f}%")
                print(f"  中位数收益: {np.median(returns):.2f}%")
                print(f"  最佳: {np.max(returns):.2f}% | 最差: {np.min(returns):.2f}%")
                print(f"  正收益股票: {sum(1 for r in returns if r > 0)}/{len(returns)}")
                print(f"  平均年化: {np.mean(annual):.2f}%")
                print(f"  平均胜率: {np.mean(win_rates):.1f}%")
        
        print("\n" + "="*80)


if __name__ == '__main__':
    main()
