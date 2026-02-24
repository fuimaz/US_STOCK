import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy

def compare_adjustment_types(symbol: str = "AAPL", period: str = "1y"):
    """
    对比不同复权方式的回测效果
    
    Args:
        symbol: 股票代码
        period: 数据周期
    """
    print("=" * 80)
    print(f"复权方式回测对比 - {symbol}")
    print("=" * 80)
    
    fetcher = DataFetcher(cache_dir='data_cache', cache_days=0)
    
    # 获取不同复权方式的数据
    adjustment_types = ['none', 'forward', 'backward']
    results = {}
    
    for adjust_type in adjustment_types:
        print(f"\n{'=' * 80}")
        print(f"正在测试: {adjust_type}复权")
        print(f"{'=' * 80}")
        
        try:
            data = fetcher.fetch_stock_data(
                symbol,
                period=period,
                use_cache=False,
                adjust=adjust_type
            )
            
            print(f"✓ 数据获取成功")
            print(f"  数据条数: {len(data)}")
            print(f"  时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
            print(f"  最新收盘价: ${data['Close'].iloc[-1]:.2f}")
            print(f"  最高价: ${data['High'].max():.2f}")
            print(f"  最低价: ${data['Low'].min():.2f}")
            
            # 创建简单策略
            strategy = MovingAverageStrategy(short_period=20, long_period=50)
            
            # 回测
            engine = BacktestEngine(initial_capital=100000)
            backtest_result = engine.run_backtest(data, strategy)
            
            results[adjust_type] = {
                'data': data,
                'backtest_result': backtest_result
            }
            
            print(f"\n回测结果:")
            print(f"  总收益率: {backtest_result['total_return_pct']:.2%}")
            print(f"  年化收益率: {backtest_result['annualized_return_pct']:.2%}")
            print(f"  最大回撤: {backtest_result['max_drawdown_pct']:.2%}")
            print(f"  夏普比率: {backtest_result['sharpe_ratio']:.2f}")
            print(f"  交易次数: {backtest_result['total_trades']}")
            print(f"  胜率: {backtest_result['win_rate_pct']:.2%}")
            
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            continue
    
    # 对比结果
    print(f"\n{'=' * 80}")
    print("回测结果对比")
    print(f"{'=' * 80}")
    
    comparison_data = []
    for adjust_type, result in results.items():
        br = result['backtest_result']
        comparison_data.append({
            '复权方式': adjust_type,
            '总收益率': f"{br['total_return_pct']:.2%}",
            '年化收益率': f"{br['annualized_return_pct']:.2%}",
            '最大回撤': f"{br['max_drawdown_pct']:.2%}",
            '夏普比率': f"{br['sharpe_ratio']:.2f}",
            '交易次数': br['total_trades'],
            '胜率': f"{br['win_rate_pct']:.2%}"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df.to_string(index=False))
    
    # 绘制对比图
    if len(results) >= 2:
        plot_comparison(results, symbol)
    
    # 给出建议
    print(f"\n{'=' * 80}")
    print("建议")
    print(f"{'=' * 80}")
    
    if len(results) >= 2:
        best_return = max(results.items(), key=lambda x: x[1]['backtest_result']['total_return_pct'])
        best_sharpe = max(results.items(), key=lambda x: x[1]['backtest_result']['sharpe_ratio'])
        best_drawdown = min(results.items(), key=lambda x: x[1]['backtest_result']['max_drawdown_pct'])
        
        print(f"\n✓ 最高收益率: {best_return[0]}复权 ({best_return[1]['backtest_result']['total_return_pct']:.2%})")
        print(f"✓ 最高夏普比率: {best_sharpe[0]}复权 ({best_sharpe[1]['backtest_result']['sharpe_ratio']:.2f})")
        print(f"✓ 最小回撤: {best_drawdown[0]}复权 ({best_drawdown[1]['backtest_result']['max_drawdown_pct']:.2%})")
        
        print(f"\n推荐:")
        if best_return[0] == best_sharpe[0]:
            print(f"  综合推荐使用 {best_return[0]}复权")
        else:
            print(f"  追求收益: 使用 {best_return[0]}复权")
            print(f"  追求稳健: 使用 {best_sharpe[0]}复权")

def plot_comparison(results: dict, symbol: str):
    """
    绘制不同复权方式的对比图
    
    Args:
        results: 回测结果字典
        symbol: 股票代码
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'{symbol} - 不同复权方式对比', fontsize=14, fontweight='bold')
    
    # 价格对比
    ax1 = axes[0, 0]
    for adjust_type, result in results.items():
        data = result['data']
        ax1.plot(data.index, data['Close'], label=f'{adjust_type}复权', linewidth=1)
    ax1.set_title('价格走势对比')
    ax1.set_xlabel('日期')
    ax1.set_ylabel('价格')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 收益率对比
    ax2 = axes[0, 1]
    for adjust_type, result in results.items():
        br = result['backtest_result']
        ax2.bar(adjust_type, br['total_return'], label=f'{adjust_type}复权')
    ax2.set_title('总收益率对比')
    ax2.set_ylabel('收益率')
    ax2.grid(True, alpha=0.3)
    
    # 回撤对比
    ax3 = axes[1, 0]
    for adjust_type, result in results.items():
        data = result['data']
        br = result['backtest_result']
        equity_curve = br['equity_curve']
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        ax3.plot(data.index, drawdown, label=f'{adjust_type}复权', linewidth=1)
    ax3.set_title('回撤对比')
    ax3.set_xlabel('日期')
    ax3.set_ylabel('回撤')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 夏普比率对比
    ax4 = axes[1, 1]
    sharpe_ratios = [result['backtest_result']['sharpe_ratio'] for result in results.values()]
    ax4.bar(results.keys(), sharpe_ratios)
    ax4.set_title('夏普比率对比')
    ax4.set_ylabel('夏普比率')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('adjustment_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ 对比图已保存到 adjustment_comparison.png")
    plt.close()

if __name__ == "__main__":
    compare_adjustment_types(symbol="AAPL", period="1y")