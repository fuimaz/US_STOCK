"""
A股最近1年热门股票缠论实时方案回测 - 只使用第一类买卖点
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from chan_theory_realtime import ChanTheoryRealtime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# 最近1年A股热门股票
HOT_STOCKS_1Y = [
    ('002230.SZ', '科大讯飞', 'AI'),
    ('000977.SZ', '浪潮信息', 'AI服务器'),
    ('002475.SZ', '立讯精密', 'AI硬件'),
    ('002050.SZ', '三花智控', '机器人'),
    ('300124.SZ', '汇川技术', '机器人'),
    ('600941.SS', '中国移动', '算力'),
    ('300750.SZ', '宁德时代', '新能源'),
    ('002594.SZ', '比亚迪', '新能源'),
    ('601012.SS', '隆基绿能', '光伏'),
    ('600036.SS', '招商银行', '银行'),
    ('000001.SZ', '平安银行', '银行'),
    ('601398.SS', '工商银行', '银行'),
    ('600519.SS', '贵州茅台', '白酒'),
    ('000858.SZ', '五粮液', '白酒'),
    ('000333.SZ', '美的集团', '家电'),
    ('600276.SS', '恒瑞医药', '医药'),
    ('300760.SZ', '迈瑞医疗', '医药'),
    ('601088.SS', '中国神华', '煤炭'),
    ('600900.SS', '长江电力', '电力'),
    ('601899.SS', '紫金矿业', '有色'),
]


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


def backtest_chan_type1_only(data, symbol, initial_capital=100000):
    """
    缠论实时方案回测 - 只使用第一类买卖点
    """
    if data is None or len(data) < 60:
        return None
    
    # 只使用近1年数据
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 30:
        return None
    
    # 使用缠论分析 - 实时近似方案
    chan = ChanTheoryRealtime(k_type='day')
    result = chan.analyze(data)
    
    # 只获取第一类买卖点（type=1）
    buy_points = [bp for bp in chan.buy_points if bp['index'] in data_backtest.index and bp['type'] == 1]
    sell_points = [sp for sp in chan.sell_points if sp['index'] in data_backtest.index and sp['type'] == 1]
    
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
    commission = 0.001  # 0.1% 佣金
    slippage = 0.0005   # 0.05% 滑点
    
    for signal in all_signals:
        current_price = signal['price']
        
        if signal['type'] == 'buy' and position == 0:
            # 买入
            shares = capital / (current_price * (1 + slippage))
            cost = shares * current_price * (1 + slippage) * (1 + commission)
            capital -= cost
            position = shares
            trades.append({
                'type': 'buy', 
                'date': signal['date'], 
                'price': current_price, 
                'value': cost,
                'bp_type': signal.get('bp_type', 1)
            })
            
        elif signal['type'] == 'sell' and position > 0:
            # 卖出
            proceeds = position * current_price * (1 - slippage) * (1 - commission)
            capital += proceeds
            trades.append({
                'type': 'sell', 
                'date': signal['date'], 
                'price': current_price, 
                'value': proceeds,
                'sp_type': signal.get('sp_type', 1)
            })
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
    avg_profit = np.mean(profits) * 100 if profits else 0
    max_profit = max(profits) * 100 if profits else 0
    max_loss = min(profits) * 100 if profits else 0
    
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
        'avg_profit': avg_profit,
        'max_profit': max_profit,
        'max_loss': max_loss,
        'max_drawdown': max_drawdown,
        'trades': trades,
        'data': data_backtest,
        'buy_points': buy_points,
        'sell_points': sell_points
    }


def generate_charts(result, symbol, name, sector, output_dir='results/hot_stocks_1y_type1'):
    """生成K线图表"""
    os.makedirs(output_dir, exist_ok=True)
    
    data = result['data']
    buy_points = result['buy_points']
    sell_points = result['sell_points']
    
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    # 主图：K线
    ax1 = axes[0]
    
    # 绘制K线
    from mplfinance.original_flavor import candlestick_ohlc
    import matplotlib.dates as mdates
    
    # 准备数据
    df_plot = data.reset_index()
    date_col = 'datetime' if 'datetime' in df_plot.columns else df_plot.columns[0]
    df_plot['Date'] = pd.to_datetime(df_plot[date_col])
    df_plot['Date'] = df_plot['Date'].map(mdates.date2num)
    
    ohlc = df_plot[['Date', 'Open', 'High', 'Low', 'Close']].values
    candlestick_ohlc(ax1, ohlc, width=0.6, colorup='red', colordown='green', alpha=0.8)
    
    # 标记买卖点（只标记第一类）
    for bp in buy_points:
        ax1.scatter(mdates.date2num(bp['index']), bp['price'], marker='^', s=200, 
                   color='blue', edgecolors='black', linewidth=2, zorder=5, label='First Buy')
        ax1.annotate('B1', (mdates.date2num(bp['index']), bp['price']), 
                    xytext=(5, 10), textcoords='offset points', fontsize=10, color='blue', fontweight='bold')
    
    for sp in sell_points:
        ax1.scatter(mdates.date2num(sp['index']), sp['price'], marker='v', s=200,
                   color='purple', edgecolors='black', linewidth=2, zorder=5, label='First Sell')
        ax1.annotate('S1', (mdates.date2num(sp['index']), sp['price']), 
                    xytext=(5, -15), textcoords='offset points', fontsize=10, color='purple', fontweight='bold')
    
    ax1.set_title(f'{symbol} {name} ({sector}) - Chan Theory Type 1 Only (Last 1 Year)\n'
                  f'Strategy: {result["total_return"]:.1f}% | Buy&Hold: {result["buyhold_return"]:.1f}% | Excess: {result["excess_return"]:+.1f}%',
                  fontsize=14)
    ax1.set_ylabel('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # 添加图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='^', color='w', markerfacecolor='blue', markeredgecolor='black', markersize=12, label='First Buy (Type 1)'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='purple', markeredgecolor='black', markersize=12, label='First Sell (Type 1)')
    ]
    ax1.legend(handles=legend_elements, loc='upper left')
    
    # 成交量
    ax2 = axes[1]
    colors = ['red' if close >= open else 'green' for open, close in zip(data['Open'], data['Close'])]
    ax2.bar(df_plot['Date'], data['Volume'], color=colors, alpha=0.6, width=0.6)
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{symbol}_type1_signals.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    return f'{output_dir}/{symbol}_type1_signals.png'


def main():
    print("=" * 100)
    print("A股热门股票缠论实时方案回测 - 仅第一类买卖点 (近1年)")
    print("=" * 100)
    print()
    
    results = []
    success_count = 0
    fail_count = 0
    
    for symbol, name, sector in HOT_STOCKS_1Y:
        print(f"Processing: {name} ({symbol}) - {sector}")
        print("-" * 100)
        
        # 加载数据
        data = load_cached_data(symbol, period='20y')
        if data is None:
            print(f"  [FAIL] No cached data available\n")
            fail_count += 1
            continue
        
        print(f"  Data points: {len(data)}")
        print(f"  Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
        
        # 回测
        result = backtest_chan_type1_only(data, symbol)
        if result is None:
            print(f"  [FAIL] Backtest failed\n")
            fail_count += 1
            continue
        
        print(f"  Last 1Y data: {len(result['data'])} bars")
        print(f"  First Buy signals: {result['buy_count']}")
        print(f"  First Sell signals: {result['sell_count']}")
        print(f"  Trades: {result['trade_count']}")
        print(f"  Win rate: {result['win_rate']:.1f}%")
        print(f"  Strategy return: {result['total_return']:.2f}% (annual {result['annualized_return']:.2f}%)")
        print(f"  Buy&Hold return: {result['buyhold_return']:.2f}% (annual {result['buyhold_annualized']:.2f}%)")
        print(f"  Excess return: {result['excess_return']:+.2f}%")
        print(f"  Max drawdown: {result['max_drawdown']:.2f}%")
        print(f"  Avg profit: {result['avg_profit']:+.2f}%")
        
        # 生成图表
        chart_path = generate_charts(result, symbol, name, sector)
        print(f"  Chart: {chart_path}")
        
        results.append({
            'symbol': symbol,
            'name': name,
            'sector': sector,
            'total_return': result['total_return'],
            'annualized_return': result['annualized_return'],
            'buyhold_return': result['buyhold_return'],
            'excess_return': result['excess_return'],
            'win_rate': result['win_rate'],
            'trade_count': result['trade_count'],
            'max_drawdown': result['max_drawdown'],
            'avg_profit': result['avg_profit'],
            'chart': chart_path
        })
        
        success_count += 1
        print(f"  [OK] Done\n")
    
    # 汇总统计
    print("=" * 100)
    print("Backtest Summary - Type 1 Only")
    print("=" * 100)
    print()
    
    if results:
        df_results = pd.DataFrame(results)
        
        # 按收益排序
        df_results = df_results.sort_values('total_return', ascending=False)
        
        print(f"{'Rank':<4} {'Symbol':<12} {'Name':<10} {'Sector':<10} {'Strategy':<10} {'Buy&Hold':<10} {'Excess':<10} {'WinRate':<8} {'Trades':<8}")
        print("-" * 100)
        
        rank = 1
        for _, row in df_results.iterrows():
            print(f"{rank:<4} {row['symbol']:<12} {row['name']:<10} {row['sector']:<10} "
                  f"{row['total_return']:>8.1f}% {row['buyhold_return']:>8.1f}% "
                  f"{row['excess_return']:>+8.1f}% {row['win_rate']:>6.1f}% {int(row['trade_count']):>6}")
            rank += 1
        
        print("-" * 100)
        print()
        
        # 统计指标
        print("Overall Statistics:")
        print(f"  Stocks tested: {len(results)}")
        print(f"  Avg strategy return: {df_results['total_return'].mean():.2f}%")
        print(f"  Avg buy&hold return: {df_results['buyhold_return'].mean():.2f}%")
        print(f"  Avg excess return: {df_results['excess_return'].mean():+.2f}%")
        print(f"  Win rate >50%: {sum(df_results['win_rate'] > 50)}/{len(results)}")
        print(f"  Positive excess: {sum(df_results['excess_return'] > 0)}/{len(results)}")
        print(f"  Avg trades: {df_results['trade_count'].mean():.1f}")
        print(f"  Avg max drawdown: {df_results['max_drawdown'].mean():.2f}%")
        print()
        
        # 与全部买卖点对比
        print("Comparison: Type 1 Only vs All Types")
        print("-" * 100)
        
        # 加载之前的全部买卖点结果
        try:
            df_all = pd.read_csv('results/hot_stocks_1y_backtest.csv')
            df_compare = df_results.merge(df_all[['symbol', 'total_return', 'trade_count']], 
                                         on='symbol', suffixes=('_type1', '_all'))
            
            print(f"{'Symbol':<12} {'Type1 Return':<12} {'All Return':<12} {'Type1 Trades':<12} {'All Trades':<12}")
            print("-" * 60)
            for _, row in df_compare.iterrows():
                print(f"{row['symbol']:<12} {row['total_return_type1']:>10.1f}% {row['total_return_all']:>10.1f}% "
                      f"{int(row['trade_count_type1']):>10} {int(row['trade_count_all']):>10}")
            
            print("-" * 60)
            print(f"{'Average':<12} {df_compare['total_return_type1'].mean():>10.1f}% {df_compare['total_return_all'].mean():>10.1f}% "
                  f"{df_compare['trade_count_type1'].mean():>10.1f} {df_compare['trade_count_all'].mean():>10.1f}")
            print()
        except:
            print("  Could not load comparison data")
        
        # 保存结果
        output_file = 'results/hot_stocks_1y_type1_backtest.csv'
        os.makedirs('results', exist_ok=True)
        df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Results saved: {output_file}")
        print()
    
    print(f"[OK]: {success_count} | [FAIL]: {fail_count}")
    print("=" * 100)


if __name__ == '__main__':
    main()
