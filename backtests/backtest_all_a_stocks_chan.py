"""
对所有A股数据进行缠论回测
"""
import pandas as pd
import numpy as np
import os
from chan_theory_v5 import ChanTheory
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

def get_all_a_stock_files():
    """
    获取所有A股数据文件
    
    Returns:
        A股数据文件列表
    """
    cache_dir = 'data_cache'
    a_stock_files = []
    
    if not os.path.exists(cache_dir):
        return a_stock_files
    
    for filename in os.listdir(cache_dir):
        # 沪市：600xxx.SS, 601xxx.SS, 603xxx.SS
        # 深市：000xxx.SZ, 002xxx.SZ, 300xxx.SZ
        if (filename.endswith('.csv') and 
            ('.SS' in filename or '.SZ' in filename) and
            '_20y_1d_forward.csv' in filename):
            a_stock_files.append(os.path.join(cache_dir, filename))
    
    return sorted(a_stock_files)

def backtest_chan_theory_on_stock(data, symbol):
    """
    对单只股票进行缠论回测
    
    Args:
        data: 股票数据
        symbol: 股票代码
    
    Returns:
        回测结果字典
    """
    # 初始化缠论指标
    chan = ChanTheory(k_type='day')
    
    # 完整分析
    result = chan.analyze(data)
    
    # 统计买卖点
    buy_points = chan.buy_points
    sell_points = chan.sell_points
    
    # 计算收益
    trades = []
    total_return = 0
    win_count = 0
    loss_count = 0
    
    for buy_point in buy_points:
        buy_date = buy_point['index']
        buy_price = buy_point['price']
        
        # 找到下一个卖点
        sell_price = None
        sell_date = None
        
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
    
    # 计算统计指标
    trade_count = len(trades)
    avg_return = total_return / trade_count if trade_count > 0 else 0
    win_rate = win_count / trade_count * 100 if trade_count > 0 else 0
    avg_holding_days = sum(t['holding_days'] for t in trades) / trade_count if trade_count > 0 else 0
    
    # 计算买入持有收益
    buy_hold_return = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0] * 100
    
    # 计算累计收益
    cumulative_return = 1.0
    for trade in trades:
        cumulative_return *= (1 + trade['return_pct'] / 100)
    cumulative_return_pct = (cumulative_return - 1) * 100
    
    # 计算最大回撤
    max_drawdown = 0
    if len(trades) > 0:
        peak = 0
        for trade in trades:
            if trade['return_pct'] > peak:
                peak = trade['return_pct']
            drawdown = peak - trade['return_pct']
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    return {
        'symbol': symbol,
        'trade_count': trade_count,
        'avg_return': avg_return,
        'cumulative_return': cumulative_return_pct,
        'win_rate': win_rate,
        'win_count': win_count,
        'loss_count': loss_count,
        'avg_holding_days': avg_holding_days,
        'buy_hold_return': buy_hold_return,
        'excess_return': cumulative_return_pct - buy_hold_return,
        'max_drawdown': max_drawdown,
        'trades': trades
    }

def backtest_all_a_stocks():
    """
    对所有A股进行缠论回测
    """
    print("=" * 100)
    print("对所有A股进行缠论回测")
    print("=" * 100)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/chan_backtest_all'
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ 结果将保存到: {output_dir}/")
    print()
    
    # 获取所有A股数据文件
    a_stock_files = get_all_a_stock_files()
    print(f"✓ 找到 {len(a_stock_files)} 个A股数据文件")
    print()
    
    # 回测所有股票
    all_results = []
    success_count = 0
    fail_count = 0
    
    for i, filepath in enumerate(a_stock_files):
        # 提取股票代码
        filename = os.path.basename(filepath)
        symbol = filename.split('_')[0]
        
        print(f"[{i+1}/{len(a_stock_files)}] 正在回测 {symbol}...")
        
        try:
            # 读取数据
            data = pd.read_csv(filepath, index_col='datetime', parse_dates=True)
            
            if len(data) < 100:
                print(f"  ✗ 数据量不足（{len(data)}条），跳过")
                fail_count += 1
                continue
            
            # 回测
            result = backtest_chan_theory_on_stock(data, symbol)
            all_results.append(result)
            success_count += 1
            
            print(f"  ✓ 交易次数: {result['trade_count']}, 累计收益: {result['cumulative_return']:.2f}%, 胜率: {result['win_rate']:.2f}%")
            
        except Exception as e:
            print(f"  ✗ 回测失败: {e}")
            fail_count += 1
    
    print()
    print("=" * 100)
    print(f"回测完成！成功: {success_count}, 失败: {fail_count}")
    print("=" * 100)
    print()
    
    # 汇总结果
    summarize_results(all_results, output_dir)

