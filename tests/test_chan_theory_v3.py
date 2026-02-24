"""
测试缠论指标并可视化 - 使用V3版本
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from chan_theory_v3 import ChanTheory
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

def resample_to_weekly(data):
    """
    将日K数据转换为周K数据
    
    Args:
        data: 日K数据DataFrame
    
    Returns:
        周K数据DataFrame
    """
    # 使用周重采样，取每周的开盘价、最高价、最低价、收盘价
    weekly = pd.DataFrame()
    weekly['Open'] = data['Open'].resample('W').first()
    weekly['High'] = data['High'].resample('W').max()
    weekly['Low'] = data['Low'].resample('W').min()
    weekly['Close'] = data['Close'].resample('W').last()
    weekly['Volume'] = data['Volume'].resample('W').sum()
    
    # 删除NaN值
    weekly = weekly.dropna()
    
    return weekly

def test_chan_theory():
    """
    测试缠论指标并可视化
    """
    print("=" * 100)
    print("缠论指标测试与可视化（V3版本）")
    print("=" * 100)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/chan_theory_v3'
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ 结果将保存到: {output_dir}/")
    print()
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 选择股票进行测试
    test_symbols = [
        ('601186.SS', 'day'),  # 中国铁建 - 日K
        ('601186.SS', 'week'),  # 中国铁建 - 周K
        ('600519.SS', 'day'),  # 贵州茅台 - 日K
    ]
    
    for symbol, k_type in test_symbols:
        print(f"正在分析 {symbol} ({'日K' if k_type == 'day' else '周K'})...")
        print("-" * 100)
        
        try:
            # 获取数据
            data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
            
            if data is None or len(data) == 0:
                print(f"✗ 未获取到数据")
                continue
            
            print(f"✓ 数据获取完成，共 {len(data)} 条记录")
            print(f"  时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
            
            # 如果是周K，转换数据
            if k_type == 'week':
                data = resample_to_weekly(data)
                print(f"✓ 转换为周K，共 {len(data)} 条记录")
            
            # 初始化缠论指标
            chan = ChanTheory(k_type=k_type)
            
            # 完整分析
            result = chan.analyze(data)
            
            # 统计结果
            fenxing_count = len(chan.fenxing_list)
            bi_count = len(chan.bi_list)
            xianduan_count = len(chan.xianduan_list)
            zhongshu_count = len(chan.zhongshu_list)
            buy_points = len(chan.buy_points)
            sell_points = len(chan.sell_points)
            
            print(f"✓ 缠论分析完成")
            print(f"  分型数量: {fenxing_count}")
            print(f"  笔数量: {bi_count}")
            print(f"  线段数量: {xianduan_count}")
            print(f"  中枢数量: {zhongshu_count}")
            print(f"  买点数量: {buy_points}")
            print(f"  卖点数量: {sell_points}")
            
            # 显示买卖点详情
            if buy_points > 0:
                print(f"\n  买点详情:")
                for bp in chan.buy_points[:10]:  # 只显示前10个
                    print(f"    {bp['index'].strftime('%Y-%m-%d')}: 第{bp['type']}类买点，价格 {bp['price']:.2f}")
            
            if sell_points > 0:
                print(f"\n  卖点详情:")
                for sp in chan.sell_points[:10]:  # 只显示前10个
                    print(f"    {sp['index'].strftime('%Y-%m-%d')}: 第{sp['type']}类卖点，价格 {sp['price']:.2f}")
            
            # 可视化
            visualize_chan_theory(symbol, k_type, result, chan, output_dir)
            
            # 保存结果
            output_file = os.path.join(output_dir, f'{symbol}_{k_type}_result.csv')
            result.to_csv(output_file)
            print(f"\n✓ 结果已保存到: {output_file}")
            
        except Exception as e:
            print(f"✗ 分析失败: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 100)
    print("测试完成！")
    print("=" * 100)

def visualize_chan_theory(symbol, k_type, data, chan, output_dir):
    """
    可视化缠论指标
    """
    print(f"\n正在生成 {symbol} ({'日K' if k_type == 'day' else '周K'}) 的可视化图表...")
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建图表
    fig, axes = plt.subplots(4, 1, figsize=(16, 20), sharex=True)
    fig.suptitle(f'{symbol} - 缠论指标分析（{"日K" if k_type == "day" else "周K"}）', fontsize=16, fontweight='bold')
    
    # 1. 价格走势与分型
    ax1 = axes[0]
    ax1.plot(data.index, data['Close'], label='收盘价', linewidth=1.5, alpha=0.8)
    
    # 标记顶分型
    for fenxing in chan.fenxing_list:
        if fenxing['type'] == 1:
            ax1.scatter(fenxing['index'], fenxing['high'], color='red', marker='v', s=200, 
                       label='顶分型' if fenxing == chan.fenxing_list[0] else '', zorder=5, edgecolors='black', linewidths=1)
    
    # 标记底分型
    for fenxing in chan.fenxing_list:
        if fenxing['type'] == -1:
            ax1.scatter(fenxing['index'], fenxing['low'], color='green', marker='^', s=200, 
                       label='底分型' if fenxing == chan.fenxing_list[0] else '', zorder=5, edgecolors='black', linewidths=1)
    
    ax1.set_ylabel('价格', fontsize=12)
    ax1.set_title('价格走势与分型', fontsize=14)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 2. 价格走势与笔
    ax2 = axes[1]
    ax2.plot(data.index, data['Close'], label='收盘价', linewidth=1.5, alpha=0.8)
    
    # 绘制笔
    for bi in chan.bi_list:
        if bi['type'] == 1:
            ax2.plot([bi['start'], bi['end']], [bi['start_price'], bi['end_price']], 
                     color='red', linewidth=2, alpha=0.6)
        else:
            ax2.plot([bi['start'], bi['end']], [bi['start_price'], bi['end_price']], 
                     color='green', linewidth=2, alpha=0.6)
    
    ax2.set_ylabel('价格', fontsize=12)
    ax2.set_title('价格走势与笔', fontsize=14)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 3. 价格走势与线段
    ax3 = axes[2]
    ax3.plot(data.index, data['Close'], label='收盘价', linewidth=1.5, alpha=0.8)
    
    # 绘制线段
    for xianduan in chan.xianduan_list:
        if xianduan['type'] == 1:
            ax3.plot([xianduan['start'], xianduan['end']], [xianduan['low'], xianduan['high']], 
                     color='red', linewidth=3, alpha=0.6)
        else:
            ax3.plot([xianduan['start'], xianduan['end']], [xianduan['high'], xianduan['low']], 
                     color='green', linewidth=3, alpha=0.6)
    
    ax3.set_ylabel('价格', fontsize=12)
    ax3.set_title('价格走势与线段', fontsize=14)
    ax3.legend(loc='upper left', fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # 4. 价格走势与中枢和买卖点
    ax4 = axes[3]
    ax4.plot(data.index, data['Close'], label='收盘价', linewidth=1.5, alpha=0.8)
    
    # 标记中枢
    for zhongshu in chan.zhongshu_list:
        start_idx = data.index.get_loc(zhongshu['start'])
        end_idx = data.index.get_loc(zhongshu['end'])
        ax4.fill_between(data.index[start_idx:end_idx + 1], 
                       zhongshu['low'], zhongshu['high'],
                       alpha=0.2, color='blue', label='中枢' if zhongshu == chan.zhongshu_list[0] else '')
    
    # 标记买点
    for buy_point in chan.buy_points:
        ax4.scatter(buy_point['index'], buy_point['price'], color='red', marker='^', s=300, 
                   label=f'第{buy_point["type"]}类买点' if buy_point == chan.buy_points[0] else '', 
                   zorder=5, edgecolors='black', linewidths=2)
    
    # 标记卖点
    for sell_point in chan.sell_points:
        ax4.scatter(sell_point['index'], sell_point['price'], color='green', marker='v', s=300, 
                   label=f'第{sell_point["type"]}类卖点' if sell_point == chan.sell_points[0] else '', 
                   zorder=5, edgecolors='black', linewidths=2)
    
    ax4.set_ylabel('价格', fontsize=12)
    ax4.set_title('价格走势与中枢、买卖点', fontsize=14)
    ax4.legend(loc='upper left', fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_minor_locator(mdates.MonthLocator([1, 4, 7, 10]))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, f'{symbol}_{k_type}_chart.png')
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 图表已保存到: {chart_file}")

if __name__ == '__main__':
    test_chan_theory()