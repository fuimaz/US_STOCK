"""
比较原始策略和改进的严格策略
"""
import pandas as pd
import numpy as np

def compare_strategies():
    """
    比较原始策略和改进的严格策略
    """
    print("=" * 100)
    print("策略对比分析：原始策略 vs 改进的严格策略")
    print("=" * 100)
    print()
    
    # 读取两个策略的结果
    original_df = pd.read_csv('results/a_stock_daily_boll/summary.csv')
    improved_df = pd.read_csv('results/improved_strict_boll/summary.csv')
    
    # 只比较成功的股票
    original_success = original_df[original_df['status'] == '成功']
    improved_success = improved_df[improved_df['status'] == '成功']
    
    print(f"原始策略成功回测: {len(original_success)} 只股票")
    print(f"改进策略成功回测: {len(improved_success)} 只股票")
    print()
    
    # 计算平均指标
    print("=" * 100)
    print("平均表现对比")
    print("=" * 100)
    print()
    
    metrics = {
        '策略总收益': 'total_return',
        '年化收益': 'annualized_return',
        '夏普比率': 'sharpe_ratio',
        '最大回撤': 'max_drawdown',
        '胜率': 'win_rate',
        '交易次数': 'total_trades',
        '买入持有收益': 'buy_hold_return',
        '超额收益': 'excess_return',
    }
    
    print(f"{'指标':<15} {'原始策略':<20} {'改进策略':<20} {'差异':<20} {'改进幅度':<15}")
    print("-" * 100)
    
    for metric_name, metric_col in metrics.items():
        original_mean = original_success[metric_col].mean()
        improved_mean = improved_success[metric_col].mean()
        diff = improved_mean - original_mean
        
        if original_mean != 0:
            improvement_pct = (diff / abs(original_mean)) * 100
        else:
            improvement_pct = 0
        
        print(f"{metric_name:<15} {original_mean:<20.2f} {improved_mean:<20.2f} {diff:<20.2f} {improvement_pct:<15.2f}%")
    
    print()
    
    # 统计有交易的股票
    print("=" * 100)
    print("交易活跃度对比")
    print("=" * 100)
    print()
    
    original_with_trades = original_success[original_success['total_trades'] > 0]
    improved_with_trades = improved_success[improved_success['total_trades'] > 0]
    
    print(f"原始策略有交易的股票: {len(original_with_trades)}/{len(original_success)} ({len(original_with_trades)/len(original_success)*100:.1f}%)")
    print(f"改进策略有交易的股票: {len(improved_with_trades)}/{len(improved_success)} ({len(improved_with_trades)/len(improved_success)*100:.1f}%)")
    print()
    
    print(f"原始策略平均交易次数: {original_success['total_trades'].mean():.2f}")
    print(f"改进策略平均交易次数: {improved_success['total_trades'].mean():.2f}")
    print()
    
    # 统计超额收益为正的股票
    print("=" * 100)
    print("超额收益分析")
    print("=" * 100)
    print()
    
    original_positive_excess = original_success[original_success['excess_return'] > 0]
    improved_positive_excess = improved_success[improved_success['excess_return'] > 0]
    
    print(f"原始策略超额收益为正: {len(original_positive_excess)}/{len(original_success)} ({len(original_positive_excess)/len(original_success)*100:.1f}%)")
    print(f"改进策略超额收益为正: {len(improved_positive_excess)}/{len(improved_success)} ({len(improved_positive_excess)/len(improved_success)*100:.1f}%)")
    print()
    
    if len(original_positive_excess) > 0:
        print(f"原始策略平均超额收益（正收益）: {original_positive_excess['excess_return'].mean():.2f}%")
    if len(improved_positive_excess) > 0:
        print(f"改进策略平均超额收益（正收益）: {improved_positive_excess['excess_return'].mean():.2f}%")
    print()
    
    # 找出在两个策略中表现都很好的股票
    print("=" * 100)
    print("策略表现对比")
    print("=" * 100)
    print()
    
    # 合并两个策略的结果
    merged_df = pd.merge(
        original_success[['symbol', 'total_return', 'excess_return', 'sharpe_ratio', 'win_rate', 'total_trades']],
        improved_success[['symbol', 'total_return', 'excess_return', 'sharpe_ratio', 'win_rate', 'total_trades']],
        on='symbol',
        suffixes=('_original', '_improved')
    )
    
    # 找出改进策略表现更好的股票
    merged_df['excess_improvement'] = merged_df['excess_return_improved'] - merged_df['excess_return_original']
    better_stocks = merged_df[merged_df['excess_improvement'] > 0].sort_values('excess_improvement', ascending=False)
    
    print(f"改进策略超额收益更高的股票: {len(better_stocks)} 只")
    print()
    
    if len(better_stocks) > 0:
        print("改进策略表现最好的10只股票:")
        print(f"{'股票代码':<15} {'原始超额收益':<20} {'改进超额收益':<20} {'提升':<20}")
        print("-" * 75)
        for i, row in enumerate(better_stocks.head(10).itertuples(), 1):
            print(f"{row.symbol:<15} {row.excess_return_original:<20.2f}% {row.excess_return_improved:<20.2f}% {row.excess_improvement:<20.2f}%")
        print()
    
    # 找出原始策略表现更好的股票
    worse_stocks = merged_df[merged_df['excess_improvement'] < 0].sort_values('excess_improvement')
    
    print(f"原始策略超额收益更高的股票: {len(worse_stocks)} 只")
    print()
    
    if len(worse_stocks) > 0:
        print("原始策略表现最好的10只股票:")
        print(f"{'股票代码':<15} {'原始超额收益':<20} {'改进超额收益':<20} {'差异':<20}")
        print("-" * 75)
        for i, row in enumerate(worse_stocks.head(10).itertuples(), 1):
            print(f"{row.symbol:<15} {row.excess_return_original:<20.2f}% {row.excess_return_improved:<20.2f}% {row.excess_improvement:<20.2f}%")
        print()
    
    # 风险收益分析
    print("=" * 100)
    print("风险收益分析")
    print("=" * 100)
    print()
    
    # 计算风险调整收益
    original_sharpe_mean = original_success['sharpe_ratio'].mean()
    improved_sharpe_mean = improved_success['sharpe_ratio'].mean()
    
    original_max_dd_mean = original_success['max_drawdown'].mean()
    improved_max_dd_mean = improved_success['max_drawdown'].mean()
    
    print(f"原始策略平均夏普比率: {original_sharpe_mean:.2f}")
    print(f"改进策略平均夏普比率: {improved_sharpe_mean:.2f}")
    print()
    
    print(f"原始策略平均最大回撤: {original_max_dd_mean:.2f}%")
    print(f"改进策略平均最大回撤: {improved_max_dd_mean:.2f}%")
    print()
    
    # 回撤改善
    dd_improvement = original_max_dd_mean - improved_max_dd_mean
    print(f"最大回撤改善: {dd_improvement:.2f}% ({dd_improvement/original_max_dd_mean*100:.1f}%)")
    print()
    
    # 胜率分析
    print("=" * 100)
    print("胜率分析")
    print("=" * 100)
    print()
    
    original_win_mean = original_success['win_rate'].mean()
    improved_win_mean = improved_success['win_rate'].mean()
    
    print(f"原始策略平均胜率: {original_win_mean:.2f}%")
    print(f"改进策略平均胜率: {improved_win_mean:.2f}%")
    print()
    
    # 只比较有交易的股票
    original_with_trades_win = original_with_trades['win_rate'].mean()
    improved_with_trades_win = improved_with_trades['win_rate'].mean()
    
    print(f"原始策略平均胜率（有交易）: {original_with_trades_win:.2f}%")
    print(f"改进策略平均胜率（有交易）: {improved_with_trades_win:.2f}%")
    print()
    
    # 策略特点总结
    print("=" * 100)
    print("策略特点总结")
    print("=" * 100)
    print()
    
    print("原始策略（Daily Bollinger）:")
    print("  ✓ 交易频繁：平均每只股票100-170次交易")
    print("  ✓ 胜率较高：平均60%左右")
    print("  ✓ 收益较高：但超额收益多为负")
    print("  ✓ 回撤较大：平均60-80%")
    print("  ✓ 适合：波动性大、趋势明显的股票")
    print()
    
    print("改进策略（Strict Bollinger）:")
    print("  ✓ 交易稀少：平均每只股票2次交易")
    print("  ✓ 胜率较低：平均20%左右（但有交易时可达50-100%）")
    print("  ✓ 收益较低：但超额收益有改善")
    print("  ✓ 回撤较小：平均10%左右")
    print("  ✓ 适合：稳健型、追求低风险的投资者")
    print()
    
    print("关键差异:")
    print(f"  1. 交易频率：改进策略减少了 {((original_success['total_trades'].mean() - improved_success['total_trades'].mean()) / original_success['total_trades'].mean() * 100):.1f}% 的交易")
    print(f"  2. 最大回撤：改进策略降低了 {((original_max_dd_mean - improved_max_dd_mean) / original_max_dd_mean * 100):.1f}% 的回撤")
    print(f"  3. 超额收益：改进策略超额收益为正的比例从 {len(original_positive_excess)/len(original_success)*100:.1f}% 提升到 {len(improved_positive_excess)/len(improved_success)*100:.1f}%")
    print()
    
    print("=" * 100)
    print("对比分析完成")
    print("=" * 100)

if __name__ == '__main__':
    compare_strategies()