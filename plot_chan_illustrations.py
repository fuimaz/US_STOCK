import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
import os

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def generate_sample_data(n_days=100, trend='up'):
    """生成示例K线数据"""
    
    np.random.seed(42)
    
    if trend == 'up':
        base_price = 100
        trend_factor = 0.5
    elif trend == 'down':
        base_price = 150
        trend_factor = -0.5
    else:
        base_price = 125
        trend_factor = 0
    
    dates = pd.date_range(start='2024-01-01', periods=n_days, freq='D')
    
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    volumes = []
    
    price = base_price
    
    for i in range(n_days):
        # 趋势成分
        trend_change = trend_factor * (1 + np.random.normal(0, 0.3))
        
        # 随机波动
        random_change = np.random.normal(0, 2)
        
        # 开盘价
        open_price = price
        
        # 收盘价
        close_price = open_price + trend_change + random_change
        
        # 最高价和最低价
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 1))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 1))
        
        # 成交量
        volume = np.random.randint(10000, 50000)
        
        open_prices.append(open_price)
        high_prices.append(high_price)
        low_prices.append(low_price)
        close_prices.append(close_price)
        volumes.append(volume)
        
        price = close_price
    
    data = pd.DataFrame({
        'Date': dates,
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volumes
    })
    
    data.set_index('Date', inplace=True)
    
    return data

def identify_fenxing(data):
    """识别分型"""
    fenxing = []
    
    for i in range(1, len(data) - 1):
        prev_high = data['High'].iloc[i-1]
        curr_high = data['High'].iloc[i]
        next_high = data['High'].iloc[i+1]
        
        prev_low = data['Low'].iloc[i-1]
        curr_low = data['Low'].iloc[i]
        next_low = data['Low'].iloc[i+1]
        
        # 顶分型：中间最高
        if curr_high > prev_high and curr_high > next_high:
            fenxing.append({
                'index': i,
                'type': 'top',
                'price': curr_high,
                'date': data.index[i]
            })
        
        # 底分型：中间最低
        elif curr_low < prev_low and curr_low < next_low:
            fenxing.append({
                'index': i,
                'type': 'bottom',
                'price': curr_low,
                'date': data.index[i]
            })
    
    return fenxing

