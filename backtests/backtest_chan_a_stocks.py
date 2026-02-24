"""
缠论策略回测 - A股20年数据
测试多只A股股票，统计整体表现
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from chan_theory import ChanTheory

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


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
        elif 'Date' in data.columns:
            data['Date'] = pd.to_datetime(data['Date'])
            data = data.set_index('Date')
        
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [c for c in required_cols if c in data.columns]
        data = data[available_cols].copy()
        data = data.dropna()
        
        return data
    except Exception as e:
        print(f"  Error loading {symbol}: {e}")
        return None


def backtest_chan_strategy(data, symbol, initial_capital=100000):
    """
    缠论策略回测
    
    策略：
    - 买入：出现第一类买点或第二类买点时买入
    - 卖出：出现第一类卖点或第二类卖点时卖出
    - 仓位：全仓买入/卖出
    """
    if data is None or len(data) < 252:  # 至少1年数据
        return None
    
    # 只使用近10年数据回测（避免数据过多）
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10*365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 100:
        return None
    
    # 运行缠论分析（使用完整数据以获得更准确的结构识别）
    chan = ChanTheory(k_type='day')
    result = chan.analyze(data)
    
    # 获取买卖点
    buy_points = [bp for bp in chan.buy_points if bp['index'] in data_backtest.index and bp['type'] in [1, 2]]
    sell_points = [sp for sp in chan.sell_points if sp['index'] in data_backtest.index and sp['type'] in [1, 2]]
    
    # 回测
    capital = initial_capital
    position = 0
    trades = []
    equity_curve = []
    
    # 合并买卖点并按时间排序
    all_signals = []
    for bp in buy_points:
        all_signals.append({'date': bp['index'], 'type': 'buy', 'price': bp['price'], 'bp_type': bp['type']})
    for sp in sell_points:
        all_signals.append({'date': sp['index'], 'type': 'sell', 'price': sp['price'], 'sp_type': sp['type']})
    
    all_signals.sort(key=lambda x: x['date'])
    
    # 执行交易
    commission = 0.001  # 0.1%手续费
    slippage = 0.0005   # 0.05%滑点
    
    for signal in all_signals:
        current_price = signal['price']
        
        if signal['type'] == 'buy' and position == 0:
            # 买入
            shares = capital / (current_price * (1 + slippage))
            cost = shares * current_price * (1 + slippage) * (1 + commission)
            capital -= cost
            position = shares
            
            trades.append({
                'date': signal['date'],
                'type': 'buy',
                'price': current_price,
                'bp_type': signal.get('bp_type', 0),
                'shares': shares,
                'cost': cost
            })
            
        elif signal['type'] == 'sell' and position > 0:
            # 卖出
            proceeds = position * current_price * (1 - slippage) * (1 - commission)
            capital += proceeds
            
            trades.append({
                'date': signal['date'],
                'type': 'sell',
                'price': current_price,
                'sp_type': signal.get('sp_type', 0),
                'shares': position,
                'proceeds': proceeds
            })
            
            position = 0
    
    # 计算每日资金曲线
    for date, row in data_backtest.iterrows():
        current_value = capital + position * row['Close']
        equity_curve.append({'date': date, 'equity': current_value})
    
    # 最后一天平仓
    final_value = capital + position * data_backtest['Close'].iloc[-1] * (1 - slippage) * (1 - commission)
    
    # 计算收益指标
    equity_df = pd.DataFrame(equity_curve).set_index('date')
    total_return = (final_value - initial_capital) / initial_capital * 100
    
    years = len(data_backtest) / 252
    annualized_return = ((final_value / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # 最大回撤
    equity = equity_df['equity']
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100
    max_drawdown = drawdown.min()
    
    # 波动率和夏普比率
    returns = equity.pct_change().dropna()
    volatility = returns.std() * np.sqrt(252) * 100
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
    
    # 胜率
    win_count = 0
    loss_count = 0
    trade_pairs = []
    
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    
    for i, buy in enumerate(buy_trades):
        if i < len(sell_trades):
            sell = sell_trades[i]
            profit = (sell['proceeds'] - buy['cost']) / buy['cost']
            trade_pairs.append(profit)
            if profit > 0:
                win_count += 1
            else:
                loss_count += 1
    
    win_rate = win_count / len(trade_pairs) * 100 if trade_pairs else 0
    
    return {
        'symbol': symbol,
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'max_drawdown': max_drawdown,
        'volatility': volatility,
        'sharpe_ratio': sharpe,
        'win_rate': win_rate,
        'total_trades': len(trades),
        'buy_count': len(buy_points),
        'sell_count': len(sell_points),
        'trade_count': len(trade_pairs),
        'win_count': win_count,
        'loss_count': loss_count,
        'data_points': len(data_backtest),
        'date_range': f"{data_backtest.index[0].strftime('%Y-%m-%d')} to {data_backtest.index[-1].strftime('%Y-%m-%d')}",
        'equity_curve': equity_df,
        'trades': trades,
        'buy_points': buy_points,
        'sell_points': sell_points
    }


def print_results(result):
    """打印回测结果"""
    if result is None:
        return
    
    print("\n" + "="*70)
    print(f"回测结果 - {result['symbol']}")
    print("="*70)
    print(f"数据区间: {result['date_range']}")
    print(f"数据点数: {result['data_points']}")
    print(f"初始资金: ${result['initial_capital']:,.2f}")
    print(f"最终资金: ${result['final_value']:,.2f}")
    print(f"总收益率: {result['total_return']:.2f}%")
    print(f"年化收益率: {result['annualized_return']:.2f}%")
    print(f"最大回撤: {result['max_drawdown']:.2f}%")
    print(f"波动率: {result['volatility']:.2f}%")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"交易次数: {result['trade_count']} (胜{result['win_count']}/负{result['loss_count']})")
    print(f"胜率: {result['win_rate']:.2f}%")
    print(f"买卖点数: 买{result['buy_count']}/卖{result['sell_count']}")
    print("="*70)


def plot_result(result, output_dir='results/chan_backtest'):
    """绘制回测图表"""
    os.makedirs(output_dir, exist_ok=True)
    
    symbol = result['symbol']
    equity_df = result['equity_curve']
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle(f'{symbol} - Chan Theory Backtest', fontsize=16, fontweight='bold')
    
    # 1. 资金曲线
    ax1 = axes[0]
    ax1.plot(equity_df.index, equity_df['equity'], linewidth=2, color='blue', label='Portfolio')
    ax1.axhline(y=result['initial_capital'], color='gray', linestyle='--', alpha=0.5)
    ax1.set_ylabel('Value ($)')
    ax1.set_title(f"Return: {result['total_return']:.2f}% | Annual: {result['annualized_return']:.2f}%")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 回撤
    ax2 = axes[1]
    equity = equity_df['equity']
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100
    ax2.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3)
    ax2.set_ylabel('Drawdown (%)')
    ax2.set_title(f"Max Drawdown: {result['max_drawdown']:.2f}%")
    ax2.grid(True, alpha=0.3)
    
    # 3. 交易信号
    ax3 = axes[2]
    ax3.plot(equity_df.index, equity, linewidth=1, color='gray', alpha=0.5)
    
    for bp in result['buy_points']:
        color = 'red' if bp['type'] == 1 else 'orange'
        ax3.scatter(bp['date'], bp['price'], color=color, marker='^', s=100, zorder=5)
    
    for sp in result['sell_points']:
        color = 'green' if sp['type'] == 1 else 'cyan'
        ax3.scatter(sp['date'], sp['price'], color=color, marker='v', s=100, zorder=5)
    
    ax3.set_ylabel('Price')
    ax3.set_xlabel('Date')
    ax3.set_title(f"Trades: {result['trade_count']} | Win Rate: {result['win_rate']:.1f}%")
    ax3.grid(True, alpha=0.3)
    
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    plt.savefig(f'{output_dir}/{symbol}_backtest.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Chart saved: {output_dir}/{symbol}_backtest.png")


def main():
    """主函数"""
    # A股测试列表
    test_symbols = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '000333.SZ',  # 美的集团
        '000858.SZ',  # 五粮液
        '002304.SZ',  # 洋河股份
        '002415.SZ',  # 海康威视
        '002594.SZ',  # 比亚迪
        '300750.SZ',  # 宁德时代
        '600036.SS',  # 招商银行
        '600276.SS',  # 恒瑞医药
        '600519.SS',  # 贵州茅台
        '601186.SS',  # 中国铁建
        '601318.SS',  # 中国平安
        '601888.SS',  # 中国中免
        '603288.SS',  # 海天味业
    ]
    
    print("="*70)
    print("Chan Theory Strategy Backtest - A Shares (10y)")
    print("="*70)
    
    results = []
    
    for symbol in test_symbols:
        print(f"\nProcessing {symbol}...")
        data = load_stock_data(symbol, '20y')
        
        if data is None:
            print(f"  Data not found")
            continue
        
        print(f"  Data loaded: {len(data)} rows")
        
        result = backtest_chan_strategy(data, symbol)
        
        if result:
            print_results(result)
            plot_result(result)
            results.append(result)
        else:
            print(f"  Backtest failed")
    
    # 汇总统计
    if results:
        print("\n" + "="*70)
        print("Summary Statistics")
        print("="*70)
        
        returns = [r['total_return'] for r in results]
        annual = [r['annualized_return'] for r in results]
        max_dd = [r['max_drawdown'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        sharpes = [r['sharpe_ratio'] for r in results]
        
        print(f"Stocks tested: {len(results)}")
        print(f"Average total return: {np.mean(returns):.2f}%")
        print(f"Median total return: {np.median(returns):.2f}%")
        print(f"Best: {np.max(returns):.2f}% | Worst: {np.min(returns):.2f}%")
        print(f"Positive return: {sum(1 for r in returns if r > 0)}/{len(results)} ({sum(1 for r in returns if r > 0)/len(results)*100:.1f}%)")
        print()
        print(f"Average annual return: {np.mean(annual):.2f}%")
        print(f"Average max drawdown: {np.mean(max_dd):.2f}%")
        print(f"Average win rate: {np.mean(win_rates):.2f}%")
        print(f"Average Sharpe: {np.mean(sharpes):.2f}")
        
        # 排序
        sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        print("\nTop 5:")
        for i, r in enumerate(sorted_results[:5], 1):
            print(f"  {i}. {r['symbol']}: {r['total_return']:.2f}% (Annual: {r['annualized_return']:.2f}%)")
        
        print("\nBottom 5:")
        for i, r in enumerate(sorted_results[-5:], 1):
            print(f"  {i}. {r['symbol']}: {r['total_return']:.2f}% (Annual: {r['annualized_return']:.2f}%)")
        
        print("="*70)
    
    print("\nBacktest completed!")


if __name__ == '__main__':
    main()
