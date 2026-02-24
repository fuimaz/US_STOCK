import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from weekly_boll_strategy import WeeklyBollingerStrategy


# 配置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def test_weekly_boll_strategy():
    """
    测试周布林带策略
    """
    print("=" * 80)
    print("周布林带策略测试（20年数据）")
    print("=" * 80)
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 测试股票列表
    symbols = ['AAPL']
    period = '20y'
    
    results_summary = []
    
    for symbol in symbols:
        print(f"\n{'=' * 80}")
        print(f"正在测试 {symbol}...")
        print(f"{'=' * 80}")
        
        try:
            # 获取日线数据
            daily_data = fetcher.fetch_stock_data(symbol, period=period, adjust='forward')
            
            # 确保索引是日期时间格式（统一时区）
            if not isinstance(daily_data.index, pd.DatetimeIndex):
                daily_data.index = pd.to_datetime(daily_data.index, utc=True)
            else:
                daily_data.index = daily_data.index.tz_convert(None)
            
            print(f"✓ 数据获取成功: {len(daily_data)} 条")
            print(f"时间范围: {daily_data.index[0].strftime('%Y-%m-%d')} 到 {daily_data.index[-1].strftime('%Y-%m-%d')}")
            print(f"最新收盘价: ${daily_data['Close'].iloc[-1]:.2f}")
            print()
            
            # 创建策略
            strategy = WeeklyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
            
            print(f"策略参数:")
            print(f"  布林带周期: {strategy.period} 周")
            print(f"  标准差倍数: {strategy.std_dev}")
            print(f"  中线阈值: {strategy.middle_threshold * 100}%")
            print()
            
            # 生成信号
            print("正在生成交易信号...")
            data_with_signals = strategy.generate_signals(daily_data)
            
            # 统计信号
            signals = data_with_signals[data_with_signals['signal'] != 0]
            buy_signals = data_with_signals[data_with_signals['signal'] == 1]
            sell_signals = data_with_signals[data_with_signals['signal'] == -1]
            
            print(f"✓ 信号生成完成")
            print(f"  总信号数: {len(signals)}")
            print(f"  买入信号: {len(buy_signals)}")
            print(f"  卖出信号: {len(sell_signals)}")
            print()
            
            # 如果没有交易信号，跳过回测
            if len(buy_signals) == 0 and len(sell_signals) == 0:
                print(f"⚠️  {symbol} 没有产生交易信号，跳过回测")
                results_summary.append({
                    'symbol': symbol,
                    'trades': 0,
                    'total_return': 0,
                    'annualized_return': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': 0,
                    'win_rate': 0,
                    'status': '无交易信号'
                })
                continue
            
            # 显示信号详情
            print("信号详情（最近20个）:")
            print("-" * 80)
            recent_signals = data_with_signals[data_with_signals['signal'] != 0].tail(20)
            for idx, row in recent_signals.iterrows():
                signal_text = "买入" if row['signal'] == 1 else "卖出"
                print(f"{idx.strftime('%Y-%m-%d')} | {signal_text} | {row['phase']:8s} | 收盘: ${row['Close']:8.2f} | 中线: ${row['Middle']:8.2f} | 上轨: ${row['Upper']:8.2f} | 下轨: ${row['Lower']:8.2f}")
            
            print("-" * 80)
            print()
            
            # 回测
            print("正在进行回测...")
            print("-" * 80)
            
            engine = BacktestEngine(initial_capital=100000)
            result = engine.run_backtest(data_with_signals, strategy)
            
            print(f"回测结果:")
            print(f"  初始资金: ${engine.initial_capital:,.2f}")
            print(f"  最终资金: ${result['final_capital']:,.2f}")
            print(f"  总收益率: {result['total_return_pct']:.2f}%")
            print(f"  年化收益率: {result['annualized_return_pct']:.2f}%")
            print(f"  最大回撤: {result['max_drawdown_pct']:.2f}%")
            print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
            print(f"  总交易次数: {result['total_trades']}")
            print(f"  胜率: {result['win_rate_pct']:.2f}%")
            print(f"  波动率: {result['volatility_pct']:.2f}%")
            print("-" * 80)
            print()
            
            # 保存结果
            output_file = f'weekly_boll_{symbol}_result.csv'
            data_with_signals.to_csv(output_file)
            print(f"✓ 结果已保存到: {output_file}")
            
            # 保存交易记录
            if not result['trades'].empty:
                trades_file = f'weekly_boll_{symbol}_trades.csv'
                result['trades'].to_csv(trades_file, index=False)
                print(f"✓ 交易记录已保存到: {trades_file}")
            
            # 绘制K线图
            if len(buy_signals) > 0 or len(sell_signals) > 0:
                print("正在绘制K线图...")
                plot_kline_with_signals(data_with_signals, symbol)
                print(f"✓ K线图已保存到: weekly_boll_{symbol}_kline.png")
            
            print()
            
            # 添加到汇总
            results_summary.append({
                'symbol': symbol,
                'trades': result['total_trades'],
                'total_return': result['total_return_pct'],
                'annualized_return': result['annualized_return_pct'],
                'max_drawdown': result['max_drawdown_pct'],
                'sharpe_ratio': result['sharpe_ratio'],
                'win_rate': result['win_rate_pct'],
                'status': '成功'
            })
            
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                'symbol': symbol,
                'trades': 0,
                'total_return': 0,
                'annualized_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'win_rate': 0,
                'status': f'失败: {str(e)}'
            })
            continue
    
    # 打印汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print()
    print(f"{'股票代码':<10} {'状态':<15} {'交易次数':<10} {'总收益率':<12} {'年化收益率':<12} {'最大回撤':<12} {'夏普比率':<10} {'胜率':<10}")
    print("-" * 100)
    
    for result in results_summary:
        print(f"{result['symbol']:<10} {result['status']:<15} {result['trades']:<10} {result['total_return']:<12.2f}% {result['annualized_return']:<12.2f}% {result['max_drawdown']:<12.2f}% {result['sharpe_ratio']:<10.2f} {result['win_rate']:<10.2f}%")
    
    print("-" * 100)
    print()
    
    # 统计成功的股票
    successful_stocks = [r for r in results_summary if r['status'] == '成功']
    if len(successful_stocks) > 0:
        print(f"✓ 成功回测的股票数量: {len(successful_stocks)}")
        
        # 找出表现最好的股票
        best_stock = max(successful_stocks, key=lambda x: x['total_return'])
        print(f"✓ 表现最好的股票: {best_stock['symbol']}（总收益率: {best_stock['total_return']:.2f}%）")
        
        # 找出夏普比率最高的股票
        best_sharpe = max(successful_stocks, key=lambda x: x['sharpe_ratio'])
        print(f"✓ 夏普比率最高的股票: {best_sharpe['symbol']}（夏普比率: {best_sharpe['sharpe_ratio']:.2f}）")
        
        # 找出胜率最高的股票
        best_win_rate = max(successful_stocks, key=lambda x: x['win_rate'])
        print(f"✓ 胜率最高的股票: {best_win_rate['symbol']}（胜率: {best_win_rate['win_rate']:.2f}%）")
    else:
        print("⚠️  没有股票产生交易信号，策略可能需要调整")
    
    print()
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


