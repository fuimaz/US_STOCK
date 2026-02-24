"""
对比分析日K和周K的回测结果
"""
import pandas as pd
import matplotlib.pyplot as plt
import os

def compare_daily_weekly():
    """
    对比分析日K和周K的回测结果
    """
    print("=" * 100)
    print("日K vs 周K 回测结果对比分析")
    print("=" * 100)
    print()
    
    # 读取日K和周K的汇总结果
    daily_summary = pd.read_csv('results/moderate_boll_v4/summary.csv')
    weekly_summary = pd.read_csv('results/moderate_boll_v4_weekly/summary.csv')
    
    # 合并数据
    comparison = daily_summary.merge(weekly_summary, on='symbol', suffixes=('_daily', '_weekly'))
    
    # 打印对比表格
    print(f"{'股票代码':<15} {'日K收益':<15} {'周K收益':<15} {'日K交易':<12} {'周K交易':<12} {'日K胜率':<12} {'周K胜率':<12}")
    print("-" * 100)
    
    for _, row in comparison.iterrows():
        print(f"{row['symbol']:<15} {row['total_return_daily']:<15.2f}% {row['total_return_weekly']:<15.2f}% {row['total_trades_daily']:<12} {row['total_trades_weekly']:<12} {row['win_rate_daily']:<12.2f}% {row['win_rate_weekly']:<12.2f}%")
    
    print()
    
    # 详细对比分析
    print("=" * 100)
    print("详细对比分析")
    print("=" * 100)
    print()
    
    for _, row in comparison.iterrows():
        print(f"股票: {row['symbol']}")
        print("-" * 100)
        print(f"日K:")
        print(f"  策略收益: {row['total_return_daily']:.2f}%")
        print(f"  年化收益: {row['annualized_return_daily']:.2f}%")
        print(f"  超额收益: {row['excess_return_daily']:.2f}%")
        print(f"  胜率: {row['win_rate_daily']:.2f}%")
        print(f"  交易次数: {row['total_trades_daily']}")
        print(f"  最大回撤: {row['max_drawdown_daily']:.2f}%")
        print()
        print(f"周K:")
        print(f"  策略收益: {row['total_return_weekly']:.2f}%")
        print(f"  年化收益: {row['annualized_return_weekly']:.2f}%")
        print(f"  超额收益: {row['excess_return_weekly']:.2f}%")
        print(f"  胜率: {row['win_rate_weekly']:.2f}%")
        print(f"  交易次数: {row['total_trades_weekly']}")
        print(f"  最大回撤: {row['max_drawdown_weekly']:.2f}%")
        print()
        
        # 计算差异
        return_diff = row['total_return_weekly'] - row['total_return_daily']
        trades_diff = row['total_trades_weekly'] - row['total_trades_daily']
        win_rate_diff = row['win_rate_weekly'] - row['win_rate_daily']
        
        print(f"差异分析:")
        print(f"  收益差异: {return_diff:.2f}% (周K {'优于' if return_diff > 0 else '劣于'} 日K)")
        print(f"  交易次数差异: {trades_diff} (周K {'减少' if trades_diff < 0 else '增加'} {abs(trades_diff)} 次)")
        print(f"  胜率差异: {win_rate_diff:.2f}% (周K {'高于' if win_rate_diff > 0 else '低于'} 日K)")
        print()
    
    # 生成对比图表
    create_comparison_charts(comparison)
    
    print("=" * 100)
    print("对比分析完成！")
    print("=" * 100)

def create_comparison_charts(comparison):
    """
    创建对比图表
    """
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('日K vs 周K 回测结果对比', fontsize=16, fontweight='bold')
    
    symbols = comparison['symbol'].tolist()
    
    # 1. 策略收益对比
    ax1 = axes[0, 0]
    x = range(len(symbols))
    width = 0.35
    
    ax1.bar([i - width/2 for i in x], comparison['total_return_daily'], width, label='日K', alpha=0.8)
    ax1.bar([i + width/2 for i in x], comparison['total_return_weekly'], width, label='周K', alpha=0.8)
    
    ax1.set_xlabel('股票代码', fontsize=12)
    ax1.set_ylabel('策略收益 (%)', fontsize=12)
    ax1.set_title('策略收益对比', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(symbols)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 2. 交易次数对比
    ax2 = axes[0, 1]
    ax2.bar([i - width/2 for i in x], comparison['total_trades_daily'], width, label='日K', alpha=0.8)
    ax2.bar([i + width/2 for i in x], comparison['total_trades_weekly'], width, label='周K', alpha=0.8)
    
    ax2.set_xlabel('股票代码', fontsize=12)
    ax2.set_ylabel('交易次数', fontsize=12)
    ax2.set_title('交易次数对比', fontsize=14)
    ax2.set_xticks(x)
    ax2.set_xticklabels(symbols)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 胜率对比
    ax3 = axes[1, 0]
    ax3.bar([i - width/2 for i in x], comparison['win_rate_daily'], width, label='日K', alpha=0.8)
    ax3.bar([i + width/2 for i in x], comparison['win_rate_weekly'], width, label='周K', alpha=0.8)
    
    ax3.set_xlabel('股票代码', fontsize=12)
    ax3.set_ylabel('胜率 (%)', fontsize=12)
    ax3.set_title('胜率对比', fontsize=14)
    ax3.set_xticks(x)
    ax3.set_xticklabels(symbols)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 最大回撤对比
    ax4 = axes[1, 1]
    ax4.bar([i - width/2 for i in x], comparison['max_drawdown_daily'], width, label='日K', alpha=0.8)
    ax4.bar([i + width/2 for i in x], comparison['max_drawdown_weekly'], width, label='周K', alpha=0.8)
    
    ax4.set_xlabel('股票代码', fontsize=12)
    ax4.set_ylabel('最大回撤 (%)', fontsize=12)
    ax4.set_title('最大回撤对比', fontsize=14)
    ax4.set_xticks(x)
    ax4.set_xticklabels(symbols)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    output_dir = 'results/comparison'
    os.makedirs(output_dir, exist_ok=True)
    chart_file = os.path.join(output_dir, 'daily_vs_weekly_comparison.png')
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 对比图表已保存到: {chart_file}")
    print()

if __name__ == '__main__':
    compare_daily_weekly()