def summarize_results(all_results, output_dir):
    """
    汇总所有股票的回测结果
    """
    print("正在汇总结果...")
    print()
    
    # 创建DataFrame
    df = pd.DataFrame([{
        '股票代码': r['symbol'],
        '交易次数': r['trade_count'],
        '平均收益率': r['avg_return'],
        '累计收益率': r['cumulative_return'],
        '胜率': r['win_rate'],
        '盈利次数': r['win_count'],
        '亏损次数': r['loss_count'],
        '平均持仓天数': r['avg_holding_days'],
        '买入持有收益': r['buy_hold_return'],
        '超额收益': r['excess_return'],
        '最大回撤': r['max_drawdown']
    } for r in all_results])
    
    # 保存到CSV
    output_file = os.path.join(output_dir, 'all_a_stocks_backtest.csv')
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✓ 结果已保存到: {output_file}")
    
    # 如果没有结果，直接返回
    if len(df) == 0:
        print("\n没有可用的回测结果")
        return
    
    # 统计汇总
    print()
    print("=" * 100)
    print("统计汇总")
    print("=" * 100)
    
    # 只统计有交易的股票
    df_with_trades = df[df['交易次数'] > 0]
    
    print(f"\n有交易的股票数量: {len(df_with_trades)}")
    print(f"平均交易次数: {df_with_trades['交易次数'].mean():.2f}")
    print(f"平均累计收益率: {df_with_trades['累计收益率'].mean():.2f}%")
    print(f"平均胜率: {df_with_trades['胜率'].mean():.2f}%")
    print(f"平均超额收益: {df_with_trades['超额收益'].mean():.2f}%")
    print(f"平均最大回撤: {df_with_trades['最大回撤'].mean():.2f}%")
    
    # 胜率统计
    print(f"\n胜率 > 50%的股票: {len(df_with_trades[df_with_trades['胜率'] > 50])}")
    print(f"胜率 > 70%的股票: {len(df_with_trades[df_with_trades['胜率'] > 70])}")
    print(f"胜率 > 80%的股票: {len(df_with_trades[df_with_trades['胜率'] > 80])}")
    
    # 收益统计
    print(f"\n累计收益 > 0的股票: {len(df_with_trades[df_with_trades['累计收益率'] > 0])}")
    print(f"累计收益 > 10%的股票: {len(df_with_trades[df_with_trades['累计收益率'] > 10])}")
    print(f"累计收益 > 20%的股票: {len(df_with_trades[df_with_trades['累计收益率'] > 20])}")
    
    # 超额收益统计
    print(f"\n超额收益 > 0的股票: {len(df_with_trades[df_with_trades['超额收益'] > 0])}")
    print(f"超额收益 > 10%的股票: {len(df_with_trades[df_with_trades['超额收益'] > 10])}")
    print(f"超额收益 > 20%的股票: {len(df_with_trades[df_with_trades['超额收益'] > 20])}")
    
    # 排序并显示Top 10
    print()
    print("=" * 100)
    print("Top 10 - 按累计收益率排序")
    print("=" * 100)
    top10_by_return = df_with_trades.nlargest(10, '累计收益率')
    print(top10_by_return[['股票代码', '交易次数', '累计收益率', '胜率', '超额收益']].to_string(index=False))
    
    print()
    print("=" * 100)
    print("Top 10 - 按胜率排序（至少3次交易）")
    print("=" * 100)
    top10_by_winrate = df_with_trades[df_with_trades['交易次数'] >= 3].nlargest(10, '胜率')
    print(top10_by_winrate[['股票代码', '交易次数', '累计收益率', '胜率', '超额收益']].to_string(index=False))
    
    print()
    print("=" * 100)
    print("Top 10 - 按超额收益排序")
    print("=" * 100)
    top10_by_excess = df_with_trades.nlargest(10, '超额收益')
    print(top10_by_excess[['股票代码', '交易次数', '累计收益率', '胜率', '超额收益']].to_string(index=False))
    
    # 可视化
    visualize_results(df_with_trades, output_dir)
    
    # 保存详细报告
    save_detailed_report(df_with_trades, output_dir)

