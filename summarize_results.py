import pandas as pd
import glob
import os

def summarize_backtest_results():
    """
    汇总所有股票的回测结果
    """
    print("=" * 100)
    print("日线布林带策略回测结果汇总（5年数据）")
    print("=" * 100)
    print()
    
    # 定义输出目录
    output_dir = 'results/daily_boll'
    
    # 检查目录是否存在
    if not os.path.exists(output_dir):
        print(f"✗ 结果目录不存在: {output_dir}")
        print("请先运行 test_daily_boll.py 生成回测结果")
        return
    
    # 获取所有交易记录文件
    trade_files = glob.glob(os.path.join(output_dir, '*_trades.csv'))
    
    if len(trade_files) == 0:
        print(f"✗ 没有找到交易记录文件: {output_dir}/*_trades.csv")
        return
    
    print(f"✓ 找到 {len(trade_files)} 个交易记录文件")
    print()
    
    results = []
    
    for trade_file in sorted(trade_files):
        # 从文件名中提取股票代码
        filename = os.path.basename(trade_file)
        symbol = filename.replace('_trades.csv', '')
        result_file = os.path.join(output_dir, f'{symbol}_result.csv')
        
        try:
            # 读取结果文件
            df = pd.read_csv(result_file, parse_dates=['datetime'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            
            # 计算原始涨幅
            first_close = df['Close'].iloc[0]
            last_close = df['Close'].iloc[-1]
            buy_hold_return = ((last_close - first_close) / first_close) * 100
            
            # 计算年化收益率
            years = len(df) / 252
            buy_hold_annual = (1 + buy_hold_return / 100) ** (1 / years) - 1
            buy_hold_annual_pct = buy_hold_annual * 100
            
            # 读取交易记录
            trades = pd.read_csv(trade_file, parse_dates=['date'])
            
            # 计算策略收益
            if len(trades) > 0:
                buys = trades[trades['type'] == 'buy']
                sells = trades[trades['type'] == 'sell']
                
                if len(buys) > 0 and len(sells) > 0:
                    total_profit = sells['proceeds'].sum() - buys['cost'].sum()
                    total_cost = buys['cost'].sum()
                    strategy_return = (total_profit / total_cost) * 100
                    strategy_annual = (1 + strategy_return / 100) ** (1 / years) - 1
                    strategy_annual_pct = strategy_annual * 100
                    
                    # 计算胜率
                    profitable_trades = 0
                    for i in range(min(len(buys), len(sells))):
                        if sells.iloc[i]['proceeds'] > buys.iloc[i]['cost']:
                            profitable_trades += 1
                    win_rate = (profitable_trades / min(len(buys), len(sells))) * 100
                    
                    # 计算最大回撤
                    df['cumulative_return'] = (1 + df['signal'].shift(1).fillna(0).cumsum() * 0).astype(float)
                    df['portfolio_value'] = 100000 * (1 + df['signal'].shift(1).fillna(0).cumsum() * 0).astype(float)
                    
                    # 简单计算最大回撤
                    df['running_max'] = df['portfolio_value'].cummax()
                    df['drawdown'] = (df['portfolio_value'] - df['running_max']) / df['running_max'] * 100
                    max_drawdown = df['drawdown'].min()
                    
                    # 计算超额收益
                    excess_return = strategy_return - buy_hold_return
                    excess_annual = strategy_annual_pct - buy_hold_annual_pct
                    
                    results.append({
                        'symbol': symbol,
                        'strategy_return': strategy_return,
                        'buy_hold_return': buy_hold_return,
                        'excess_return': excess_return,
                        'strategy_annual': strategy_annual_pct,
                        'buy_hold_annual': buy_hold_annual_pct,
                        'excess_annual': excess_annual,
                        'total_trades': len(buys),
                        'win_rate': win_rate,
                        'max_drawdown': max_drawdown,
                        'advantage': '是' if excess_return > 0 else '否'
                    })
        except Exception as e:
            print(f"✗ 处理 {symbol} 失败: {e}")
            continue
    
    # 创建DataFrame
    results_df = pd.DataFrame(results)
    
    # 按策略收益排序
    results_df = results_df.sort_values('strategy_return', ascending=False)
    
    # 打印汇总表格
    print(f"{'股票代码':<10} {'策略收益':<12} {'原始涨幅':<12} {'超额收益':<12} {'策略年化':<12} {'原始年化':<12} {'超额年化':<12} {'交易次数':<10} {'胜率':<10} {'优势':<6}")
    print("-" * 110)
    
    for _, row in results_df.iterrows():
        print(f"{row['symbol']:<10} {row['strategy_return']:>10.2f}% {row['buy_hold_return']:>10.2f}% {row['excess_return']:>10.2f}% {row['strategy_annual']:>10.2f}% {row['buy_hold_annual']:>10.2f}% {row['excess_annual']:>10.2f}% {row['total_trades']:>8} {row['win_rate']:>8.2f}% {row['advantage']:<6}")
    
    print("-" * 110)
    print()
    
    # 统计分析
    print("=" * 100)
    print("统计分析")
    print("=" * 100)
    print()
    
    total_stocks = len(results_df)
    winning_stocks = len(results_df[results_df['excess_return'] > 0])
    losing_stocks = len(results_df[results_df['excess_return'] < 0])
    
    print(f"总股票数: {total_stocks}")
    print(f"策略跑赢原始涨幅: {winning_stocks} ({winning_stocks/total_stocks*100:.1f}%)")
    print(f"策略跑输原始涨幅: {losing_stocks} ({losing_stocks/total_stocks*100:.1f}%)")
    print()
    
    # 平均值
    avg_strategy_return = results_df['strategy_return'].mean()
    avg_buy_hold_return = results_df['buy_hold_return'].mean()
    avg_excess_return = results_df['excess_return'].mean()
    
    print(f"平均策略收益: {avg_strategy_return:.2f}%")
    print(f"平均原始涨幅: {avg_buy_hold_return:.2f}%")
    print(f"平均超额收益: {avg_excess_return:.2f}%")
    print()
    
    # 中位数
    median_strategy_return = results_df['strategy_return'].median()
    median_buy_hold_return = results_df['buy_hold_return'].median()
    median_excess_return = results_df['excess_return'].median()
    
    print(f"中位数策略收益: {median_strategy_return:.2f}%")
    print(f"中位数原始涨幅: {median_buy_hold_return:.2f}%")
    print(f"中位数超额收益: {median_excess_return:.2f}%")
    print()
    
    # 最佳和最差
    best_stock = results_df.iloc[0]
    worst_stock = results_df.iloc[-1]
    
    print(f"表现最好: {best_stock['symbol']} (策略收益: {best_stock['strategy_return']:.2f}%, 超额收益: {best_stock['excess_return']:.2f}%)")
    print(f"表现最差: {worst_stock['symbol']} (策略收益: {worst_stock['strategy_return']:.2f}%, 超额收益: {worst_stock['excess_return']:.2f}%)")
    print()
    
    # 跑赢的股票列表
    winning_list = results_df[results_df['excess_return'] > 0]['symbol'].tolist()
    print(f"跑赢原始涨幅的股票: {', '.join(winning_list)}")
    print()
    
    # 保存汇总结果到输出目录
    summary_file = os.path.join(output_dir, 'summary.csv')
    results_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    print(f"✓ 汇总结果已保存到: {summary_file}")
    print()
    
    print("=" * 100)
    print("汇总完成！")
    print("=" * 100)

if __name__ == '__main__':
    summarize_backtest_results()
