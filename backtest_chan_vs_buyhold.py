"""
缠论策略 vs 买入持有策略 对比
对比三种策略与原始涨幅：
1. 全部买卖点
2. 忽略一卖 ⭐
3. 只使用一买一卖
4. 买入持有（原始涨幅）
"""
import pandas as pd
import numpy as np
import os
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


def calc_buy_hold_return(data, years=10):
    """计算买入持有收益"""
    if data is None or len(data) < 252:
        return None
    
    # 使用近10年数据
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=years*365)
    data_period = data[data.index >= start_date]
    
    if len(data_period) < 100:
        return None
    
    start_price = data_period['Close'].iloc[0]
    end_price = data_period['Close'].iloc[-1]
    
    total_return = (end_price - start_price) / start_price * 100
    annual_return = ((end_price / start_price) ** (1/years) - 1) * 100
    
    # 计算最大回撤
    cumulative = (1 + data_period['Close'].pct_change()).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min() * 100
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'start_price': start_price,
        'end_price': end_price,
        'start_date': data_period.index[0].strftime('%Y-%m-%d'),
        'end_date': data_period.index[-1].strftime('%Y-%m-%d')
    }


def backtest_strategy(data, strategy_type='all', initial_capital=100000):
    """回测指定策略"""
    if data is None or len(data) < 252:
        return None
    
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10*365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 100:
        return None
    
    chan = ChanTheory(k_type='day')
    result = chan.analyze(data)
    
    # 筛选买卖点
    buy_points = []
    sell_points = []
    
    for bp in chan.buy_points:
        if bp['index'] not in data_backtest.index:
            continue
        if strategy_type == 'all' and bp['type'] in [1, 2]:
            buy_points.append(bp)
        elif strategy_type == 'no_first_sell' and bp['type'] in [1, 2]:
            buy_points.append(bp)
        elif strategy_type == 'only_first' and bp['type'] == 1:
            buy_points.append(bp)
    
    for sp in chan.sell_points:
        if sp['index'] not in data_backtest.index:
            continue
        if strategy_type == 'all' and sp['type'] in [1, 2]:
            sell_points.append(sp)
        elif strategy_type == 'no_first_sell' and sp['type'] == 2:  # 忽略一卖
            sell_points.append(sp)
        elif strategy_type == 'only_first' and sp['type'] == 1:
            sell_points.append(sp)
    
    # 回测
    capital = initial_capital
    position = 0
    
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
            
        elif signal['type'] == 'sell' and position > 0:
            proceeds = position * current_price * (1 - slippage) * (1 - commission)
            capital += proceeds
            position = 0
    
    final_value = capital + position * data_backtest['Close'].iloc[-1] * (1 - slippage) * (1 - commission)
    
    total_return = (final_value - initial_capital) / initial_capital * 100
    years = len(data_backtest) / 252
    annualized = ((final_value / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    
    return {
        'total_return': total_return,
        'annual_return': annualized,
        'trade_count': len([s for s in all_signals if s['type'] == 'sell']),
        'buy_count': len(buy_points),
        'sell_count': len(sell_points)
    }


def compare_strategies(symbol, data):
    """对比所有策略与买入持有"""
    results = {}
    
    # 买入持有
    bh = calc_buy_hold_return(data)
    if bh:
        results['buy_hold'] = bh
    
    # 策略1: 全部买卖点
    r1 = backtest_strategy(data, 'all')
    if r1:
        results['all'] = r1
    
    # 策略2: 忽略一卖
    r2 = backtest_strategy(data, 'no_first_sell')
    if r2:
        results['no_first_sell'] = r2
    
    # 策略3: 只使用一买一卖
    r3 = backtest_strategy(data, 'only_first')
    if r3:
        results['only_first'] = r3
    
    return results


def print_comparison_table(symbol, results):
    """打印对比表格"""
    if not results:
        return
    
    bh = results.get('buy_hold', {})
    all_s = results.get('all', {})
    no_fs = results.get('no_first_sell', {})
    only_f = results.get('only_first', {})
    
    bh_return = bh.get('total_return', 0)
    
    print(f"\n{'='*90}")
    print(f"股票: {symbol} | 数据区间: {bh.get('start_date', 'N/A')} ~ {bh.get('end_date', 'N/A')}")
    print(f"{'='*90}")
    print(f"买入持有: ${bh.get('start_price', 0):.2f} → ${bh.get('end_price', 0):.2f} | 收益: {bh_return:+.2f}% | 最大回撤: {bh.get('max_drawdown', 0):.2f}%")
    print('-'*90)
    print(f"{'策略':<20} {'总收益':>12} {'超额收益':>12} {'年化':>10} {'交易次数':>10} {'买/卖信号':>12}")
    print('-'*90)
    
    for name, label in [('all', '全部买卖点'), ('no_first_sell', '忽略一卖'), ('only_first', '只使用一买一卖')]:
        if name in results:
            r = results[name]
            excess = r['total_return'] - bh_return
            excess_str = f"{excess:+.2f}%"
            win = "[OK]" if excess > 0 else "[X]"
            print(f"{label:<18} {r['total_return']:>11.2f}% {excess_str:>12} {r['annual_return']:>10.2f}% {r['trade_count']:>10} {r['buy_count']}/{r['sell_count']:>8} {win}")
    
    # 找出最佳
    strategy_returns = [
        ('买入持有', bh_return),
        ('全部买卖点', all_s.get('total_return', -999) if all_s else -999),
        ('忽略一卖', no_fs.get('total_return', -999) if no_fs else -999),
        ('只使用一买一卖', only_f.get('total_return', -999) if only_f else -999)
    ]
    best = max(strategy_returns, key=lambda x: x[1])
    print(f"\n最佳: {best[0]} ({best[1]:+.2f}%)")


def main():
    test_symbols = [
        '000001.SZ', '000002.SZ', '000333.SZ', '000858.SZ', '002304.SZ',
        '002415.SZ', '002594.SZ', '300750.SZ', '600036.SS', '600276.SS',
        '600519.SS', '601186.SS', '601318.SS', '601888.SS', '603288.SS'
    ]
    
    print("="*90)
    print("缠论策略 vs 买入持有 对比测试")
    print("="*90)
    print("\n说明:")
    print("- 买入持有: 10年前买入，持有到现在")
    print("- 超额收益: 策略收益 - 买入持有收益")
    print("- [OK] 表示跑赢买入持有，[X] 表示跑输")
    
    all_results = []
    
    for symbol in test_symbols:
        data = load_stock_data(symbol, '20y')
        if data is None:
            continue
        
        results = compare_strategies(symbol, data)
        if results and 'buy_hold' in results:
            print_comparison_table(symbol, results)
            all_results.append({'symbol': symbol, 'results': results})
    
    # 汇总统计
    if all_results:
        print("\n" + "="*90)
        print("汇总统计")
        print("="*90)
        
        # 统计各策略跑赢/跑输情况
        buy_hold_returns = []
        all_excess = []
        no_fs_excess = []
        only_f_excess = []
        
        win_all = 0
        win_no_fs = 0
        win_only_f = 0
        
        for item in all_results:
            r = item['results']
            bh_return = r['buy_hold']['total_return']
            buy_hold_returns.append(bh_return)
            
            if 'all' in r:
                excess = r['all']['total_return'] - bh_return
                all_excess.append(excess)
                if excess > 0:
                    win_all += 1
            
            if 'no_first_sell' in r:
                excess = r['no_first_sell']['total_return'] - bh_return
                no_fs_excess.append(excess)
                if excess > 0:
                    win_no_fs += 1
            
            if 'only_first' in r:
                excess = r['only_first']['total_return'] - bh_return
                only_f_excess.append(excess)
                if excess > 0:
                    win_only_f += 1
        
        print(f"\n测试股票数: {len(all_results)}")
        print(f"买入持有平均收益: {np.mean(buy_hold_returns):.2f}%")
        print(f"买入持有中位数: {np.median(buy_hold_returns):.2f}%")
        print(f"买入持有最佳: {np.max(buy_hold_returns):.2f}%")
        print(f"买入持有最差: {np.min(buy_hold_returns):.2f}%")
        print()
        
        print("策略 vs 买入持有:")
        print(f"  全部买卖点: 跑赢 {win_all}/{len(all_results)} 只, 平均超额 {np.mean(all_excess):.2f}%")
        print(f"  忽略一卖:   跑赢 {win_no_fs}/{len(all_results)} 只, 平均超额 {np.mean(no_fs_excess):.2f}%")
        print(f"  只一买一卖: 跑赢 {win_only_f}/{len(all_results)} 只, 平均超额 {np.mean(only_f_excess):.2f}%")
        
        print("\n" + "="*90)


if __name__ == '__main__':
    main()