def visualize_results(df, output_dir):
    """
    可视化回测结果
    """
    print(f"\n正在生成可视化图表...")
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('A股缠论回测结果汇总', fontsize=16, fontweight='bold')
    
    # 1. 累计收益率分布
    ax1 = axes[0, 0]
    ax1.hist(df['累计收益率'], bins=30, edgecolor='black', alpha=0.7)
    ax1.axvline(x=0, color='red', linestyle='--', linewidth=2, label='盈亏平衡线')
    ax1.set_xlabel('累计收益率 (%)', fontsize=12)
    ax1.set_ylabel('股票数量', fontsize=12)
    ax1.set_title('累计收益率分布', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 胜率分布
    ax2 = axes[0, 1]
    ax2.hist(df['胜率'], bins=30, edgecolor='black', alpha=0.7)
    ax2.axvline(x=50, color='red', linestyle='--', linewidth=2, label='50%胜率线')
    ax2.set_xlabel('胜率 (%)', fontsize=12)
    ax2.set_ylabel('股票数量', fontsize=12)
    ax2.set_title('胜率分布', fontsize=14)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 累计收益率 vs 胜率散点图
    ax3 = axes[1, 0]
    scatter = ax3.scatter(df['胜率'], df['累计收益率'], c=df['超额收益'], 
                         cmap='RdYlGn', s=100, alpha=0.6, edgecolors='black', linewidths=1)
    ax3.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax3.axvline(x=50, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax3.set_xlabel('胜率 (%)', fontsize=12)
    ax3.set_ylabel('累计收益率 (%)', fontsize=12)
    ax3.set_title('累计收益率 vs 胜率', fontsize=14)
    ax3.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax3, label='超额收益 (%)')
    
    # 4. 超额收益分布
    ax4 = axes[1, 1]
    ax4.hist(df['超额收益'], bins=30, edgecolor='black', alpha=0.7)
    ax4.axvline(x=0, color='red', linestyle='--', linewidth=2, label='盈亏平衡线')
    ax4.set_xlabel('超额收益 (%)', fontsize=12)
    ax4.set_ylabel('股票数量', fontsize=12)
    ax4.set_title('超额收益分布', fontsize=14)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, 'all_a_stocks_summary.png')
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 图表已保存到: {chart_file}")

def save_detailed_report(df, output_dir):
    """
    保存详细报告
    """
    report_file = os.path.join(output_dir, 'detailed_report.txt')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("A股缠论回测详细报告\n")
        f.write("=" * 100 + "\n\n")
        
        f.write(f"回测股票数量: {len(df)}\n\n")
        
        f.write("统计汇总:\n")
        f.write("-" * 100 + "\n")
        f.write(f"平均交易次数: {df['交易次数'].mean():.2f}\n")
        f.write(f"平均累计收益率: {df['累计收益率'].mean():.2f}%\n")
        f.write(f"平均胜率: {df['胜率'].mean():.2f}%\n")
        f.write(f"平均超额收益: {df['超额收益'].mean():.2f}%\n")
        f.write(f"平均最大回撤: {df['最大回撤'].mean():.2f}%\n\n")
        
        f.write("胜率统计:\n")
        f.write("-" * 100 + "\n")
        f.write(f"胜率 > 50%的股票: {len(df[df['胜率'] > 50])}\n")
        f.write(f"胜率 > 70%的股票: {len(df[df['胜率'] > 70])}\n")
        f.write(f"胜率 > 80%的股票: {len(df[df['胜率'] > 80])}\n\n")
        
        f.write("收益统计:\n")
        f.write("-" * 100 + "\n")
        f.write(f"累计收益 > 0的股票: {len(df[df['累计收益率'] > 0])}\n")
        f.write(f"累计收益 > 10%的股票: {len(df[df['累计收益率'] > 10])}\n")
        f.write(f"累计收益 > 20%的股票: {len(df[df['累计收益率'] > 20])}\n\n")
        
        f.write("超额收益统计:\n")
        f.write("-" * 100 + "\n")
        f.write(f"超额收益 > 0的股票: {len(df[df['超额收益'] > 0])}\n")
        f.write(f"超额收益 > 10%的股票: {len(df[df['超额收益'] > 10])}\n")
        f.write(f"超额收益 > 20%的股票: {len(df[df['超额收益'] > 20])}\n\n")
        
        f.write("Top 10 - 按累计收益率排序:\n")
        f.write("-" * 100 + "\n")
        top10_by_return = df.nlargest(10, '累计收益率')
        f.write(top10_by_return[['股票代码', '交易次数', '累计收益率', '胜率', '超额收益']].to_string(index=False))
        f.write("\n\n")
        
        f.write("Top 10 - 按胜率排序（至少3次交易）:\n")
        f.write("-" * 100 + "\n")
        top10_by_winrate = df[df['交易次数'] >= 3].nlargest(10, '胜率')
        f.write(top10_by_winrate[['股票代码', '交易次数', '累计收益率', '胜率', '超额收益']].to_string(index=False))
        f.write("\n\n")
        
        f.write("Top 10 - 按超额收益排序:\n")
        f.write("-" * 100 + "\n")
        top10_by_excess = df.nlargest(10, '超额收益')
        f.write(top10_by_excess[['股票代码', '交易次数', '累计收益率', '胜率', '超额收益']].to_string(index=False))
        f.write("\n\n")
        
        f.write("所有股票详细结果:\n")
        f.write("-" * 100 + "\n")
        f.write(df.to_string(index=False))
    
    print(f"✓ 详细报告已保存到: {report_file}")

if __name__ == '__main__':
    backtest_all_a_stocks()