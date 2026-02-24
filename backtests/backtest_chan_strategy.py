"""
缠论策略回测 - 10年数据
使用新的chan_theory.py实现
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from chan_theory import ChanTheory
from backtest_engine import BacktestEngine, BaseStrategy

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class ChanTheoryStrategy(BaseStrategy):
    """
    缠论交易策略
    
    策略逻辑：
    - 买入信号：出现第一类买点或第二类买点
    - 卖出信号：出现第一类卖点或第二类卖点
    """
    
    def __init__(self, k_type='day'):
        super().__init__(name="ChanTheory_Strategy")
        self.k_type = k_type
        self.chan = ChanTheory(k_type=k_type)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: OHLCV数据
            
        Returns:
            添加了信号列的DataFrame
        """
        df = data.copy()
        
        # 运行缠论分析
        result = self.chan.analyze(df)
        
        # 初始化信号列
        df['signal'] = 0  # 0:无信号, 1:买入, -1:卖出
        df['buy_point'] = 0
        df['sell_point'] = 0
        
        # 标记买点信号（一买和二买）
        for bp in self.chan.buy_points:
            if bp['type'] in [1, 2] and bp['index'] in df.index:  # 只使用一买和二买
                df.loc[bp['index'], 'signal'] = 1
                df.loc[bp['index'], 'buy_point'] = bp['type']
        
        # 标记卖点信号（一卖和二卖）
        for sp in self.chan.sell_points:
            if sp['type'] in [1, 2] and sp['index'] in df.index:  # 只使用一卖和二卖
                df.loc[sp['index'], 'signal'] = -1
                df.loc[sp['index'], 'sell_point'] = sp['type']
        
        return df


def load_stock_data(symbol, period='10y'):
    """
    加载股票数据
    
    Args:
        symbol: 股票代码
        period: 数据周期
        
    Returns:
        DataFrame或None
    """
    cache_file = f'data_cache/{symbol}_{period}_1d_forward.csv'
    
    if not os.path.exists(cache_file):
        # 尝试其他文件名格式
        cache_file = f'data_cache/{symbol}_{period}_1d_none.csv'
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        data = pd.read_csv(cache_file)
        
        # 处理时间列
        if 'datetime' in data.columns:
            data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
            data = data.set_index('datetime')
        elif 'Date' in data.columns:
            data['Date'] = pd.to_datetime(data['Date'])
            data = data.set_index('Date')
        
        # 只保留OHLCV列
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [c for c in required_cols if c in data.columns]
        data = data[available_cols].copy()
        
        # 删除NaN值
        data = data.dropna()
        
        return data
    except Exception as e:
        print(f"  Error loading {symbol}: {e}")
        return None


def backtest_stock(symbol, data, initial_capital=100000):
    """
    对单只股票进行回测
    
    Args:
        symbol: 股票代码
        data: 股票数据
        initial_capital: 初始资金
        
    Returns:
        回测结果字典
    """
    if data is None or len(data) < 100:
        return None
    
    # 创建策略和回测引擎
    strategy = ChanTheoryStrategy(k_type='day')
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=0.001,  # 0.1%手续费
        slippage=0.0001    # 0.01%滑点
    )
    
    # 运行回测
    results = engine.run_backtest(data, strategy)
    results['symbol'] = symbol
    results['strategy_name'] = strategy.name
    results['data_points'] = len(data)
    results['date_range'] = f"{data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}"
    
    # 保存买卖点信息
    results['buy_points'] = strategy.chan.buy_points
    results['sell_points'] = strategy.chan.sell_points
    
    return results


def print_backtest_results(results):
    """
    打印回测结果
    
    Args:
        results: 回测结果字典
    """
    if results is None:
        print("No results to display")
        return
    
    symbol = results.get('symbol', 'Unknown')
    
    print("\n" + "="*70)
    print(f"回测结果 - {symbol}")
    print("="*70)
    print(f"数据区间: {results.get('date_range', 'N/A')}")
    print(f"数据点数: {results.get('data_points', 0)}")
    print(f"初始资金: ${results.get('initial_capital', 100000):,.2f}")
    print(f"最终资金: ${results['final_capital']:,.2f}")
    print(f"总收益率: {results['total_return_pct']:.2f}%")
    print(f"年化收益率: {results['annualized_return_pct']:.2f}%")
    print(f"夏普比率: {results['sharpe_ratio']:.2f}")
    print(f"最大回撤: {results['max_drawdown_pct']:.2f}%")
    print(f"胜率: {results['win_rate_pct']:.2f}%")
    print(f"波动率: {results['volatility_pct']:.2f}%")
    print(f"总交易次数: {results['total_trades']}")
    print(f"买点数量: {len(results.get('buy_points', []))}")
    print(f"卖点数量: {len(results.get('sell_points', []))}")
    print("="*70 + "\n")


