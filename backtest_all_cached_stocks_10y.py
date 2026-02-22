"""
批量回测缓存中所有有10年数据的股票 - 缠论实时方案
"""
import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime, timedelta
from chan_theory_realtime import ChanTheoryRealtime
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


def get_cached_symbols():
    """获取所有缓存的股票代码"""
    cache_files = glob.glob('data_cache/*_20y_1d_forward.csv')
    symbols = []
    for f in cache_files:
        basename = os.path.basename(f)
        symbol = basename.split('_')[0]
        symbols.append(symbol)
    return sorted(list(set(symbols)))


def load_cached_data(symbol, period='20y'):
    """从缓存加载股票数据"""
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
    except Exception as e:
        print(f"  Error loading cache: {e}")
        return None


def backtest_chan_realtime(data, symbol, initial_capital=100000):
    """
    缠论实时方案回测 - 使用近10年数据
    """
    if data is None or len(data) < 252 * 5:  # 至少5年数据
        return None
    
    # 只使用近10年数据
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10*365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 252 * 2:  # 至少2年数据
        return None
    
    # 使用缠论分析
    chan = ChanTheoryRealtime(k_type='day')
    result = chan.analyze(data)
    
    # 获取回测区间内的买卖点
    buy_points = [bp for bp in chan.buy_points if bp['index'] in data_backtest.index and bp['type'] in [1, 2]]
    sell_points = [sp for sp in chan.sell_points if sp['index'] in data_backtest.index and sp['type'] in [1, 2]]
    
    # 回测交易
    capital = initial_capital
    position = 0
    trades = []
    
    # 合并信号
    all_signals = []
    for bp in buy_points:
        all_signals.append({'date': bp['index'], 'type': 'buy', 'price': bp['price'], 'bp_type': bp['type']})
    for sp in sell_points:
        all_signals.append({'date': sp['index'], 'type': 'sell', 'price': sp['price'], 'sp_type': sp['type']})
    
    all_signals.sort(key=lambda x: x['date'])
    
    # 交易费用
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
    final_price = data_backtest['Close'].iloc[-1]
    if position > 0:
        final_value = capital + position * final_price * (1 - slippage) * (1 - commission)
    else:
        final_value = capital
    
    # 计算收益
    total_return = (final_value - initial_capital) / initial_capital * 100
    years = len(data_backtest) / 252
    annualized = ((final_value / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # 计算买入持有收益
    first_price = data_backtest['Close'].iloc[0]
    buyhold_return = (final_price - first_price) / first_price * 100
    buyhold_annualized = ((final_price / first_price) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # 计算胜率
    profits = []
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    
    for i, buy in enumerate(buy_trades):
        if i < len(sell_trades):
            profit = (sell_trades[i]['value'] - buy['value']) / buy['value']
            profits.append(profit)
    
    win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100 if profits else 0
    
    # 计算最大回撤
    equity_curve = [initial_capital]
    for trade in trades:
        if trade['type'] == 'sell':
            equity_curve.append(trade['value'])
    
    max_drawdown = 0
    peak = initial_capital
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return {
        'symbol': symbol,
        'years': years,
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized,
        'buyhold_return': buyhold_return,
        'buyhold_annualized': buyhold_annualized,
        'excess_return': total_return - buyhold_return,
        'win_rate': win_rate,
        'trade_count': len(profits),
        'buy_count': len(buy_points),
        'sell_count': len(sell_points),
        'max_drawdown': max_drawdown
    }


def generate_summary_charts(df_results, output_dir='results/chan_10y_backtest'):
    """生成汇总图表"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 收益分布直方图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 策略收益分布
    ax = axes[0, 0]
    ax.hist(df_results['total_return'], bins=20, color='blue', alpha=0.6, edgecolor='black')
    ax.axvline(df_results['total_return'].mean(), color='red', linestyle='--', linewidth=2, label=f"Mean: {df_results['total_return'].mean():.1f}%")
    ax.set_xlabel('Strategy Return (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Strategy Returns (10Y)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 买入持有收益分布
    ax = axes[0, 1]
    ax.hist(df_results['buyhold_return'], bins=20, color='green', alpha=0.6, edgecolor='black')
    ax.axvline(df_results['buyhold_return'].mean(), color='red', linestyle='--', linewidth=2, label=f"Mean: {df_results['buyhold_return'].mean():.1f}%")
    ax.set_xlabel('Buy&Hold Return (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Buy&Hold Returns (10Y)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 超额收益分布
    ax = axes[1, 0]
    ax.hist(df_results['excess_return'], bins=20, color='orange', alpha=0.6, edgecolor='black')
    ax.axvline(df_results['excess_return'].mean(), color='red', linestyle='--', linewidth=2, label=f"Mean: {df_results['excess_return'].mean():.1f}%")
    ax.axvline(0, color='black', linestyle='-', linewidth=1)
    ax.set_xlabel('Excess Return (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Excess Returns (10Y)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 胜率分布
    ax = axes[1, 1]
    ax.hist(df_results['win_rate'], bins=20, color='purple', alpha=0.6, edgecolor='black')
    ax.axvline(df_results['win_rate'].mean(), color='red', linestyle='--', linewidth=2, label=f"Mean: {df_results['win_rate'].mean():.1f}%")
    ax.axvline(50, color='black', linestyle='-', linewidth=1)
    ax.set_xlabel('Win Rate (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Win Rates')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/summary_distributions.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 2. Top 20 收益排名图
    fig, ax = plt.subplots(figsize=(14, 10))
    top20 = df_results.nlargest(20, 'total_return')
    
    x = range(len(top20))
    width = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x], top20['total_return'], width, label='Strategy', color='blue', alpha=0.7)
    bars2 = ax.bar([i + width/2 for i in x], top20['buyhold_return'], width, label='Buy&Hold', color='green', alpha=0.7)
    
    ax.set_xlabel('Stock')
    ax.set_ylabel('Return (%)')
    ax.set_title('Top 20 Stocks by Strategy Return (10Y)')
    ax.set_xticks(x)
    ax.set_xticklabels(top20['symbol'], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/top20_returns.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 3. 散点图：策略收益 vs 买入持有收益
    fig, ax = plt.subplots(figsize=(10, 10))
    
    ax.scatter(df_results['buyhold_return'], df_results['total_return'], alpha=0.6, s=50)
    
    # 添加对角线
    min_val = min(df_results['buyhold_return'].min(), df_results['total_return'].min())
    max_val = max(df_results['buyhold_return'].max(), df_results['total_return'].max())
    ax.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='y=x')
    
    # 标注表现最好的
    top5 = df_results.nlargest(5, 'excess_return')
    for _, row in top5.iterrows():
        ax.annotate(row['symbol'], (row['buyhold_return'], row['total_return']), 
                   xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    ax.set_xlabel('Buy&Hold Return (%)')
    ax.set_ylabel('Strategy Return (%)')
    ax.set_title('Strategy vs Buy&Hold Returns (10Y)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/scatter_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()


def main():
    print("=" * 100)
    print("批量回测缓存中所有股票 - 缠论实时方案（近10年）")
    print("=" * 100)
    print()
    
    # 获取所有缓存的股票代码
    symbols = get_cached_symbols()
    print(f"发现 {len(symbols)} 只有缓存数据的股票")
    print()
    
    results = []
    success_count = 0
    fail_count = 0
    
    start_time = datetime.now()
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Processing: {symbol}")
        
        # 加载数据
        data = load_cached_data(symbol, period='20y')
        if data is None:
            print(f"  [FAIL] No data available")
            fail_count += 1
            continue
        
        # 检查数据是否足够10年
        if len(data) < 252 * 10:
            print(f"  [SKIP] Data only {len(data)/252:.1f} years, need at least 10 years")
            fail_count += 1
            continue
        
        # 回测
        result = backtest_chan_realtime(data, symbol)
        if result is None:
            print(f"  [FAIL] Backtest failed")
            fail_count += 1
            continue
        
        print(f"  [OK] Strategy: {result['total_return']:.1f}% | Buy&Hold: {result['buyhold_return']:.1f}% | Excess: {result['excess_return']:+.1f}% | WinRate: {result['win_rate']:.1f}% | Trades: {result['trade_count']}")
        
        results.append(result)
        success_count += 1
    
    elapsed = datetime.now() - start_time
    
    # 汇总统计
    print()
    print("=" * 100)
    print(f"回测完成 - 耗时: {elapsed.total_seconds():.1f}秒")
    print("=" * 100)
    print()
    
    if results:
        df_results = pd.DataFrame(results)
        
        # 按收益排序
        df_results = df_results.sort_values('total_return', ascending=False)
        
        # 保存详细结果
        output_dir = 'results/chan_10y_backtest'
        os.makedirs(output_dir, exist_ok=True)
        
        df_results.to_csv(f'{output_dir}/detailed_results.csv', index=False, encoding='utf-8-sig')
        
        # 显示前20名
        print("Top 20 Stocks by Strategy Return:")
        print(f"{'Rank':<4} {'Symbol':<12} {'Strategy':<10} {'Buy&Hold':<10} {'Excess':<10} {'Annual':<8} {'WinRate':<8} {'Trades':<8}")
        print("-" * 80)
        
        for rank, (_, row) in enumerate(df_results.head(20).iterrows(), 1):
            print(f"{rank:<4} {row['symbol']:<12} {row['total_return']:>8.1f}% {row['buyhold_return']:>8.1f}% "
                  f"{row['excess_return']:>+8.1f}% {row['annualized_return']:>6.1f}% {row['win_rate']:>6.1f}% {int(row['trade_count']):>6}")
        
        print()
        
        # 显示后10名
        print("Bottom 10 Stocks by Strategy Return:")
        print(f"{'Rank':<4} {'Symbol':<12} {'Strategy':<10} {'Buy&Hold':<10} {'Excess':<10} {'Annual':<8} {'WinRate':<8} {'Trades':<8}")
        print("-" * 80)
        
        for rank, (_, row) in enumerate(df_results.tail(10).iterrows(), 1):
            print(f"{rank:<4} {row['symbol']:<12} {row['total_return']:>8.1f}% {row['buyhold_return']:>8.1f}% "
                  f"{row['excess_return']:>+8.1f}% {row['annualized_return']:>6.1f}% {row['win_rate']:>6.1f}% {int(row['trade_count']):>6}")
        
        print()
        print("=" * 100)
        print("Overall Statistics:")
        print("=" * 100)
        print(f"  Stocks tested: {len(results)}")
        print(f"  Avg years of data: {df_results['years'].mean():.1f}")
        print()
        print(f"  Strategy Return:")
        print(f"    Average: {df_results['total_return'].mean():.2f}%")
        print(f"    Median: {df_results['total_return'].median():.2f}%")
        print(f"    Best: {df_results['total_return'].max():.2f}% ({df_results.loc[df_results['total_return'].idxmax(), 'symbol']})")
        print(f"    Worst: {df_results['total_return'].min():.2f}% ({df_results.loc[df_results['total_return'].idxmin(), 'symbol']})")
        print(f"    Std: {df_results['total_return'].std():.2f}%")
        print()
        print(f"  Buy&Hold Return:")
        print(f"    Average: {df_results['buyhold_return'].mean():.2f}%")
        print(f"    Median: {df_results['buyhold_return'].median():.2f}%")
        print(f"    Best: {df_results['buyhold_return'].max():.2f}% ({df_results.loc[df_results['buyhold_return'].idxmax(), 'symbol']})")
        print(f"    Worst: {df_results['buyhold_return'].min():.2f}% ({df_results.loc[df_results['buyhold_return'].idxmin(), 'symbol']})")
        print()
        print(f"  Excess Return:")
        print(f"    Average: {df_results['excess_return'].mean():+.2f}%")
        print(f"    Median: {df_results['excess_return'].median():+.2f}%")
        print(f"    Best: {df_results['excess_return'].max():+.2f}% ({df_results.loc[df_results['excess_return'].idxmax(), 'symbol']})")
        print(f"    Worst: {df_results['excess_return'].min():+.2f}% ({df_results.loc[df_results['excess_return'].idxmin(), 'symbol']})")
        print(f"    Positive: {sum(df_results['excess_return'] > 0)}/{len(df_results)} ({sum(df_results['excess_return'] > 0)/len(df_results)*100:.1f}%)")
        print()
        print(f"  Win Rate:")
        print(f"    Average: {df_results['win_rate'].mean():.2f}%")
        print(f"    >50%: {sum(df_results['win_rate'] > 50)}/{len(df_results)} ({sum(df_results['win_rate'] > 50)/len(df_results)*100:.1f}%)")
        print()
        print(f"  Trading Activity:")
        print(f"    Avg trades per stock: {df_results['trade_count'].mean():.1f}")
        print(f"    Avg buy signals: {df_results['buy_count'].mean():.1f}")
        print(f"    Avg sell signals: {df_results['sell_count'].mean():.1f}")
        print()
        print(f"  Risk Metrics:")
        print(f"    Avg max drawdown: {df_results['max_drawdown'].mean():.2f}%")
        print()
        
        # 生成汇总图表
        print("Generating summary charts...")
        generate_summary_charts(df_results, output_dir)
        print(f"Charts saved to: {output_dir}/")
        print()
    
    print(f"Success: {success_count} | Failed/Skipped: {fail_count}")
    print("=" * 100)


if __name__ == '__main__':
    main()
