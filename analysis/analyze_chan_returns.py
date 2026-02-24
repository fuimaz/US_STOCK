"""
分析缠论买卖点的收益
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from chan_theory_v5 import ChanTheory
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def analyze_chan_returns():
    """
    分析缠论买卖点的收益
    """
    print("=" * 100)
    print("缠论买卖点收益分析")
    print("=" * 100)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/chan_returns'
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
    
    # 选择股票进行分析
    symbol = '601186.SS'  # 中国铁建
    
    print(f"正在分析股票: {symbol}")
    print("-" * 100)
    
    # 获取数据
    data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
    
    if data is None or len(data) == 0:
        print("✗ 未获取到数据")
        return
    
    print(f"✓ 数据获取完成，共 {len(data)} 条记录")
    print(f"  时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    print()
    
    # 初始化缠论指标
    chan = ChanTheory(k_type='day')
    
    # 完整分析
    result = chan.analyze(data)
    
    # 统计买卖点
    buy_points = chan.buy_points
    sell_points = chan.sell_points
    
    print(f"✓ 缠论分析完成")
    print(f"  买点数量: {len(buy_points)}")
    print(f"  卖点数量: {len(sell_points)}")
    print()
    
    # 计算收益
    trades = []
    total_return = 0
    win_count = 0
    loss_count = 0
    
    print("交易详情:")
    print("-" * 100)
    print(f"{'序号':<6} {'买入日期':<12} {'买入价格':<10} {'卖出日期':<12} {'卖出价格':<10} {'收益率':<10} {'持仓天数':<10}")
    print("-" * 100)
    
    for i, buy_point in enumerate(buy_points):
        buy_date = buy_point['index']
        buy_price = buy_point['price']
        
        # 找到下一个卖点
        sell_price = None
        sell_date = None
        holding_days = None
        
        for sell_point in sell_points:
            if sell_point['index'] > buy_date:
                sell_date = sell_point['index']
                sell_price = sell_point['price']
                break
        
        # 如果没有卖点，使用最后一个价格
        if sell_price is None:
            sell_date = data.index[-1]
            sell_price = data['Close'].iloc[-1]
        
        # 计算收益率
        return_pct = (sell_price - buy_price) / buy_price * 100
        
        # 计算持仓天数
        holding_days = (sell_date - buy_date).days
        
        # 记录交易
        trades.append({
            'buy_date': buy_date,
            'buy_price': buy_price,
            'sell_date': sell_date,
            'sell_price': sell_price,
            'return_pct': return_pct,
            'holding_days': holding_days
        })
        
        # 统计
        total_return += return_pct
        if return_pct > 0:
            win_count += 1
        else:
            loss_count += 1
        
        # 打印交易详情
        print(f"{i+1:<6} {buy_date.strftime('%Y-%m-%d'):<12} {buy_price:<10.2f} {sell_date.strftime('%Y-%m-%d'):<12} {sell_price:<10.2f} {return_pct:<10.2f}% {holding_days:<10}")
    
    print("-" * 100)
    
    # 计算统计指标
    avg_return = total_return / len(trades) if len(trades) > 0 else 0
    win_rate = win_count / len(trades) * 100 if len(trades) > 0 else 0
    avg_holding_days = sum(t['holding_days'] for t in trades) / len(trades) if len(trades) > 0 else 0
    
    # 计算买入持有收益
    buy_hold_return = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0] * 100
    
    # 计算累计收益
    cumulative_return = 1.0
    for trade in trades:
        cumulative_return *= (1 + trade['return_pct'] / 100)
    cumulative_return_pct = (cumulative_return - 1) * 100
    
    print(f"\n统计指标:")
    print("-" * 100)
    print(f"交易次数: {len(trades)}")
    print(f"平均收益率: {avg_return:.2f}%")
    print(f"累计收益率: {cumulative_return_pct:.2f}%")
    print(f"胜率: {win_rate:.2f}%")
    print(f"盈利次数: {win_count}")
    print(f"亏损次数: {loss_count}")
    print(f"平均持仓天数: {avg_holding_days:.1f}天")
    print(f"买入持有收益: {buy_hold_return:.2f}%")
    print(f"超额收益: {cumulative_return_pct - buy_hold_return:.2f}%")
    print()
    
    # 计算最大回撤
    if len(trades) > 0:
        max_drawdown = 0
        peak = 0
        for trade in trades:
            if trade['return_pct'] > peak:
                peak = trade['return_pct']
            drawdown = peak - trade['return_pct']
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        print(f"最大回撤: {max_drawdown:.2f}%")
    
    print()
    print("=" * 100)
    print("分析完成！")
    print("=" * 100)
    
    # 可视化
    visualize_chan_returns(symbol, data, trades, buy_hold_return, output_dir)
    
    # 保存结果
    save_results(symbol, trades, output_dir)

def visualize_chan_returns(symbol, data, trades, buy_hold_return, output_dir):
    """
    可视化缠论买卖点收益
    """
    print(f"\n正在生成 {symbol} 的收益可视化图表...")
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建图表
    fig, axes = plt.subplots(3, 1, figsize=(16, 18), sharex=True)
    fig.suptitle(f'{symbol} - 缠论买卖点收益分析', fontsize=16, fontweight='bold')
    
    # 1. 价格走势与买卖点
    ax1 = axes[0]
    ax1.plot(data.index, data['Close'], label='收盘价', linewidth=1.5, alpha=0.8)
    
    # 标记买点
    for trade in trades:
        ax1.scatter(trade['buy_date'], trade['buy_price'], color='red', marker='^', s=300, 
                   label='买点' if trade == trades[0] else '', 
                   zorder=5, edgecolors='black', linewidths=2)
        ax1.scatter(trade['sell_date'], trade['sell_price'], color='green', marker='v', s=300, 
                   label='卖点' if trade == trades[0] else '', 
                   zorder=5, edgecolors='black', linewidths=2)
        
        # 绘制交易线
        ax1.plot([trade['buy_date'], trade['sell_date']], 
                [trade['buy_price'], trade['sell_price']], 
                color='blue', linewidth=2, alpha=0.6, linestyle='--')
    
    ax1.set_ylabel('价格', fontsize=12)
    ax1.set_title('价格走势与买卖点', fontsize=14)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 2. 收益率曲线
    ax2 = axes[1]
    
    # 计算累计收益
    cumulative_returns = []
    cumulative_return = 0
    buy_hold_returns = []
    buy_hold_return_val = 0
    
    for i, trade in enumerate(trades):
        cumulative_return += trade['return_pct']
        cumulative_returns.append(cumulative_return)
        
        # 计算买入持有收益
        buy_idx = data.index.get_loc(trade['buy_date'])
        sell_idx = data.index.get_loc(trade['sell_date'])
        buy_hold = (data['Close'].iloc[sell_idx] - data['Close'].iloc[buy_idx]) / data['Close'].iloc[buy_idx] * 100
        buy_hold_returns.append(buy_hold)
    
    x = range(1, len(trades) + 1)
    ax2.plot(x, cumulative_returns, marker='o', label='缠论累计收益', linewidth=2, markersize=8)
    ax2.plot(x, buy_hold_returns, marker='s', label='买入持有收益', linewidth=2, markersize=8, alpha=0.7)
    
    # 添加收益标签
    for i, (cr, bhr) in enumerate(zip(cumulative_returns, buy_hold_returns)):
        ax2.annotate(f'{cr:.1f}%', (i+1, cr), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
        ax2.annotate(f'{bhr:.1f}%', (i+1, bhr), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=8)
    
    ax2.set_ylabel('累计收益率 (%)', fontsize=12)
    ax2.set_title('累计收益率对比', fontsize=14)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    # 3. 单次交易收益率
    ax3 = axes[2]
    
    returns = [t['return_pct'] for t in trades]
    colors = ['red' if r > 0 else 'green' for r in returns]
    
    bars = ax3.bar(x, returns, color=colors, alpha=0.7, edgecolor='black', linewidth=1)
    
    # 添加收益标签
    for i, (bar, r) in enumerate(zip(bars, returns)):
        height = bar.get_height()
        ax3.annotate(f'{r:.1f}%', 
                    (bar.get_x() + bar.get_width() / 2., height),
                    textcoords="offset points", 
                    xytext=(0, 5 if r > 0 else -15), 
                    ha='center', fontsize=8)
    
    ax3.set_xlabel('交易序号', fontsize=12)
    ax3.set_ylabel('收益率 (%)', fontsize=12)
    ax3.set_title('单次交易收益率', fontsize=14)
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_minor_locator(mdates.MonthLocator([1, 4, 7, 10]))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, f'{symbol}_returns_chart.png')
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 图表已保存到: {chart_file}")

def save_results(symbol, trades, output_dir):
    """
    保存分析结果
    """
    # 创建DataFrame
    df = pd.DataFrame(trades)
    
    # 保存到CSV
    output_file = os.path.join(output_dir, f'{symbol}_trades.csv')
    df.to_csv(output_file, index=False)
    print(f"✓ 交易记录已保存到: {output_file}")
    
    # 保存详细报告
    report_file = os.path.join(output_dir, f'{symbol}_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write(f"{symbol} - 缠论买卖点收益分析报告\n")
        f.write("=" * 100 + "\n\n")
        
        f.write("交易详情:\n")
        f.write("-" * 100 + "\n")
        f.write(f"{'序号':<6} {'买入日期':<12} {'买入价格':<10} {'卖出日期':<12} {'卖出价格':<10} {'收益率':<10} {'持仓天数':<10}\n")
        f.write("-" * 100 + "\n")
        
        for i, trade in enumerate(trades):
            f.write(f"{i+1:<6} {trade['buy_date'].strftime('%Y-%m-%d'):<12} {trade['buy_price']:<10.2f} {trade['sell_date'].strftime('%Y-%m-%d'):<12} {trade['sell_price']:<10.2f} {trade['return_pct']:<10.2f}% {trade['holding_days']:<10}\n")
        
        f.write("-" * 100 + "\n\n")
        
        # 统计指标
        total_return = sum(t['return_pct'] for t in trades)
        avg_return = total_return / len(trades) if len(trades) > 0 else 0
        win_count = sum(1 for t in trades if t['return_pct'] > 0)
        loss_count = sum(1 for t in trades if t['return_pct'] <= 0)
        win_rate = win_count / len(trades) * 100 if len(trades) > 0 else 0
        avg_holding_days = sum(t['holding_days'] for t in trades) / len(trades) if len(trades) > 0 else 0
        
        # 计算累计收益
        cumulative_return = 1.0
        for trade in trades:
            cumulative_return *= (1 + trade['return_pct'] / 100)
        cumulative_return_pct = (cumulative_return - 1) * 100
        
        f.write("统计指标:\n")
        f.write("-" * 100 + "\n")
        f.write(f"交易次数: {len(trades)}\n")
        f.write(f"平均收益率: {avg_return:.2f}%\n")
        f.write(f"累计收益率: {cumulative_return_pct:.2f}%\n")
        f.write(f"胜率: {win_rate:.2f}%\n")
        f.write(f"盈利次数: {win_count}\n")
        f.write(f"亏损次数: {loss_count}\n")
        f.write(f"平均持仓天数: {avg_holding_days:.1f}天\n")
        f.write("-" * 100 + "\n")
    
    print(f"✓ 分析报告已保存到: {report_file}")

if __name__ == '__main__':
    analyze_chan_returns()