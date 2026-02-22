"""
测试缠论指标实现
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from chan_theory import ChanTheory
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os


def create_mock_data():
    """
    创建模拟K线数据用于测试
    构造一个明显的上涨-盘整-下跌走势
    """
    np.random.seed(42)
    
    # 生成100天的数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    # 构造走势：先上涨，再盘整，最后下跌
    prices = []
    base_price = 100
    
    for i in range(100):
        if i < 30:
            # 上涨阶段
            trend = 0.5
        elif i < 60:
            # 盘整阶段
            trend = 0.1 * np.sin(i * 0.3)
        else:
            # 下跌阶段
            trend = -0.4
        
        noise = np.random.normal(0, 0.5)
        close = base_price + trend * i + noise
        
        # 构造OHLC
        high = close + abs(np.random.normal(0, 0.5))
        low = close - abs(np.random.normal(0, 0.5))
        open_price = close + np.random.normal(0, 0.3)
        
        prices.append({
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close,
            'Volume': np.random.randint(1000000, 5000000)
        })
    
    df = pd.DataFrame(prices, index=dates)
    return df


def test_chan_theory():
    """
    测试缠论指标
    """
    print("=" * 80)
    print("缠论指标测试")
    print("=" * 80)
    
    # 创建模拟数据
    print("\n1. 创建模拟数据...")
    data = create_mock_data()
    print(f"   数据范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"   数据条数: {len(data)}")
    print(f"   价格范围: {data['Low'].min():.2f} - {data['High'].max():.2f}")
    
    # 初始化缠论指标
    print("\n2. 初始化缠论指标...")
    chan = ChanTheory(k_type='day')
    
    # 执行完整分析
    print("\n3. 执行缠论分析...")
    result = chan.analyze(data)
    
    # 获取汇总
    summary = chan.get_summary()
    
    print("\n4. 分析结果汇总:")
    print(f"   分型数量: {summary['fenxing_count']}")
    print(f"   笔数量: {summary['bi_count']}")
    print(f"   线段数量: {summary['xianduan_count']}")
    print(f"   中枢数量: {summary['zhongshu_count']}")
    print(f"   买点数量: {summary['buy_points']}")
    print(f"   卖点数量: {summary['sell_points']}")
    
    # 显示买卖点详情
    if summary['buy_points'] > 0:
        print("\n   买点详情:")
        for bp in summary['buy_point_details'][:5]:
            print(f"      {bp['date'].strftime('%Y-%m-%d')}: {bp['desc']} 价格={bp['price']:.2f}")
    
    if summary['sell_points'] > 0:
        print("\n   卖点详情:")
        for sp in summary['sell_point_details'][:5]:
            print(f"      {sp['date'].strftime('%Y-%m-%d')}: {sp['desc']} 价格={sp['price']:.2f}")
    
    # 可视化
    print("\n5. 生成可视化图表...")
    visualize_result(data, chan, result)
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    
    return chan, result


def visualize_result(data, chan, result):
    """
    可视化缠论分析结果
    """
    # 创建输出目录
    output_dir = 'results/chan_theory'
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, axes = plt.subplots(5, 1, figsize=(16, 24), sharex=True)
    fig.suptitle('缠论指标分析', fontsize=16, fontweight='bold')
    
    # 1. 原始K线价格
    ax1 = axes[0]
    ax1.plot(data.index, data['Close'], label='收盘价', linewidth=1.5, color='black', alpha=0.7)
    ax1.set_ylabel('价格', fontsize=12)
    ax1.set_title('原始价格走势', fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 2. 分型
    ax2 = axes[1]
    ax2.plot(data.index, data['Close'], label='收盘价', linewidth=1, color='gray', alpha=0.5)
    
    # 标记顶分型
    for fx in chan.fenxing_list:
        if fx['type'] == 1:
            ax2.scatter(fx['date'], fx['high'], color='red', marker='v', s=150, 
                       label='顶分型' if fx == chan.fenxing_list[0] else '', 
                       zorder=5, edgecolors='black', linewidths=1)
        else:
            ax2.scatter(fx['date'], fx['low'], color='green', marker='^', s=150,
                       label='底分型' if fx == chan.fenxing_list[0] else '',
                       zorder=5, edgecolors='black', linewidths=1)
    
    ax2.set_ylabel('价格', fontsize=12)
    ax2.set_title('分型识别', fontsize=14)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # 3. 笔
    ax3 = axes[2]
    ax3.plot(data.index, data['Close'], label='收盘价', linewidth=1, color='gray', alpha=0.5)
    
    for bi in chan.bi_list:
        color = 'red' if bi['type'] == 1 else 'green'
        ax3.plot([bi['start'], bi['end']], [bi['start_price'], bi['end_price']],
                color=color, linewidth=2, alpha=0.7)
        # 标记起点和终点
        ax3.scatter(bi['start'], bi['start_price'], color=color, s=50, zorder=5)
        ax3.scatter(bi['end'], bi['end_price'], color=color, s=50, zorder=5)
    
    ax3.set_ylabel('价格', fontsize=12)
    ax3.set_title('笔', fontsize=14)
    ax3.grid(True, alpha=0.3)
    
    # 4. 线段
    ax4 = axes[3]
    ax4.plot(data.index, data['Close'], label='收盘价', linewidth=1, color='gray', alpha=0.5)
    
    for xd in chan.xianduan_list:
        color = 'red' if xd['type'] == 1 else 'green'
        ax4.plot([xd['start'], xd['end']], [xd['low'], xd['high']],
                color=color, linewidth=3, alpha=0.7)
    
    ax4.set_ylabel('价格', fontsize=12)
    ax4.set_title('线段', fontsize=14)
    ax4.grid(True, alpha=0.3)
    
    # 5. 中枢和买卖点
    ax5 = axes[4]
    ax5.plot(data.index, data['Close'], label='收盘价', linewidth=1.5, color='black', alpha=0.7)
    
    # 绘制中枢
    for zs in chan.zhongshu_list:
        # 绘制中枢区间
        ax5.fill_between([zs['start'], zs['end']], zs['low'], zs['high'],
                        alpha=0.2, color='blue')
        ax5.plot([zs['start'], zs['end']], [zs['high'], zs['high']],
                color='blue', linewidth=1, linestyle='--', alpha=0.7)
        ax5.plot([zs['start'], zs['end']], [zs['low'], zs['low']],
                color='blue', linewidth=1, linestyle='--', alpha=0.7)
    
    # 标记买点
    for bp in chan.buy_points:
        marker = {1: '^', 2: '^', 3: '^'}[bp['type']]
        color = {1: 'red', 2: 'orange', 3: 'purple'}[bp['type']]
        size = {1: 200, 2: 150, 3: 150}[bp['type']]
        ax5.scatter(bp['date'], bp['price'], color=color, marker=marker, s=size,
                   label=f"第{bp['type']}类买点" if bp == chan.buy_points[0] else '',
                   zorder=10, edgecolors='black', linewidths=1.5)
    
    # 标记卖点
    for sp in chan.sell_points:
        marker = {1: 'v', 2: 'v', 3: 'v'}[sp['type']]
        color = {1: 'green', 2: 'cyan', 3: 'blue'}[sp['type']]
        size = {1: 200, 2: 150, 3: 150}[sp['type']]
        ax5.scatter(sp['date'], sp['price'], color=color, marker=marker, s=size,
                   label=f"第{sp['type']}类卖点" if sp == chan.sell_points[0] else '',
                   zorder=10, edgecolors='black', linewidths=1.5)
    
    ax5.set_ylabel('价格', fontsize=12)
    ax5.set_xlabel('日期', fontsize=12)
    ax5.set_title('中枢与买卖点', fontsize=14)
    ax5.legend(loc='upper left')
    ax5.grid(True, alpha=0.3)
    
    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, 'chan_theory_test.png')
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"   图表已保存到: {chart_file}")
    
    # 保存数据
    data_file = os.path.join(output_dir, 'chan_theory_result.csv')
    result.to_csv(data_file)
    print(f"   数据已保存到: {data_file}")


if __name__ == '__main__':
    chan, result = test_chan_theory()