def plot_fenxing(data, fenxing, save_path):
    """绘制分型图"""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # 绘制K线
    colors = ['#ff5252' if data['Close'].iloc[i] >= data['Open'].iloc[i] else '#4caf50' 
              for i in range(len(data))]
    
    ax.bar(data.index, data['Close'] - data['Open'], bottom=data['Open'], 
           width=0.6, color=colors, alpha=0.8)
    ax.bar(data.index, data['High'] - data['Close'], bottom=data['Close'], 
           width=0.1, color=colors, alpha=0.8)
    ax.bar(data.index, data['Low'] - data['Open'], bottom=data['Open'], 
           width=0.1, color=colors, alpha=0.8)
    
    # 标注分型
    for fx in fenxing:
        if fx['type'] == 'top':
            ax.scatter(fx['date'], fx['price'], color='red', s=300, marker='v', 
                      zorder=5, label='顶分型' if fx == fenxing[0] or fx['type'] == 'top' and all(f['type'] != 'top' for f in fenxing[:fenxing.index(fx)]) else "")
            ax.annotate('顶分型', xy=(fx['date'], fx['price']), 
                       xytext=(0, 15), textcoords='offset points',
                       fontsize=10, color='red', fontweight='bold', ha='center')
        else:
            ax.scatter(fx['date'], fx['price'], color='green', s=300, marker='^', 
                      zorder=5, label='底分型' if fx == fenxing[0] or fx['type'] == 'bottom' and all(f['type'] != 'bottom' for f in fenxing[:fenxing.index(fx)]) else "")
            ax.annotate('底分型', xy=(fx['date'], fx['price']), 
                       xytext=(0, -20), textcoords='offset points',
                       fontsize=10, color='green', fontweight='bold', ha='center')
    
    ax.set_title('缠论分型识别', fontsize=16, fontweight='bold')
    ax.set_ylabel('价格', fontsize=12)
    ax.legend(loc='upper left', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

def plot_buy_sell_points(data, save_path):
    """绘制买卖点示意图"""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # 创建一个更明显的上涨下跌趋势
    dates = pd.date_range(start='2024-01-01', periods=80, freq='D')
    
    # 模拟数据：先上涨，后下跌
    prices = []
    for i in range(80):
        if i < 40:
            # 上涨阶段
            price = 100 + i * 1.5 + np.random.normal(0, 3)
        else:
            # 下跌阶段
            price = 160 - (i - 40) * 1.2 + np.random.normal(0, 3)
        prices.append(price)
    
    # 生成OHLC数据
    opens = []
    highs = []
    lows = []
    closes = []
    
    for i, price in enumerate(prices):
        open_p = price + np.random.normal(0, 1)
        close_p = price + np.random.normal(0, 1)
        high_p = max(open_p, close_p) + abs(np.random.normal(0, 1))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, 1))
        
        opens.append(open_p)
        highs.append(high_p)
        lows.append(low_p)
        closes.append(close_p)
    
    data = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes
    }, index=dates)
    
    # 绘制K线
    colors = ['#ff5252' if data['Close'].iloc[i] >= data['Open'].iloc[i] else '#4caf50' 
              for i in range(len(data))]
    
    ax.bar(data.index, data['Close'] - data['Open'], bottom=data['Open'], 
           width=0.6, color=colors, alpha=0.8)
    ax.bar(data.index, data['High'] - data['Close'], bottom=data['Close'], 
           width=0.1, color=colors, alpha=0.8)
    ax.bar(data.index, data['Low'] - data['Open'], bottom=data['Open'], 
           width=0.1, color=colors, alpha=0.8)
    
    # 标注第一类买点（下跌结束）
    buy_date = dates[45]
    buy_price = data['Close'].iloc[45]
    ax.scatter(buy_date, buy_price, color='red', s=400, marker='^', 
              zorder=5, label='第一类买点')
    ax.annotate('第一类买点\n向下线段结束', xy=(buy_date, buy_price), 
               xytext=(0, -35), textcoords='offset points',
               fontsize=12, color='red', fontweight='bold', ha='center',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9))
    
    # 标注第一类卖点（上涨结束）
    sell_date = dates[35]
    sell_price = data['High'].iloc[35]
    ax.scatter(sell_date, sell_price, color='green', s=400, marker='v', 
              zorder=5, label='第一类卖点')
    ax.annotate('第一类卖点\n向上线段结束', xy=(sell_date, sell_price), 
               xytext=(0, 25), textcoords='offset points',
               fontsize=12, color='green', fontweight='bold', ha='center',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9))
    
    # 标注第二类买点
    buy2_date = dates[50]
    buy2_price = data['Close'].iloc[50]
    ax.scatter(buy2_date, buy2_price, color='orange', s=400, marker='^', 
              zorder=5, label='第二类买点')
    ax.annotate('第二类买点\n回调不破前低', xy=(buy2_date, buy2_price), 
               xytext=(0, -35), textcoords='offset points',
               fontsize=12, color='orange', fontweight='bold', ha='center',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9))
    
    # 标注第二类卖点
    sell2_date = dates[30]
    sell2_price = data['Close'].iloc[30]
    ax.scatter(sell2_date, sell2_price, color='blue', s=400, marker='v', 
              zorder=5, label='第二类卖点')
    ax.annotate('第二类卖点\n反弹不破前高', xy=(sell2_date, sell2_price), 
               xytext=(0, 25), textcoords='offset points',
               fontsize=12, color='blue', fontweight='bold', ha='center',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9))
    
    # 绘制中枢区域
    center_start = dates[15]
    center_end = dates[25]
    center_low = 130
    center_high = 140
    
    rect = Rectangle((center_start, center_low), 
                    center_end - center_start, 
                    center_high - center_low,
                    linewidth=2, edgecolor='purple', facecolor='purple', alpha=0.2)
    ax.add_patch(rect)
    ax.text(center_start + (center_end - center_start) / 2, center_low - 5, 
           '中枢区域', fontsize=12, color='purple', fontweight='bold', ha='center')
    
    # 绘制向上线段
    ax.annotate('', xy=(dates[35], data['High'].iloc[35]), 
               xytext=(dates[5], data['Low'].iloc[5]),
               arrowprops=dict(arrowstyle='->', color='green', lw=3))
    ax.text(dates[20], data['High'].iloc[20] + 10, '向上线段', 
           fontsize=12, color='green', fontweight='bold', ha='center')
    
    # 绘制向下线段
    ax.annotate('', xy=(dates[45], data['Low'].iloc[45]), 
               xytext=(dates[35], data['High'].iloc[35]),
               arrowprops=dict(arrowstyle='->', color='red', lw=3))
    ax.text(dates[40], data['Low'].iloc[40] - 10, '向下线段', 
           fontsize=12, color='red', fontweight='bold', ha='center')
    
    ax.set_title('缠论买卖点示意图', fontsize=16, fontweight='bold')
    ax.set_ylabel('价格', fontsize=12)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

