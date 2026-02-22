"""
用真实股票数据测试缠论指标
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from chan_theory import ChanTheory
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def test_with_real_data():
    """用真实数据测试"""
    print("Testing with real stock data...")
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=3,
        retry_delay=3.0
    )
    
    # 获取AAPL数据
    symbol = 'AAPL'
    print(f"\nFetching data for {symbol}...")
    
    try:
        data = fetcher.fetch_stock_data(symbol, period='1y')
        
        if data is None or len(data) == 0:
            print("No data fetched!")
            return
        
        print(f"Data loaded: {len(data)} rows")
        print(f"Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
        print(f"Price range: ${data['Low'].min():.2f} - ${data['High'].max():.2f}")
        
        # 分析
        print("\nAnalyzing with Chan Theory...")
        chan = ChanTheory(k_type='day')
        result = chan.analyze(data)
        
        summary = chan.get_summary()
        
        print("\n=== Results ===")
        print(f"Fenxing: {summary['fenxing_count']}")
        print(f"Bi: {summary['bi_count']}")
        print(f"Xianduan: {summary['xianduan_count']}")
        print(f"Zhongshu: {summary['zhongshu_count']}")
        print(f"Buy points: {summary['buy_points']}")
        print(f"Sell points: {summary['sell_points']}")
        
        # Show buy/sell points
        if summary['buy_points'] > 0:
            print("\nBuy Points:")
            for bp in summary['buy_point_details'][:5]:
                print(f"  {bp['date'].strftime('%Y-%m-%d')}: {bp['desc']} @ ${bp['price']:.2f}")
        
        if summary['sell_points'] > 0:
            print("\nSell Points:")
            for sp in summary['sell_point_details'][:5]:
                print(f"  {sp['date'].strftime('%Y-%m-%d')}: {sp['desc']} @ ${sp['price']:.2f}")
        
        # Visualize
        visualize(data, chan, result, symbol)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def visualize(data, chan, result, symbol):
    """可视化"""
    output_dir = 'results/chan_theory'
    os.makedirs(output_dir, exist_ok=True)
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, axes = plt.subplots(5, 1, figsize=(16, 20), sharex=True)
    fig.suptitle(f'{symbol} - Chan Theory Analysis', fontsize=16, fontweight='bold')
    
    # 1. Price
    ax1 = axes[0]
    ax1.plot(data.index, data['Close'], label='Close', linewidth=1.5, color='black')
    ax1.set_ylabel('Price')
    ax1.set_title('Price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Fenxing
    ax2 = axes[1]
    ax2.plot(data.index, data['Close'], linewidth=1, color='gray', alpha=0.5)
    for fx in chan.fenxing_list:
        color = 'red' if fx['type'] == 1 else 'green'
        marker = 'v' if fx['type'] == 1 else '^'
        price = fx['high'] if fx['type'] == 1 else fx['low']
        ax2.scatter(fx['date'], price, color=color, marker=marker, s=100, zorder=5)
    ax2.set_ylabel('Price')
    ax2.set_title(f'Fenxing ({len(chan.fenxing_list)} found)')
    ax2.grid(True, alpha=0.3)
    
    # 3. Bi
    ax3 = axes[2]
    ax3.plot(data.index, data['Close'], linewidth=1, color='gray', alpha=0.5)
    for bi in chan.bi_list:
        color = 'red' if bi['type'] == 1 else 'green'
        ax3.plot([bi['start'], bi['end']], [bi['start_price'], bi['end_price']], 
                color=color, linewidth=2, alpha=0.7)
    ax3.set_ylabel('Price')
    ax3.set_title(f'Bi ({len(chan.bi_list)} found)')
    ax3.grid(True, alpha=0.3)
    
    # 4. Xianduan
    ax4 = axes[3]
    ax4.plot(data.index, data['Close'], linewidth=1, color='gray', alpha=0.5)
    for xd in chan.xianduan_list:
        color = 'red' if xd['type'] == 1 else 'green'
        ax4.plot([xd['start'], xd['end']], [xd['low'], xd['high']], 
                color=color, linewidth=3, alpha=0.7)
    ax4.set_ylabel('Price')
    ax4.set_title(f'Xianduan ({len(chan.xianduan_list)} found)')
    ax4.grid(True, alpha=0.3)
    
    # 5. Zhongshu and Buy/Sell Points
    ax5 = axes[4]
    ax5.plot(data.index, data['Close'], linewidth=1.5, color='black', alpha=0.7)
    
    # Zhongshu
    for zs in chan.zhongshu_list:
        ax5.fill_between([zs['start'], zs['end']], zs['low'], zs['high'],
                        alpha=0.2, color='blue')
    
    # Buy points
    for bp in chan.buy_points:
        colors = {1: 'red', 2: 'orange', 3: 'purple'}
        ax5.scatter(bp['date'], bp['price'], color=colors.get(bp['type'], 'red'), 
                   marker='^', s=200, zorder=10, edgecolors='black', linewidths=1.5)
    
    # Sell points
    for sp in chan.sell_points:
        colors = {1: 'green', 2: 'cyan', 3: 'blue'}
        ax5.scatter(sp['date'], sp['price'], color=colors.get(sp['type'], 'green'),
                   marker='v', s=200, zorder=10, edgecolors='black', linewidths=1.5)
    
    ax5.set_ylabel('Price')
    ax5.set_xlabel('Date')
    ax5.set_title(f'Zhongshu ({len(chan.zhongshu_list)}) & Buy/Sell Points ({len(chan.buy_points)}/{len(chan.sell_points)})')
    ax5.grid(True, alpha=0.3)
    
    # Format x-axis
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart_file = os.path.join(output_dir, f'{symbol}_chan_analysis.png')
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\nChart saved to: {chart_file}")

if __name__ == '__main__':
    test_with_real_data()
