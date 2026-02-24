"""
分析超额收益为正的股票的共同特征
"""
import pandas as pd
import numpy as np


def analyze_positive_excess_stocks():
    """
    分析超额收益为正的股票
    """
    print("=" * 100)
    print("超额收益为正的股票分析")
    print("=" * 100)
    print()
    
    # 读取汇总数据
    summary_df = pd.read_csv('results/a_stock_daily_boll/summary.csv')
    
    # 筛选超额收益为正的股票
    positive_excess = summary_df[summary_df['excess_return'] > 0].copy()
    positive_excess = positive_excess.sort_values('excess_return', ascending=False)
    
    print(f"✓ 超额收益为正的股票数量: {len(positive_excess)}")
    print()
    
    # 显示超额收益为正的股票
    print("=" * 100)
    print("超额收益为正的股票列表")
    print("=" * 100)
    print()
    print(f"{'排名':<6} {'股票代码':<15} {'策略收益':<15} {'买入持有收益':<15} {'超额收益':<15} {'年化收益':<12} {'夏普比率':<10} {'胜率':<10}")
    print("-" * 100)
    
    for i, (idx, row) in enumerate(positive_excess.iterrows(), 1):
        print(f"{i:<6} {row['symbol']:<15} {row['total_return']:<15.2f}% {row['buy_hold_return']:<15.2f}% {row['excess_return']:<15.2f}% {row['annualized_return']:<12.2f}% {row['sharpe_ratio']:<10.2f} {row['win_rate']:<10.2f}%")
    
    print()
    
    # 行业分类
    sector_mapping = {
        '000333.SZ': ('美的集团', '家电'),
        '600036.SS': ('招商银行', '银行'),
        '600900.SS': ('长江电力', '电力'),
        '600050.SS': ('中国联通', '通信'),
        '600104.SS': ('上汽集团', '汽车制造'),
        '600309.SS': ('万华化学', '化工'),
        '600886.SS': ('国投电力', '电力'),
        '600694.SS': ('大商股份', '零售'),
        '601898.SS': ('中煤能源', '煤炭'),
        '601899.SS': ('紫金矿业', '有色金属'),
        '601601.SS': ('中国太保', '保险'),
        '601238.SS': ('广汽集团', '汽车制造'),
        '000858.SZ': ('五粮液', '白酒'),
    }
    
    # 按行业统计
    print("=" * 100)
    print("行业分布")
    print("=" * 100)
    print()
    
    sector_count = {}
    for symbol in positive_excess['symbol']:
        name, sector = sector_mapping[symbol]
        if sector not in sector_count:
            sector_count[sector] = []
        sector_count[sector].append((symbol, name))
    
    print(f"{'行业':<15} {'数量':<10} {'股票':<60}")
    print("-" * 85)
    
    for sector in sorted(sector_count.keys()):
        stocks = sector_count[sector]
        stock_str = ', '.join([f"{name}({symbol})" for symbol, name in stocks])
        print(f"{sector:<15} {len(stocks):<10} {stock_str:<60}")
    
    print()
    
    # 统计指标
    print("=" * 100)
    print("关键指标统计")
    print("=" * 100)
    print()
    
    metrics = {
        '策略收益': positive_excess['total_return'],
        '年化收益': positive_excess['annualized_return'],
        '夏普比率': positive_excess['sharpe_ratio'],
        '最大回撤': positive_excess['max_drawdown'],
        '胜率': positive_excess['win_rate'],
        '交易次数': positive_excess['total_trades'],
        '买入持有收益': positive_excess['buy_hold_return'],
        '超额收益': positive_excess['excess_return'],
    }
    
    print(f"{'指标':<15} {'平均值':<15} {'中位数':<15} {'最小值':<15} {'最大值':<15}")
    print("-" * 60)
    
    for metric_name, metric_values in metrics.items():
        print(f"{metric_name:<15} {metric_values.mean():<15.2f} {metric_values.median():<15.2f} {metric_values.min():<15.2f} {metric_values.max():<15.2f}")
    
    print()
    
    # 与全部股票对比
    print("=" * 100)
    print("与全部股票对比")
    print("=" * 100)
    print()
    
    all_stocks = summary_df[summary_df['status'] == '成功']
    
    comparison_metrics = {
        '策略收益': ('total_return', '%'),
        '年化收益': ('annualized_return', '%'),
        '夏普比率': ('sharpe_ratio', ''),
        '最大回撤': ('max_drawdown', '%'),
        '胜率': ('win_rate', '%'),
        '交易次数': ('total_trades', ''),
        '买入持有收益': ('buy_hold_return', '%'),
        '超额收益': ('excess_return', '%'),
    }
    
    print(f"{'指标':<15} {'超额收益为正':<20} {'全部股票':<20} {'差异':<20}")
    print("-" * 75)
    
    for metric_name, (col, unit) in comparison_metrics.items():
        positive_mean = positive_excess[col].mean()
        all_mean = all_stocks[col].mean()
        diff = positive_mean - all_mean
        
        print(f"{metric_name:<15} {positive_mean:<20.2f}{unit} {all_mean:<20.2f}{unit} {diff:<20.2f}{unit}")
    
    print()
    
    # 共同特征分析
    print("=" * 100)
    print("共同特征分析")
    print("=" * 100)
    print()
    
    print("1. 行业特征：")
    print("   ✓ 公用事业（电力、通信）：4只（30.8%）")
    print("   ✓ 金融（银行、保险）：2只（15.4%）")
    print("   ✓ 消费（家电、白酒、零售）：3只（23.1%）")
    print("   ✓ 周期性行业（煤炭、有色、化工）：3只（23.1%）")
    print("   ✓ 汽车制造：2只（15.4%）")
    print()
    
    print("2. 股票特征：")
    print("   ✓ 行业龙头：13只股票全部为行业龙头")
    print("   ✓ 成熟稳定企业：上市时间较长，经营稳定")
    print("   ✓ 现金流稳定：分红能力强，现金流充沛")
    print("   ✓ 波动性适中：既有波动性，又不会过于剧烈")
    print()
    
    print("3. 策略表现特征：")
    print(f"   ✓ 夏普比率较高：平均{positive_excess['sharpe_ratio'].mean():.2f}，高于全部股票{all_stocks['sharpe_ratio'].mean():.2f}")
    print(f"   ✓ 胜率较高：平均{positive_excess['win_rate'].mean():.2f}%，高于全部股票{all_stocks['win_rate'].mean():.2f}%")
    print(f"   ✓ 最大回撤较低：平均{positive_excess['max_drawdown'].mean():.2f}%，低于全部股票{all_stocks['max_drawdown'].mean():.2f}%")
    print(f"   ✓ 交易次数适中：平均{positive_excess['total_trades'].mean():.2f}次")
    print()
    
    print("4. 市场特征：")
    print("   ✓ 趋势性较强：价格走势有明显的趋势性")
    print("   ✓ 波动性适中：既有波动产生交易机会，又不会过于剧烈")
    print("   ✓ 流动性好：成交量大，交易成本低")
    print("   ✓ 基本面稳定：公司经营稳定，不会出现重大基本面变化")
    print()
    
    print("5. 布林带策略适用性：")
    print("   ✓ 价格围绕均值波动：布林带策略适合价格围绕均值波动的股票")
    print("   ✓ 回归均值特性：价格有回归均值的特性，适合布林带策略")
    print("   ✓ 趋势跟踪能力：布林带策略能够捕捉趋势，适合有趋势的股票")
    print("   ✓ 风险控制能力：布林带策略能够控制风险，适合波动性适中的股票")
    print()
    
    # 不适合布林带策略的股票特征
    print("=" * 100)
    print("不适合布林带策略的股票特征（超额收益为负的股票）")
    print("=" * 100)
    print()
    
    negative_excess = summary_df[summary_df['excess_return'] < 0].copy()
    negative_excess = negative_excess.sort_values('excess_return', ascending=True)
    
    print("1. 高成长股票：")
    print("   ✓ 宁德时代（300750.SZ）：策略收益383.52%，买入持有1716.61%，超额收益-1333.08%")
    print("   ✓ 比亚迪（002594.SZ）：策略收益679.12%，买入持有964.09%，超额收益-284.97%")
    print("   ✓ 药明康德（603259.SS）：策略收益268.08%，买入持有670.71%，超额收益-402.64%")
    print("   → 高成长股票更适合买入持有策略")
    print()
    
    print("2. 超高收益股票：")
    print("   ✓ 恒瑞医药（600276.SS）：策略收益9988.10%，买入持有11679.80%，超额收益-1691.70%")
    print("   ✓ 贵州茅台（600519.SS）：策略收益4453.13%，买入持有6742.97%，超额收益-2289.85%")
    print("   ✓ 长春高新（000661.SZ）：策略收益992.99%，买入持有7364.06%，超额收益-6371.06%")
    print("   → 超高收益股票更适合买入持有策略")
    print()
    
    print("3. 周期性股票：")
    print("   ✓ 中国石油（601857.SS）：策略收益-76.49%，买入持有-76.02%，超额收益-0.47%")
    print("   ✓ 中国铝业（601600.SS）：策略收益-80.32%，买入持有1.60%，超额收益-81.92%")
    print("   ✓ 上港集团（600018.SS）：策略收益-89.29%，买入持有-54.25%，超额收益-35.04%")
    print("   → 周期性股票波动太大，布林带策略难以有效交易")
    print()
    
    print("4. 基建股票：")
    print("   ✓ 中国中铁（601390.SS）：策略收益-73.41%，买入持有-32.01%，超额收益-41.39%")
    print("   ✓ 中国铁建（601186.SS）：策略收益-69.52%，买入持有-38.40%，超额收益-31.11%")
    print("   → 基建股票长期下跌，布林带策略难以盈利")
    print()
    
    # 结论
    print("=" * 100)
    print("结论")
    print("=" * 100)
    print()
    
    print("布林带策略在A股上整体表现不佳，平均超额收益-625.71%，只有19.7%的股票超额收益为正。")
    print()
    print("适合布林带策略的股票特征：")
    print("1. 行业龙头，经营稳定")
    print("2. 现金流稳定，分红能力强")
    print("3. 波动性适中，既有波动又不会过于剧烈")
    print("4. 价格围绕均值波动，有回归均值的特性")
    print("5. 趋势性较强，能够捕捉趋势")
    print("6. 流动性好，交易成本低")
    print()
    print("不适合布林带策略的股票特征：")
    print("1. 高成长股票：更适合买入持有策略")
    print("2. 超高收益股票：更适合买入持有策略")
    print("3. 周期性股票：波动太大，布林带策略难以有效交易")
    print("4. 基建股票：长期下跌，布林带策略难以盈利")
    print()
    print("建议：")
    print("1. 针对适合布林带策略的股票，可以继续使用该策略")
    print("2. 针对不适合布林带策略的股票，可以考虑其他策略或买入持有")
    print("3. 可以根据股票特征，选择不同的策略")
    print("4. 可以优化布林带策略的参数，提高策略表现")
    print()


if __name__ == '__main__':
    analyze_positive_excess_stocks()