def plot_backtest_results(symbol, data, results, output_dir='results/chan_backtest'):
    """
    绘制回测结果图表
    
    Args:
        symbol: 股票代码
        data: 股票数据
        results: 回测结果
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    fig.suptitle(f'{symbol} - Chan Theory Strategy Backtest', fontsize=16, fontweight='bold')
    
    # 1. 价格走势和买卖点
    ax1 = axes[0]
    ax1.plot(data.index, data['Close'], label='Close Price', linewidth=1.5, color='black', alpha=0.8)
    
    # 标记买点
    for bp in results.get('buy_points', []):
        if bp['index'] in data.index:
            color = 'red' if bp['type'] == 1 else 'orange'
            ax1.scatter(bp['index'], bp['price'], color=color, marker='^', s=150, 
                       zorder=5, edgecolors='black', linewidths=1.5, label=f'Buy Type {bp["type"]}' if bp == results['buy_points'][0] else '')
    
    # 标记卖点
    for sp in results.get('sell_points', []):
        if sp['index'] in data.index:
            color = 'green' if sp['type'] == 1 else 'cyan'
            ax1.scatter(sp['index'], sp['price'], color=color, marker='v', s=150,
                       zorder=5, edgecolors='black', linewidths=1.5, label=f'Sell Type {sp["type"]}' if sp == results['sell_points'][0] else '')
    
    ax1.set_ylabel('Price', fontsize=12)
    ax1.set_title('Price Chart with Buy/Sell Points', fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 2. 资金曲线
    ax2 = axes[1]
    equity_curve = results['equity_curve']
    ax2.plot(equity_curve.index, equity_curve['equity'], label='Portfolio Value', 
            linewidth=2, color='blue', alpha=0.8)
    ax2.axhline(y=results.get('initial_capital', 100000), color='gray', 
               linestyle='--', alpha=0.5, label='Initial Capital')
    ax2.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax2.set_title(f'Equity Curve (Return: {results["total_return_pct"]:.2f}%)', fontsize=14)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # 3. 回撤
    ax3 = axes[2]
    equity = equity_curve['equity']
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100
    ax3.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3, label='Drawdown')
    ax3.set_ylabel('Drawdown (%)', fontsize=12)
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_title(f'Drawdown (Max: {results["max_drawdown_pct"]:.2f}%)', fontsize=14)
    ax3.legend(loc='lower left')
    ax3.grid(True, alpha=0.3)
    
    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, f'{symbol}_backtest.png')
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Chart saved to: {chart_file}")


def run_backtest_on_multiple_stocks(symbols, period='10y'):
    """
    对多只股票进行回测
    
    Args:
        symbols: 股票代码列表
        period: 数据周期
    """
    print("="*70)
    print(f"Chan Theory Strategy Backtest - {period} Data")
    print("="*70)
    
    all_results = []
    
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        
        # 加载数据
        data = load_stock_data(symbol, period)
        
        if data is None:
            print(f"  Data not found for {symbol}")
            continue
        
        print(f"  Data loaded: {len(data)} rows")
        print(f"  Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
        
        # 运行回测
        results = backtest_stock(symbol, data)
        
        if results:
            print_backtest_results(results)
            plot_backtest_results(symbol, data, results)
            all_results.append(results)
        else:
            print(f"  Backtest failed for {symbol}")
    
    # 汇总结果
    if all_results:
        print_summary(all_results)
    
    return all_results


def print_summary(all_results):
    """
    打印汇总结果
    
    Args:
        all_results: 所有回测结果列表
    """
    print("\n" + "="*70)
    print("Summary Statistics")
    print("="*70)
    
    returns = [r['total_return_pct'] for r in all_results]
    annual_returns = [r['annualized_return_pct'] for r in all_results]
    max_dd = [r['max_drawdown_pct'] for r in all_results]
    sharpe = [r['sharpe_ratio'] for r in all_results]
    win_rates = [r['win_rate_pct'] for r in all_results]
    
    print(f"Number of stocks tested: {len(all_results)}")
    print(f"Average total return: {np.mean(returns):.2f}%")
    print(f"Median total return: {np.median(returns):.2f}%")
    print(f"Best return: {np.max(returns):.2f}%")
    print(f"Worst return: {np.min(returns):.2f}%")
    print(f"Win rate (positive return): {sum(1 for r in returns if r > 0) / len(returns) * 100:.1f}%")
    print()
    print(f"Average annualized return: {np.mean(annual_returns):.2f}%")
    print(f"Average max drawdown: {np.mean(max_dd):.2f}%")
    print(f"Average Sharpe ratio: {np.mean(sharpe):.2f}")
    print(f"Average win rate: {np.mean(win_rates):.2f}%")
    print("="*70 + "\n")
    
    # 按收益率排序
    sorted_results = sorted(all_results, key=lambda x: x['total_return_pct'], reverse=True)
    
    print("Top 5 Performers:")
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"  {i}. {r['symbol']}: {r['total_return_pct']:.2f}% (Annual: {r['annualized_return_pct']:.2f}%)")
    
    print("\nBottom 5 Performers:")
    for i, r in enumerate(sorted_results[-5:], 1):
        print(f"  {i}. {r['symbol']}: {r['total_return_pct']:.2f}% (Annual: {r['annualized_return_pct']:.2f}%)")
    
    print("="*70 + "\n")


def main():
    """主函数"""
    # 测试股票列表
    test_symbols = [
        'AAPL',      # 苹果
        'MSFT',      # 微软
        'GOOGL',     # 谷歌
        'AMZN',      # 亚马逊
        'TSLA',      # 特斯拉
        'NVDA',      # 英伟达
        'META',      # Meta
        'BABA',      # 阿里巴巴
        '601186.SS', # 中国铁建
        '600519.SS', # 贵州茅台
    ]
    
    # 运行回测
    results = run_backtest_on_multiple_stocks(test_symbols, period='10y')
    
    print("\nBacktest completed!")


if __name__ == '__main__':
    main()