def plot_kline_with_signals(data: pd.DataFrame, symbol: str):
    """
    绘制K线图并标记买卖点
    
    Args:
        data: 包含信号的数据
        symbol: 股票代码
    """
    # 配置mplfinance使用中文字体
    mc = mpf.make_marketcolors(up='r', down='g', edge='i', wick='i', volume='in', inherit=True)
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=False)
    
    # 准备布林带数据
    apds = [
        mpf.make_addplot(data['Upper'], color='red', width=1, alpha=0.7),
        mpf.make_addplot(data['Middle'], color='blue', width=1, alpha=0.7),
        mpf.make_addplot(data['Lower'], color='green', width=1, alpha=0.7)
    ]
    
    # 准备买卖点标记
    buy_signals = data[data['signal'] == 1]
    sell_signals = data[data['signal'] == -1]
    
    # 创建标记点
    buy_markers = pd.Series(index=data.index, dtype=float)
    sell_markers = pd.Series(index=data.index, dtype=float)
    
    # 只在信号从0变为1的那一天标记买入点
    for i in range(1, len(data)):
        if data['signal'].iloc[i] == 1 and data['signal'].iloc[i-1] == 0:
            buy_markers[data.index[i]] = data['Low'].iloc[i] * 0.98
    
    # 只在信号从1变为-1的那一天标记卖出点
    for i in range(1, len(data)):
        if data['signal'].iloc[i] == -1 and data['signal'].iloc[i-1] == 1:
            sell_markers[data.index[i]] = data['High'].iloc[i] * 1.02
    
    # 添加买卖点标记到addplot
    if len(buy_markers.dropna()) > 0:
        apds.append(mpf.make_addplot(buy_markers, type='scatter', markersize=100, marker='^', color='red'))
    
    if len(sell_markers.dropna()) > 0:
        apds.append(mpf.make_addplot(sell_markers, type='scatter', markersize=100, marker='v', color='green'))
    
    # 绘制K线图
    fig, axes = mpf.plot(
        data,
        type='candle',
        style=s,
        title=f'{symbol} Weekly Bollinger Strategy - Buy/Sell Signals',
        ylabel='Price ($)',
        volume=True,
        addplot=apds,
        figsize=(16, 10),
        returnfig=True
    )
    
    # 添加图例
    axes[0].legend(['Upper Band', 'Middle Band', 'Lower Band'], loc='upper left')
    
    # 添加买卖点图例
    from matplotlib.lines import Line2D
    custom_lines = []
    if len(buy_markers.dropna()) > 0:
        custom_lines.append(Line2D([0], [0], marker='^', color='w', markerfacecolor='red', markersize=10, label='Buy Signal'))
    if len(sell_markers.dropna()) > 0:
        custom_lines.append(Line2D([0], [0], marker='v', color='w', markerfacecolor='green', markersize=10, label='Sell Signal'))
    
    if custom_lines:
        axes[0].legend(handles=custom_lines, loc='upper right')
    
    # 保存图片
    output_file = f'weekly_boll_{symbol}_kline.png'
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    
    # 显示图片
    mpf.show()


if __name__ == '__main__':
    test_weekly_boll_strategy()
