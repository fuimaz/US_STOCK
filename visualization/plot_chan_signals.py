"""
缠论买卖点可视化
在K线图上标记买卖点
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from chan_theory import ChanTheory
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


def plot_candlestick_with_signals(data, symbol, output_dir='results/chan_signals'):
    """
    绘制K线图并标记买卖点
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 运行缠论分析
    chan = ChanTheory(k_type='day')
    result = chan.analyze(data)
    
    # 只使用近3年数据可视化（更清晰）
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=3*365)
    plot_data = data[data.index >= start_date].copy()
    
    # 筛选此区间的买卖点
    buy_points = [bp for bp in chan.buy_points if bp['index'] >= start_date and bp['index'] <= end_date]
    sell_points = [sp for sp in chan.sell_points if sp['index'] >= start_date and sp['index'] <= end_date]
    
    # 创建图表
    fig, axes = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    fig.suptitle(f'{symbol} - Chan Theory Signals (Last 3 Years)', fontsize=16, fontweight='bold')
    
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
                    ha='center', fontsize=8, color=color, fontweight='bold')
    
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
                    ha='center', fontsize=8, color=color, fontweight='bold')
    
    # 设置K线图
    ax1.set_ylabel('Price', fontsize=12)
    ax1.set_title(f'Candlestick Chart with Buy/Sell Points | Buy: {len(buy_points)} | Sell: {len(sell_points)}', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=10)
    
    # 绘制成交量
    colors = ['red' if plot_data['Close'].iloc[i] >= plot_data['Open'].iloc[i] else 'green' 
              for i in range(len(plot_data))]
    ax2.bar(plot_data.index, plot_data['Volume'], color=colors, alpha=0.6, width=0.8)
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, f'{symbol}_signals.png')
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Chart saved: {chart_file}")
    return chart_file


def plot_strategy_comparison(data, symbol, output_dir='results/chan_signals'):
    """
    对比三种策略的买卖点
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 运行缠论分析
    chan = ChanTheory(k_type='day')
    result = chan.analyze(data)
    
    # 只使用近2年数据
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=2*365)
    plot_data = data[data.index >= start_date].copy()
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 16), sharex=True)
    fig.suptitle(f'{symbol} - Strategy Comparison (Last 2 Years)', fontsize=16, fontweight='bold')
    
    strategies = [
        ('all', 'All Signals (B1/B2/S1/S2)', axes[0]),
        ('no_first_sell', 'Ignore First Sell (B1/B2/S2)', axes[1]),
        ('only_first', 'Only First Signals (B1/S1)', axes[2])
    ]
    
    for strategy_type, title, ax in strategies:
        # 筛选买卖点
        if strategy_type == 'all':
            buy_points = [bp for bp in chan.buy_points if bp['type'] in [1, 2] and bp['index'] >= start_date]
            sell_points = [sp for sp in chan.sell_points if sp['type'] in [1, 2] and sp['index'] >= start_date]
        elif strategy_type == 'no_first_sell':
            buy_points = [bp for bp in chan.buy_points if bp['type'] in [1, 2] and bp['index'] >= start_date]
            sell_points = [sp for sp in chan.sell_points if sp['type'] == 2 and sp['index'] >= start_date]
        else:  # only_first
            buy_points = [bp for bp in chan.buy_points if bp['type'] == 1 and bp['index'] >= start_date]
            sell_points = [sp for sp in chan.sell_points if sp['type'] == 1 and sp['index'] >= start_date]
        
        # 绘制K线
        for i, (date, row) in enumerate(plot_data.iterrows()):
            color = 'red' if row['Close'] >= row['Open'] else 'green'
            height = abs(row['Close'] - row['Open'])
            bottom = min(row['Close'], row['Open'])
            ax.bar(date, height, bottom=bottom, color=color, width=0.8, alpha=0.8)
            ax.plot([date, date], [row['Low'], row['High']], color=color, linewidth=0.5)
        
        # 标记买点
        for bp in buy_points:
            color = 'blue' if bp['type'] == 1 else 'orange'
            ax.scatter(bp['date'], bp['price'], color=color, marker='^', s=150,
                      zorder=5, edgecolors='black', linewidths=1)
        
        # 标记卖点
        for sp in sell_points:
            color = 'purple' if sp['type'] == 1 else 'cyan'
            ax.scatter(sp['date'], sp['price'], color=color, marker='v', s=150,
                      zorder=5, edgecolors='black', linewidths=1)
        
        ax.set_ylabel('Price', fontsize=11)
        ax.set_title(f'{title} | Buy: {len(buy_points)} | Sell: {len(sell_points)}', fontsize=11)
        ax.grid(True, alpha=0.3)
        
        # 添加图例
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='^', color='w', markerfacecolor='blue', markersize=10, label='Buy 1'),
            Line2D([0], [0], marker='^', color='w', markerfacecolor='orange', markersize=10, label='Buy 2'),
            Line2D([0], [0], marker='v', color='w', markerfacecolor='purple', markersize=10, label='Sell 1'),
            Line2D([0], [0], marker='v', color='w', markerfacecolor='cyan', markersize=10, label='Sell 2')
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=9)
    
    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart_file = os.path.join(output_dir, f'{symbol}_strategy_comparison.png')
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Comparison chart saved: {chart_file}")
    return chart_file


def main():
    """主函数"""
    # 选择几只代表性股票
    symbols = [
        '000001.SZ',  # 平安银行
        '000333.SZ',  # 美的集团
        '002594.SZ',  # 比亚迪
        '300750.SZ',  # 宁德时代
        '600519.SS',  # 贵州茅台
    ]
    
    print("="*70)
    print("Generating Chan Theory Signal Charts")
    print("="*70)
    
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        data = load_stock_data(symbol, '20y')
        
        if data is None:
            print(f"  Data not found")
            continue
        
        print(f"  Data loaded: {len(data)} rows")
        
        # 生成K线+买卖点图
        plot_candlestick_with_signals(data, symbol)
        
        # 生成策略对比图
        plot_strategy_comparison(data, symbol)
    
    print("\n" + "="*70)
    print("All charts generated!")
    print("="*70)


if __name__ == '__main__':
    main()
