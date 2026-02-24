"""
缠论策略回测 - 实时近似版本（方案3）
当天收盘时判断疑似分型，无延迟，无未来函数
"""
import pandas as pd
import numpy as np
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indicators.chan.chan_theory_realtime import ChanTheoryRealtime


def discover_cached_a_share_symbols(period='20y'):
    """从 data_cache 自动发现已缓存的 A 股代码。"""
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


def backtest_realtime(data, symbol, initial_capital=100000):
    """
    实时近似版本回测
    """
    if data is None or len(data) < 252:
        return None
    
    # 只使用近10年数据
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10*365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 100:
        return None
    
    # 使用实时近似版本
    chan = ChanTheoryRealtime(k_type='day')
    result = chan.analyze(data)
    
    # 获取回测区间内的买卖点
    buy_points = [bp for bp in chan.buy_points if bp['index'] in data_backtest.index]
    sell_points = [sp for sp in chan.sell_points if sp['index'] in data_backtest.index]
    
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
    
    final_value = capital + position * data_backtest['Close'].iloc[-1] * (1 - slippage) * (1 - commission)
    
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
        'strategy': 'realtime',
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized,
        'win_rate': win_rate,
        'trade_count': len(profits),
        'buy_count': len(buy_points),
        'sell_count': len(sell_points)
    }


def main():
    test_symbols = discover_cached_a_share_symbols(period='20y')
    
    print("="*80)
    print("Chan Theory Backtest - Realtime Approximation (Scheme 3)")
    print("="*80)
    print("\n使用疑似分型实时判断，当天收盘即可交易")
    print("无延迟，无未来函数，但有一定误判率\n")
    
    print(f"Detected cached A-share symbols: {len(test_symbols)}")
    if not test_symbols:
        print("No cached A-share data found under data_cache/*_20y_1d_forward.csv")
        return

    results = []
    
    for symbol in test_symbols:
        print(f"Processing {symbol}...")
        data = load_stock_data(symbol, '20y')
        
        if data is None:
            continue
        
        result = backtest_realtime(data, symbol)
        if result:
            results.append(result)
    
    # 汇总统计
    print("\n" + "="*80)
    print("Summary - Realtime Approximation")
    print("="*80)
    if results:
        returns = [r['total_return'] for r in results]
        print(f"Stocks tested: {len(results)}")
        print(f"Average total return: {np.mean(returns):.2f}%")
        print(f"Median return: {np.median(returns):.2f}%")
        print(f"Best: {np.max(returns):.2f}% | Worst: {np.min(returns):.2f}%")
        print(f"Positive: {sum(1 for r in returns if r > 0)}/{len(returns)}")
        print(f"Average annual: {np.mean([r['annualized_return'] for r in results]):.2f}%")
        print(f"Average win rate: {np.mean([r['win_rate'] for r in results]):.1f}%")
    
    # 对比其他方案
    print("\n" + "="*80)
    print("Comparison with Other Schemes")
    print("="*80)
    print("\nScheme 1: Delay 1 Day")
    print("  Average return: ~348% | Annual: ~15%")
    print("\nScheme 2: Delay 2 Days")
    print("  Average return: ~195% | Annual: ~11%")
    print("\nScheme 3: Realtime (current)")
    if results:
        print(f"  Average return: ~{np.mean(returns):.0f}% | Annual: ~{np.mean([r['annualized_return'] for r in results]):.0f}%")
    
    # 详细对比前5只股票
    print("\n" + "="*80)
    print("Detailed Comparison (Top 5 Stocks)")
    print("="*80)
    for symbol in test_symbols[:5]:
        data = load_stock_data(symbol, '20y')
        if data is None:
            continue
        
        end_date = data.index[-1]
        start_date = end_date - timedelta(days=10*365)
        data_bh = data[data.index >= start_date]
        
        bh_return = (data_bh['Close'].iloc[-1] - data_bh['Close'].iloc[0]) / data_bh['Close'].iloc[0] * 100
        
        result = [r for r in results if r['symbol'] == symbol]
        
        print(f"\n{symbol}:")
        print(f"  Buy & Hold: {bh_return:.2f}%")
        if result:
            print(f"  Realtime: {result[0]['total_return']:.2f}% (excess: {result[0]['total_return']-bh_return:+.2f}%)")

    if results:
        output_dir = 'results/chan_backtest_realtime'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'backtest_realtime_summary.csv')
        pd.DataFrame(results).to_csv(output_file, index=False, encoding='utf-8-sig')
        print("\n" + "="*80)
        print(f"Results saved: {output_file}")


if __name__ == '__main__':
    main()
