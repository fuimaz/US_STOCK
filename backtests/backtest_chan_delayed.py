"""
缠论策略回测 - 延迟确认版本（修复未来函数）
"""
import pandas as pd
import numpy as np
import os
from datetime import timedelta
from chan_theory_delayed import ChanTheoryDelayed


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


def backtest_with_delay(data, symbol, delay_days=1, initial_capital=100000):
    """
    使用延迟确认的回测
    
    Args:
        delay_days: 延迟确认天数（1或2）
    """
    if data is None or len(data) < 252:
        return None
    
    # 只使用近10年数据
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10*365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 100:
        return None
    
    # 使用延迟确认版本
    chan = ChanTheoryDelayed(k_type='day', delay_days=delay_days)
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
        'delay_days': delay_days,
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
    test_symbols = [
        '000001.SZ', '000002.SZ', '000333.SZ', '000858.SZ', '002304.SZ',
        '002415.SZ', '002594.SZ', '300750.SZ', '600036.SS', '600276.SS',
        '600519.SS', '601186.SS', '601318.SS', '601888.SS', '603288.SS'
    ]
    
    print("="*80)
    print("Chan Theory Backtest - Delayed Confirmation (Future Function Fixed)")
    print("="*80)
    
    results_delay1 = []
    results_delay2 = []
    
    for symbol in test_symbols:
        print(f"\nProcessing {symbol}...")
        data = load_stock_data(symbol, '20y')
        
        if data is None:
            continue
        
        # 延迟1天
        result1 = backtest_with_delay(data, symbol, delay_days=1)
        if result1:
            results_delay1.append(result1)
        
        # 延迟2天
        result2 = backtest_with_delay(data, symbol, delay_days=2)
        if result2:
            results_delay2.append(result2)
    
    # 汇总统计
    print("\n" + "="*80)
    print("Summary - Delay 1 Day")
    print("="*80)
    if results_delay1:
        returns = [r['total_return'] for r in results_delay1]
        print(f"Stocks tested: {len(results_delay1)}")
        print(f"Average total return: {np.mean(returns):.2f}%")
        print(f"Median return: {np.median(returns):.2f}%")
        print(f"Best: {np.max(returns):.2f}% | Worst: {np.min(returns):.2f}%")
        print(f"Positive: {sum(1 for r in returns if r > 0)}/{len(returns)}")
        print(f"Average annual: {np.mean([r['annualized_return'] for r in results_delay1]):.2f}%")
        print(f"Average win rate: {np.mean([r['win_rate'] for r in results_delay1]):.1f}%")
    
    print("\n" + "="*80)
    print("Summary - Delay 2 Days")
    print("="*80)
    if results_delay2:
        returns = [r['total_return'] for r in results_delay2]
        print(f"Stocks tested: {len(results_delay2)}")
        print(f"Average total return: {np.mean(returns):.2f}%")
        print(f"Median return: {np.median(returns):.2f}%")
        print(f"Best: {np.max(returns):.2f}% | Worst: {np.min(returns):.2f}%")
        print(f"Positive: {sum(1 for r in returns if r > 0)}/{len(returns)}")
        print(f"Average annual: {np.mean([r['annualized_return'] for r in results_delay2]):.2f}%")
        print(f"Average win rate: {np.mean([r['win_rate'] for r in results_delay2]):.1f}%")
    
    # 对比买入持有
    print("\n" + "="*80)
    print("Comparison with Buy & Hold")
    print("="*80)
    for symbol in test_symbols[:5]:  # 只显示前5只
        data = load_stock_data(symbol, '20y')
        if data is None:
            continue
        
        end_date = data.index[-1]
        start_date = end_date - timedelta(days=10*365)
        data_bh = data[data.index >= start_date]
        
        bh_return = (data_bh['Close'].iloc[-1] - data_bh['Close'].iloc[0]) / data_bh['Close'].iloc[0] * 100
        
        result1 = [r for r in results_delay1 if r['symbol'] == symbol]
        result2 = [r for r in results_delay2 if r['symbol'] == symbol]
        
        print(f"\n{symbol}:")
        print(f"  Buy & Hold: {bh_return:.2f}%")
        if result1:
            print(f"  Chan (delay 1d): {result1[0]['total_return']:.2f}% (excess: {result1[0]['total_return']-bh_return:+.2f}%)")
        if result2:
            print(f"  Chan (delay 2d): {result2[0]['total_return']:.2f}% (excess: {result2[0]['total_return']-bh_return:+.2f}%)")


if __name__ == '__main__':
    main()
