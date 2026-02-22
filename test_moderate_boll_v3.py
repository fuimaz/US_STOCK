"""
测试调整后的适中布林带策略V3并可视化
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from moderate_boll_strategy_v3 import ModerateBollStrategyV3
from backtest_engine import BacktestEngine
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

def test_and_visualize():
    """
    测试调整后的适中策略V3并可视化买卖点
    """
    print("=" * 100)
    print("调整后的适中布林带策略V3测试与可视化")
    print("=" * 100)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/moderate_boll_v3'
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
    
    # 选择3个股票进行测试
    test_symbols = [
        '601186.SS',  # 中国铁建 - 在改进策略中表现很好
        '600519.SS',  # 贵州茅台 - 在原始策略中表现很好
        '000001.SZ',  # 平安银行 - 表现中等
    ]
    
    print(f"✓ 测试股票: {', '.join(test_symbols)}")
    print()
    
    # 初始化回测引擎
    engine = BacktestEngine()
    
    # 初始化策略
    strategy = ModerateBollStrategyV3(
        period=20,
        std_dev=2,
        min_uptrend_days=20,
        min_interval_days=10,
        ma_period=60,
        uptrend_threshold=0.5
    )
    
    results_summary = []
    
    for symbol in test_symbols:
        print(f"正在回测 {symbol}...")
        print("-" * 100)
        
        try:
            # 从缓存获取数据
            data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
            
            if data is None or len(data) == 0:
                print(f"✗ 未获取到数据")
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
            
            # 生成信号
            signals_df = strategy.generate_signals(data)
            
            # 可视化
            visualize_trades(symbol, signals_df, result['trades'], output_dir)
            
            # 保存结果
            output_file = os.path.join(output_dir, f'{symbol}_result.csv')
            signals_df.to_csv(output_file)
            print(f"✓ 结果已保存到: {output_file}")
            
            # 保存交易记录
            if not result['trades'].empty:
                trades_file = os.path.join(output_dir, f'{symbol}_trades.csv')
                result['trades'].to_csv(trades_file, index=False)
                print(f"✓ 交易记录已保存到: {trades_file}")
            
            results_summary.append({
                'symbol': symbol,
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
        
        print()
    
    # 打印汇总结果
    print("=" * 100)
    print("回测结果汇总")
    print("=" * 100)
    print()
    print(f"{'股票代码':<15} {'策略收益':<15} {'年化收益':<15} {'超额收益':<15} {'胜率':<12} {'交易次数':<10}")
    print("-" * 100)
    
    for result in results_summary:
        print(f"{result['symbol']:<15} {result['total_return']:<15.2f}% {result['annualized_return']:<15.2f}% {result['excess_return']:<15.2f}% {result['win_rate']:<12.2f}% {result['total_trades']:<10}")
    
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

def visualize_trades(symbol, data, trades, output_dir):
    """
    可视化交易信号
    
    Args:
        symbol: 股票代码
        data: 包含信号的数据
        trades: 交易记录
        output_dir: 输出目录
    """
    print(f"正在生成 {symbol} 的可视化图表...")
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
    fig.suptitle(f'{symbol} - 调整后适中布林带策略V3交易信号', fontsize=16, fontweight='bold')
    
    # 绘制价格和布林带
    ax1.plot(data.index, data['Close'], label='收盘价', linewidth=1, alpha=0.8)
    ax1.plot(data.index, data['upper_band'], label='上轨', linewidth=1, alpha=0.6, color='red', linestyle='--')
    ax1.plot(data.index, data['middle_band'], label='中轨', linewidth=1, alpha=0.6, color='orange', linestyle='--')
    ax1.plot(data.index, data['lower_band'], label='下轨', linewidth=1, alpha=0.6, color='green', linestyle='--')
    
    # 绘制买入卖出点
    buy_signals = data[data['signal'] == 1]
    sell_signals = data[data['signal'] == -1]
    
    if not buy_signals.empty:
        ax1.scatter(buy_signals.index, buy_signals['Close'], color='red', marker='^', s=200, 
                   label='买入', zorder=5, edgecolors='black', linewidths=1)
    
    if not sell_signals.empty:
        ax1.scatter(sell_signals.index, sell_signals['Close'], color='green', marker='v', s=200, 
                   label='卖出', zorder=5, edgecolors='black', linewidths=1)
    
    ax1.set_ylabel('价格', fontsize=12)
    ax1.set_title('价格走势与交易信号', fontsize=14)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 绘制布林带宽度
    bb_width = data['upper_band'] - data['lower_band']
    ax2.plot(data.index, bb_width, label='布林带宽度', linewidth=1, color='purple')
    ax2.axhline(y=bb_width.mean(), color='red', linestyle='--', alpha=0.5, label='平均宽度')
    ax2.fill_between(data.index, bb_width, alpha=0.3, color='purple')
    
    ax2.set_ylabel('布林带宽度', fontsize=12)
    ax2.set_xlabel('日期', fontsize=12)
    ax2.set_title('布林带宽度（波动性）', fontsize=14)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 格式化x轴
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax2.xaxis.set_minor_locator(mdates.MonthLocator([1, 4, 7, 10]))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, f'{symbol}_chart.png')
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 图表已保存到: {chart_file}")
    
    # 如果有交易，创建详细的交易图表
    if not trades.empty:
        visualize_detailed_trades(symbol, data, trades, output_dir)

def visualize_detailed_trades(symbol, data, trades, output_dir):
    """
    可视化详细交易
    
    Args:
        symbol: 股票代码
        data: 包含信号的数据
        trades: 交易记录
        output_dir: 输出目录
    """
    print(f"正在生成 {symbol} 的详细交易图表...")
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 分离买入和卖出交易
    buy_trades = trades[trades['type'] == 'buy']
    sell_trades = trades[trades['type'] == 'sell']
    
    # 计算交易对数
    num_trades = min(len(buy_trades), len(sell_trades))
    
    if num_trades == 0:
        return
    
    # 为每笔交易创建一个子图
    fig, axes = plt.subplots(num_trades, 1, figsize=(16, 6 * num_trades))
    if num_trades == 1:
        axes = [axes]
    
    fig.suptitle(f'{symbol} - 详细交易分析', fontsize=16, fontweight='bold')
    
    for i in range(num_trades):
        ax = axes[i]
        
        buy_trade = buy_trades.iloc[i]
        sell_trade = sell_trades.iloc[i]
        
        buy_date = buy_trade['date']
        sell_date = sell_trade['date']
        
        # 获取买入和卖出日期的索引
        buy_idx = data.index.get_loc(buy_date)
        sell_idx = data.index.get_loc(sell_date)
        
        # 扩展显示范围（前后各30天）
        start_idx = max(0, buy_idx - 30)
        end_idx = min(len(data) - 1, sell_idx + 30)
        
        # 提取相关数据
        plot_data = data.iloc[start_idx:end_idx + 1]
        
        # 计算收益率
        buy_price = buy_trade['price']
        sell_price = sell_trade['price']
        return_pct = ((sell_price - buy_price) / buy_price) * 100
        
        # 绘制价格和布林带
        ax.plot(plot_data.index, plot_data['Close'], label='收盘价', linewidth=1.5, alpha=0.8)
        ax.plot(plot_data.index, plot_data['upper_band'], label='上轨', linewidth=1, alpha=0.6, color='red', linestyle='--')
        ax.plot(plot_data.index, plot_data['middle_band'], label='中轨', linewidth=1, alpha=0.6, color='orange', linestyle='--')
        ax.plot(plot_data.index, plot_data['lower_band'], label='下轨', linewidth=1, alpha=0.6, color='green', linestyle='--')
        
        # 绘制买入卖出点
        ax.scatter([buy_date], [buy_price], color='red', marker='^', s=300, 
                  label='买入', zorder=5, edgecolors='black', linewidths=2)
        ax.scatter([sell_date], [sell_price], color='green', marker='v', s=300, 
                  label='卖出', zorder=5, edgecolors='black', linewidths=2)
        
        # 添加收益标注
        color = 'red' if return_pct < 0 else 'green'
        ax.annotate(f'收益: {return_pct:.2f}%', 
                   xy=(sell_date, sell_price), 
                   xytext=(10, 10), 
                   textcoords='offset points',
                   fontsize=12, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 添加交易信息
        info_text = f'交易 {i+1}\n'
        info_text += f'买入: {buy_date.strftime("%Y-%m-%d")} @ {buy_price:.2f}\n'
        info_text += f'卖出: {sell_date.strftime("%Y-%m-%d")} @ {sell_price:.2f}\n'
        info_text += f'持仓天数: {(sell_date - buy_date).days} 天\n'
        info_text += f'收益率: {return_pct:.2f}%'
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        ax.set_ylabel('价格', fontsize=12)
        ax.set_title(f'交易 {i+1}: {buy_date.strftime("%Y-%m-%d")} 至 {sell_date.strftime("%Y-%m-%d")}', fontsize=14)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    # 保存图表
    chart_file = os.path.join(output_dir, f'{symbol}_detailed_trades.png')
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 详细交易图表已保存到: {chart_file}")

if __name__ == '__main__':
    test_and_visualize()