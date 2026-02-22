"""
实时近似方案 - 买卖点可视化
生成带有缠论买卖点标记的K线图
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from chan_theory_realtime import ChanTheoryRealtime
import os

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
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        data = data.dropna()
        return data
    except Exception as e:
        print(f"Error loading {symbol}: {e}")
        return None


def plot_candlestick_with_signals(data, symbol, output_dir='results/chan_realtime_signals'):
    """
    绘制K线图并标记实时近似方案的买卖点
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 运行实时近似缠论分析
    chan = ChanTheoryRealtime(k_type='day')
    result = chan.analyze(data)
    
    # 只使用近1年数据可视化（更清晰）
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=365)
    plot_data = data[data.index >= start_date].copy()
    
    # 筛选此区间的买卖点
    buy_points = [bp for bp in chan.buy_points if bp['index'] >= start_date and bp['index'] <= end_date]
    sell_points = [sp for sp in chan.sell_points if sp['index'] >= start_date and sp['index'] <= end_date]
    
    # 创建图表
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    fig.suptitle(f'{symbol} - Realtime Chan Theory Signals (Last 1 Year)', fontsize=16, fontweight='bold')
    
    ax1 = axes[0]
    ax2 = axes[1]
    
    # 绘制K线
    for i, (date, row) in enumerate(plot_data.iterrows()):
        color = 'red' if row['Close'] >= row['Open'] else 'green'
        
        # 实体
        height = abs(row['Close'] - row['Open'])
        bottom = min(row['Close'], row['Open'])
        ax1.bar(date, height, bottom=bottom, color=color, width=0.8, alpha=0.8)
        
        # 影线
        ax1.plot([date, date], [row['Low'], row['High']], color=color, linewidth=0.5)
    
    # 标记买点
    for bp in buy_points:
        color = 'blue' if bp['type'] == 1 else 'orange'  # 一买蓝色，二买橙色
        marker = '^'
        ax1.scatter(bp['date'], bp['price'], color=color, marker=marker, s=200, 
                   zorder=5, edgecolors='black', linewidths=1.5,
                   label=f'Buy Type {bp["type"]}' if bp == buy_points[0] else '')
        # 添加文字标注
        ax1.annotate(f'B{bp["type"]}', xy=(bp['date'], bp['price']), 
                    xytext=(0, 10), textcoords='offset points',
                    ha='center', fontsize=9, color=color, fontweight='bold')
    
    # 标记卖点
    for sp in sell_points:
        color = 'purple' if sp['type'] == 1 else 'cyan'  # 一卖紫色，二卖青色
        marker = 'v'
        ax1.scatter(sp['date'], sp['price'], color=color, marker=marker, s=200,
                   zorder=5, edgecolors='black', linewidths=1.5,
                   label=f'Sell Type {sp["type"]}' if sp == sell_points[0] else '')
        # 添加文字标注
        ax1.annotate(f'S{sp["type"]}', xy=(sp['date'], sp['price']),
                    xytext=(0, -15), textcoords='offset points',
                    ha='center', fontsize=9, color=color, fontweight='bold')
    
    # 设置K线图
    ax1.set_ylabel('Price', fontsize=12)
    ax1.set_title(f'Candlestick with Realtime Chan Signals | Buy: {len(buy_points)} | Sell: {len(sell_points)}', 
                  fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # 添加图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='^', color='w', markerfacecolor='blue', markersize=12, label='First Buy'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='orange', markersize=12, label='Second Buy'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='purple', markersize=12, label='First Sell'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='cyan', markersize=12, label='Second Sell')
    ]
    ax1.legend(handles=legend_elements, loc='upper left', fontsize=10)
    
    # 绘制成交量
    colors = ['red' if plot_data['Close'].iloc[i] >= plot_data['Open'].iloc[i] else 'green' 
              for i in range(len(plot_data))]
    ax2.bar(plot_data.index, plot_data['Volume'], color=colors, alpha=0.6, width=0.8)
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, f'{symbol}_realtime_signals.png')
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Chart saved: {chart_file}")
    
    # 打印买卖点统计
    print(f"  Buy signals: {len(buy_points)} (Type1: {sum(1 for b in buy_points if b['type']==1)}, Type2: {sum(1 for b in buy_points if b['type']==2)})")
    print(f"  Sell signals: {len(sell_points)} (Type1: {sum(1 for s in sell_points if s['type']==1)}, Type2: {sum(1 for s in sell_points if s['type']==2)})")
    
    return chart_file, buy_points, sell_points


