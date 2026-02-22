"""
测试改进的严格布林带策略
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from improved_strict_boll_strategy import ImprovedStrictBollStrategy
from backtest_engine import BacktestEngine
import glob
import os

def test_improved_strict_boll_strategy():
    """
    测试改进的严格布林带策略
    """
    print("=" * 100)
    print("改进的严格布林带策略测试（20年数据）")
    print("=" * 100)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/improved_strict_boll'
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
    
    # 获取缓存中的所有A股数据文件
    cache_files = glob.glob('data_cache/*_20y_1d_forward.csv')
    
    # 筛选出A股文件（包含.SS或.SZ后缀）
    a_stock_files = [f for f in cache_files if '.SS_' in f or '.SZ_' in f]
    
    if len(a_stock_files) == 0:
        print("✗ 缓存中没有找到A股数据文件")
        return
    
    print(f"✓ 找到 {len(a_stock_files)} 个A股数据文件")
    print()
    
    # 从文件名中提取股票代码
    symbols = []
    for file_path in a_stock_files:
        filename = os.path.basename(file_path)
        symbol = filename.split('_')[0]
        symbols.append(symbol)
    
    print(f"✓ 股票列表: {', '.join(symbols)}")
    print()
    
    # 初始化回测引擎
    engine = BacktestEngine()
    
    # 初始化策略
    strategy = ImprovedStrictBollStrategy(
        period=20,
        std_dev=2,
        min_uptrend_days=20,  # 一个月约20个交易日
        min_interval_days=10,  # 2周约10个交易日
        ma_period=60,  # 60日移动平均线
        uptrend_threshold=0.5  # 50%的天数创新高
    )
    
    results_summary = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] 正在回测 {symbol}...")
        print("-" * 100)
        
        try:
            # 从缓存获取数据
            data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
            
            if data is None or len(data) == 0:
                print(f"✗ 未获取到数据")
                results_summary.append({
                    'symbol': symbol,
                    'status': '无数据',
                    'total_return': None,
                    'annualized_return': None,
                    'sharpe_ratio': None,
                    'max_drawdown': None,
                    'win_rate': None,
                    'total_trades': 0,
                    'buy_hold_return': None,
                    'excess_return': None
                })
                print()
                continue
            
            # 执行回测
            result = engine.run_backtest(data, strategy)
            
            # 计算买入持有收益
            first_close = data['Close'].iloc[0]
            last_close = data['Close'].iloc[-1]
            buy_hold_return = ((last_close - first_close) / first_close) * 100
            
            # 计算超额收益
            excess_return = result['total_return_pct'] - buy_hold_return
            
            # 计算年化收益
            years = len(data) / 252
            annualized_return = result['annualized_return_pct']
            
            # 计算买入持有年化收益
            buy_hold_annualized = (1 + buy_hold_return / 100) ** (1 / years) - 1
            buy_hold_annualized_pct = buy_hold_annualized * 100
            
            print(f"✓ 回测完成")
            print(f"  数据量: {len(data)} 条")
            print(f"  时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
            print(f"  初始资金: ¥{engine.initial_capital:,.2f}")
            print(f"  最终资金: ¥{result['final_capital']:,.2f}")
            print(f"  策略总收益: {result['total_return_pct']:.2f}%")
            print(f"  策略年化收益: {annualized_return:.2f}%")
            print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
            print(f"  最大回撤: {result['max_drawdown_pct']:.2f}%")
            print(f"  胜率: {result['win_rate_pct']:.2f}%")
            print(f"  总交易次数: {result['total_trades']}")
            print(f"  买入持有收益: {buy_hold_return:.2f}%")
            print(f"  买入持有年化: {buy_hold_annualized_pct:.2f}%")
            print(f"  超额收益: {excess_return:.2f}%")
            
            # 添加信号到数据中
            data_with_signals = data.copy()
            data_with_signals['Signal'] = 0
            data_with_signals['Position'] = 0
            
            # 处理交易记录
            trades_df = result['trades']
            if not trades_df.empty:
                buy_trades = trades_df[trades_df['type'] == 'buy']
                sell_trades = trades_df[trades_df['type'] == 'sell']
                
                for i in range(min(len(buy_trades), len(sell_trades))):
                    buy_trade = buy_trades.iloc[i]
                    sell_trade = sell_trades.iloc[i]
                    
                    entry_idx = data.index.get_loc(buy_trade['date'])
                    exit_idx = data.index.get_loc(sell_trade['date'])
                    data_with_signals.iloc[entry_idx, data_with_signals.columns.get_loc('Signal')] = 1
                    data_with_signals.iloc[entry_idx:exit_idx+1, data_with_signals.columns.get_loc('Position')] = 1
            
            # 保存结果到统一文件夹
            output_file = os.path.join(output_dir, f'{symbol}_result.csv')
            data_with_signals.to_csv(output_file)
            print(f"✓ 结果已保存到: {output_file}")
            
            # 保存交易记录到统一文件夹
            if not trades_df.empty:
                trades_file = os.path.join(output_dir, f'{symbol}_trades.csv')
                trades_df.to_csv(trades_file, index=False)
                print(f"✓ 交易记录已保存到: {trades_file}")
            
            results_summary.append({
                'symbol': symbol,
                'status': '成功',
                'total_return': result['total_return_pct'],
                'annualized_return': annualized_return,
                'sharpe_ratio': result['sharpe_ratio'],
                'max_drawdown': result['max_drawdown_pct'],
                'win_rate': result['win_rate_pct'],
                'total_trades': result['total_trades'],
                'buy_hold_return': buy_hold_return,
                'buy_hold_annualized': buy_hold_annualized_pct,
                'excess_return': excess_return
            })
            
        except Exception as e:
            print(f"✗ 回测失败: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                'symbol': symbol,
                'status': f'失败: {str(e)}',
                'total_return': None,
                'annualized_return': None,
                'sharpe_ratio': None,
                'max_drawdown': None,
                'win_rate': None,
                'total_trades': 0,
                'buy_hold_return': None,
                'excess_return': None
            })
        
        print()
    
    # 打印汇总结果
    print("=" * 100)
    print("回测结果汇总")
    print("=" * 100)
    print()
    print(f"{'股票代码':<15} {'状态':<20} {'策略收益':<12} {'年化收益':<12} {'超额收益':<12} {'胜率':<10} {'交易次数':<10}")
    print("-" * 100)
    
    for result in results_summary:
        total_return_str = f"{result['total_return']:.2f}%" if result['total_return'] is not None else "N/A"
        annualized_return_str = f"{result['annualized_return']:.2f}%" if result['annualized_return'] is not None else "N/A"
        excess_return_str = f"{result['excess_return']:.2f}%" if result['excess_return'] is not None else "N/A"
        win_rate_str = f"{result['win_rate']:.2f}%" if result['win_rate'] is not None else "N/A"
        
        print(f"{result['symbol']:<15} {result['status']:<20} {total_return_str:<12} {annualized_return_str:<12} {excess_return_str:<12} {win_rate_str:<10} {result['total_trades']:<10}")
    
    print("-" * 100)
    print()
    
    # 统计成功和失败
    successful_results = [r for r in results_summary if r['status'] == '成功']
    failed_results = [r for r in results_summary if r['status'] != '成功']
    
    print(f"✓ 成功回测: {len(successful_results)}/{len(results_summary)}")
    print(f"✗ 失败: {len(failed_results)}/{len(results_summary)}")
    print(f"✓ 成功率: {len(successful_results) / len(results_summary) * 100:.1f}%")
    print()
    
    if successful_results:
        # 计算平均指标
        avg_total_return = np.mean([r['total_return'] for r in successful_results])
        avg_annualized_return = np.mean([r['annualized_return'] for r in successful_results])
        avg_sharpe_ratio = np.mean([r['sharpe_ratio'] for r in successful_results])
        avg_max_drawdown = np.mean([r['max_drawdown'] for r in successful_results])
        avg_win_rate = np.mean([r['win_rate'] for r in successful_results])
        avg_total_trades = np.mean([r['total_trades'] for r in successful_results])
        avg_buy_hold_return = np.mean([r['buy_hold_return'] for r in successful_results])
        avg_excess_return = np.mean([r['excess_return'] for r in successful_results])
        
        print("=" * 100)
        print("平均表现")
        print("=" * 100)
        print()
        print(f"平均策略收益: {avg_total_return:.2f}%")
        print(f"平均年化收益: {avg_annualized_return:.2f}%")
        print(f"平均夏普比率: {avg_sharpe_ratio:.2f}")
        print(f"平均最大回撤: {avg_max_drawdown:.2f}%")
        print(f"平均胜率: {avg_win_rate:.2f}%")
        print(f"平均交易次数: {avg_total_trades:.2f}")
        print(f"平均买入持有收益: {avg_buy_hold_return:.2f}%")
        print(f"平均超额收益: {avg_excess_return:.2f}%")
        print()
        
        # 找出表现最好的股票
        best_total_return = max(successful_results, key=lambda x: x['total_return'])
        best_annualized = max(successful_results, key=lambda x: x['annualized_return'])
        best_sharpe = max(successful_results, key=lambda x: x['sharpe_ratio'])
        best_excess = max(successful_results, key=lambda x: x['excess_return'])
        
        print("=" * 100)
        print("表现最好的股票")
        print("=" * 100)
        print()
        print(f"✓ 策略收益最高: {best_total_return['symbol']} - {best_total_return['total_return']:.2f}%")
        print(f"✓ 年化收益最高: {best_annualized['symbol']} - {best_annualized['annualized_return']:.2f}%")
        print(f"✓ 夏普比率最高: {best_sharpe['symbol']} - {best_sharpe['sharpe_ratio']:.2f}")
        print(f"✓ 超额收益最高: {best_excess['symbol']} - {best_excess['excess_return']:.2f}%")
        print()
        
        # 统计超额收益为正的股票
        positive_excess = [r for r in successful_results if r['excess_return'] > 0]
        print(f"✓ 超额收益为正: {len(positive_excess)}/{len(successful_results)} ({len(positive_excess)/len(successful_results)*100:.1f}%)")
        print()
        
        # 统计有交易的股票
        with_trades = [r for r in successful_results if r['total_trades'] > 0]
        print(f"✓ 有交易的股票: {len(with_trades)}/{len(successful_results)} ({len(with_trades)/len(successful_results)*100:.1f}%)")
        print()
    
    # 保存汇总结果
    summary_df = pd.DataFrame(results_summary)
    summary_file = os.path.join(output_dir, 'summary.csv')
    summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    print(f"✓ 汇总结果已保存到: {summary_file}")
    print()
    
    print("=" * 100)
    print("回测完成！")
    print("=" * 100)

if __name__ == '__main__':
    test_improved_strict_boll_strategy()