def plot_zhongshu(data, save_path):
    """绘制中枢示意图"""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # 创建震荡数据
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    
    prices = []
    for i in range(100):
        # 震荡上涨
        base = 100 + i * 0.3
        oscillation = 10 * np.sin(i * 0.2)
        noise = np.random.normal(0, 2)
        price = base + oscillation + noise
        prices.append(price)
    
    # 生成OHLC数据
    opens = []
    highs = []
    lows = []
    closes = []
    
    for i, price in enumerate(prices):
        open_p = price + np.random.normal(0, 1)
        close_p = price + np.random.normal(0, 1)
        high_p = max(open_p, close_p) + abs(np.random.normal(0, 1))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, 1))
        
        opens.append(open_p)
        highs.append(high_p)
        lows.append(low_p)
        closes.append(close_p)
    
    data = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes
    }, index=dates)
    
    # 绘制K线
    colors = ['#ff5252' if data['Close'].iloc[i] >= data['Open'].iloc[i] else '#4caf50' 
              for i in range(len(data))]
    
    ax.bar(data.index, data['Close'] - data['Open'], bottom=data['Open'], 
           width=0.6, color=colors, alpha=0.8)
    ax.bar(data.index, data['High'] - data['Close'], bottom=data['Close'], 
           width=0.1, color=colors, alpha=0.8)
    ax.bar(data.index, data['Low'] - data['Open'], bottom=data['Open'], 
           width=0.1, color=colors, alpha=0.8)
    
    # 绘制中枢区域（多个）
    center_regions = [
        (dates[10], dates[30], 95, 105),
        (dates[40], dates[60], 105, 115),
        (dates[70], dates[90], 115, 125)
    ]
    
    for i, (start, end, low, high) in enumerate(center_regions):
        rect = Rectangle((start, low), 
                        end - start, 
                        high - low,
                        linewidth=2, edgecolor='purple', facecolor='purple', alpha=0.2)
        ax.add_patch(rect)
        ax.text(start + (end - start) / 2, low - 3, 
               f'中枢{i+1}', fontsize=11, color='purple', fontweight='bold', ha='center')
    
    # 标注第三类买点（突破中枢后回抽）
    buy3_date = dates[65]
    buy3_price = data['Close'].iloc[65]
    ax.scatter(buy3_date, buy3_price, color='orange', s=400, marker='^', 
              zorder=5, label='第三类买点')
    ax.annotate('第三类买点\n突破中枢后回抽', xy=(buy3_date, buy3_price), 
               xytext=(0, -35), textcoords='offset points',
               fontsize=11, color='orange', fontweight='bold', ha='center',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9))
    
    # 标注第三类卖点（跌破中枢后反弹）
    sell3_date = dates[35]
    sell3_price = data['Close'].iloc[35]
    ax.scatter(sell3_date, sell3_price, color='blue', s=400, marker='v', 
              zorder=5, label='第三类卖点')
    ax.annotate('第三类卖点\n跌破中枢后反弹', xy=(sell3_date, sell3_price), 
               xytext=(0, 25), textcoords='offset points',
               fontsize=11, color='blue', fontweight='bold', ha='center',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9))
    
    ax.set_title('缠论中枢示意图', fontsize=16, fontweight='bold')
    ax.set_ylabel('价格', fontsize=12)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