def plot_trade_simulation(data, symbol, output_dir='results/chan_realtime_signals'):
    """
    绘制交易模拟图 - 显示资金曲线和买卖点
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 运行分析
    chan = ChanTheoryRealtime(k_type='day')
    result = chan.analyze(data)
    
    # 只使用近2年数据
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=2*365)
    plot_data = data[data.index >= start_date].copy()
    
    # 获取买卖点
    buy_points = [bp for bp in chan.buy_points if bp['index'] >= start_date and bp['index'] <= end_date]
    sell_points = [sp for sp in chan.sell_points if sp['index'] >= start_date and sp['index'] <= end_date]
    
    # 简单回测
    initial_capital = 100000
    capital = initial_capital
    position = 0
    equity_curve = []
    
    # 合并信号并按时间排序
    all_signals = []
    for bp in buy_points:
        all_signals.append({'date': bp['index'], 'type': 'buy', 'price': bp['price']})
    for sp in sell_points:
        all_signals.append({'date': sp['index'], 'type': 'sell', 'price': sp['price']})
    all_signals.sort(key=lambda x: x['date'])
    
    # 计算每日资金曲线
    for date, row in plot_data.iterrows():
        # 检查是否有交易信号
        for signal in all_signals:
            if signal['date'] == date:
                if signal['type'] == 'buy' and position == 0:
                    shares = capital / signal['price']
                    capital = 0
                    position = shares
                elif signal['type'] == 'sell' and position > 0:
                    capital = position * signal['price']
                    position = 0
        
        current_value = capital + position * row['Close']
        equity_curve.append({'date': date, 'equity': current_value})
    
    equity_df = pd.DataFrame(equity_curve).set_index('date')
    
    # 创建图表
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    fig.suptitle(f'{symbol} - Trade Simulation (Realtime Chan Strategy)', fontsize=16, fontweight='bold')
    
    # 上图：K线 + 买卖点
    ax1 = axes[0]
    for date, row in plot_data.iterrows():
        color = 'red' if row['Close'] >= row['Open'] else 'green'
        height = abs(row['Close'] - row['Open'])
        bottom = min(row['Close'], row['Open'])
        ax1.bar(date, height, bottom=bottom, color=color, width=0.8, alpha=0.6)
        ax1.plot([date, date], [row['Low'], row['High']], color=color, linewidth=0.5)
    
    # 标记买卖点
    for bp in buy_points:
        color = 'blue' if bp['type'] == 1 else 'orange'
        ax1.scatter(bp['date'], bp['price'], color=color, marker='^', s=150, zorder=5, edgecolors='black')
    
    for sp in sell_points:
        color = 'purple' if sp['type'] == 1 else 'cyan'
        ax1.scatter(sp['date'], sp['price'], color=color, marker='v', s=150, zorder=5, edgecolors='black')
    
    ax1.set_ylabel('Price', fontsize=12)
    ax1.set_title('Price Chart with Trade Signals', fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # 下图：资金曲线
    ax2 = axes[1]
    ax2.plot(equity_df.index, equity_df['equity'], linewidth=2, color='blue', label='Strategy Equity')
    ax2.axhline(y=initial_capital, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    
    # 计算买入持有曲线
    bh_shares = initial_capital / plot_data['Close'].iloc[0]
    bh_equity = bh_shares * plot_data['Close']
    ax2.plot(plot_data.index, bh_equity, linewidth=1.5, color='orange', alpha=0.7, label='Buy & Hold')
    
    final_return = (equity_df['equity'].iloc[-1] - initial_capital) / initial_capital * 100
    bh_return = (bh_equity.iloc[-1] - initial_capital) / initial_capital * 100
    
    ax2.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_title(f'Equity Curve | Strategy: {final_return:.1f}% | Buy&Hold: {bh_return:.1f}%', fontsize=12)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart_file = os.path.join(output_dir, f'{symbol}_trade_simulation.png')
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Trade simulation chart saved: {chart_file}")
    
    return chart_file


def main():
    """主函数"""
    # 选择代表性股票
    symbols = [
        '000001.SZ',  # 平安银行
        '000333.SZ',  # 美的集团
        '002594.SZ',  # 比亚迪
        '600519.SS',  # 贵州茅台
        '601888.SS',  # 中国中免
    ]
    
    print("="*80)
    print("Generating Realtime Chan Theory Signal Charts")
    print("="*80)
    
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        data = load_stock_data(symbol, '20y')
        
        if data is None:
            print(f"  Data not found")
            continue
        
        print(f"  Data loaded: {len(data)} rows")
        
        # 生成K线+买卖点图
        plot_candlestick_with_signals(data, symbol)
        
        # 生成交易模拟图
        plot_trade_simulation(data, symbol)
    
    print("\n" + "="*80)
    print("All charts generated!")
    print("Charts saved in: results/chan_realtime_signals/")
    print("="*80)


if __name__ == '__main__':
    main()