def plot_bi_xianduan(data, save_path):
    """绘制笔和线段示意图"""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # 创建明显的波浪数据
    dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
    
    prices = []
    for i in range(60):
        # 波浪形态
        wave = 5 * np.sin(i * 0.3) + 5 * np.sin(i * 0.15)
        trend = i * 0.2
        noise = np.random.normal(0, 1)
        price = 100 + wave + trend + noise
        prices.append(price)
    
    # 生成OHLC数据
    opens = []
    highs = []
    lows = []
    closes = []
    
    for i, price in enumerate(prices):
        open_p = price + np.random.normal(0, 0.5)
        close_p = price + np.random.normal(0, 0.5)
        high_p = max(open_p, close_p) + abs(np.random.normal(0, 0.5))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, 0.5))
        
        opens.append(open_p)
        highs.append(high_p)
        lows.append(low_p)
        closes.append(close_p)
    
    data = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes
    }, index=dates)
    
    # 绘制K线
    colors = ['#ff5252' if data['Close'].iloc[i] >= data['Open'].iloc[i] else '#4caf50' 
              for i in range(len(data))]
    
    ax.bar(data.index, data['Close'] - data['Open'], bottom=data['Open'], 
           width=0.6, color=colors, alpha=0.8)
    ax.bar(data.index, data['High'] - data['Close'], bottom=data['Close'], 
           width=0.1, color=colors, alpha=0.8)
    ax.bar(data.index, data['Low'] - data['Open'], bottom=data['Open'], 
           width=0.1, color=colors, alpha=0.8)
    
    # 识别关键点（模拟）
    key_points = [
        (dates[5], data['Low'].iloc[5], '底分型'),
        (dates[12], data['High'].iloc[12], '顶分型'),
        (dates[20], data['Low'].iloc[20], '底分型'),
        (dates[28], data['High'].iloc[28], '顶分型'),
        (dates[38], data['Low'].iloc[38], '底分型'),
        (dates[48], data['High'].iloc[48], '顶分型'),
        (dates[55], data['Low'].iloc[55], '底分型'),
    ]
    
    # 绘制笔（连接顶底分型）
    for i in range(len(key_points) - 1):
        start_date, start_price, _ = key_points[i]
        end_date, end_price, _ = key_points[i + 1]
        
        color = 'green' if end_price > start_price else 'red'
        ax.plot([start_date, end_date], [start_price, end_price], 
               color=color, linewidth=3, alpha=0.7)
        
        # 标注笔
        mid_date = start_date + (end_date - start_date) / 2
        mid_price = (start_price + end_price) / 2
        bi_type = '向上笔' if end_price > start_price else '向下笔'
        ax.text(mid_date, mid_price + 3, bi_type, 
               fontsize=10, color=color, fontweight='bold', ha='center',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 标注关键点
    for date, price, label in key_points:
        if '顶' in label:
            ax.scatter(date, price, color='red', s=200, marker='v', zorder=5)
        else:
            ax.scatter(date, price, color='green', s=200, marker='^', zorder=5)
    
    # 标注线段
    ax.text(dates[17], data['High'].iloc[17] + 10, '向上线段', 
           fontsize=12, color='green', fontweight='bold', ha='center',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7))
    
    ax.text(dates[33], data['Low'].iloc[33] - 10, '向下线段', 
           fontsize=12, color='red', fontweight='bold', ha='center',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.7))
    
    ax.set_title('缠论笔和线段示意图', fontsize=16, fontweight='bold')
    ax.set_ylabel('价格', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

def main():
    """主函数"""
    print("=" * 100)
    print("缠论买卖点可视化")
    print("=" * 100)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/chan_illustrations'
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ 结果将保存到: {output_dir}/")
    print()
    
    # 1. 绘制分型图
    print("1. 生成分型示意图...")
    data_up = generate_sample_data(n_days=80, trend='up')
    fenxing = identify_fenxing(data_up)
    plot_fenxing(data_up, fenxing, os.path.join(output_dir, '01_fenxing.png'))
    print("  ✓ 分型示意图已保存")
    
    # 2. 绘制买卖点示意图
    print("2. 生成买卖点示意图...")
    plot_buy_sell_points(data_up, os.path.join(output_dir, '02_buy_sell_points.png'))
    print("  ✓ 买卖点示意图已保存")
    
    # 3. 绘制中枢示意图
    print("3. 生成中枢示意图...")
    plot_zhongshu(data_up, os.path.join(output_dir, '03_zhongshu.png'))
    print("  ✓ 中枢示意图已保存")
    
    # 4. 绘制笔和线段示意图
    print("4. 生成笔和线段示意图...")
    plot_bi_xianduan(data_up, os.path.join(output_dir, '04_bi_xianduan.png'))
    print("  ✓ 笔和线段示意图已保存")
    
    print()
    print("=" * 100)
    print("所有示意图已生成完成！")
    print("=" * 100)

if __name__ == '__main__':
    main()
