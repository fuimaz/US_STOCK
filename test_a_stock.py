"""
A股数据获取、展示和回测
使用与美股相同的代码结构
"""
import pandas as pd
from data_fetcher import DataFetcher
from daily_boll_strategy import DailyBollingerStrategy
from backtest_engine import BacktestEngine
from interactive_kline import InteractiveKLineViewer
import os


def test_a_stock_backtest():
    """
    A股布林带策略回测
    """
    print("=" * 80)
    print("A股布林带策略测试（1年数据）")
    print("=" * 80)
    
    # 创建输出文件夹
    output_dir = 'results/a_stock'
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
    
    # 测试A股列表（上海和深圳交易所）
    symbols = [
        ('600519.SS', '贵州茅台', '上海'),
        ('601318.SS', '中国平安', '上海'),
        ('600036.SS', '招商银行', '上海'),
        ('600276.SS', '恒瑞医药', '上海'),
        ('000001.SZ', '平安银行', '深圳'),
        ('000002.SZ', '万科A', '深圳'),
        ('000858.SZ', '五粮液', '深圳'),
        ('002594.SZ', '比亚迪', '深圳'),
        ('300750.SZ', '宁德时代', '深圳'),
    ]
    period = '1y'
    
    results_summary = []
    
    for symbol, name, market in symbols:
        print(f"\n{'=' * 80}")
        print(f"正在测试 {name} ({symbol})...")
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
            print(f"最新收盘价: ¥{daily_data['Close'].iloc[-1]:.2f}")
            
            # 创建策略
            strategy = DailyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
            
            # 生成信号
            data_with_signals = strategy.generate_signals(daily_data)
            
            # 统计信号
            signals = data_with_signals[data_with_signals['signal'] != 0]
            buy_signals = data_with_signals[data_with_signals['signal'] == 1]
            sell_signals = data_with_signals[data_with_signals['signal'] == -1]
            
            # 如果没有交易信号，跳过回测
            if len(buy_signals) == 0 and len(sell_signals) == 0:
                print(f"⚠️  {name} 没有产生交易信号，跳过回测")
                results_summary.append({
                    'symbol': symbol,
                    'name': name,
                    'market': market,
                    'trades': 0,
                    'total_return': 0,
                    'annualized_return': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': 0,
                    'win_rate': 0,
                    'buy_hold_return': 0,
                    'buy_hold_annual': 0,
                    'excess_return': 0,
                    'excess_annual': 0,
                    'status': '无交易信号'
                })
                continue
            
            # 回测
            engine = BacktestEngine(initial_capital=100000)
            result = engine.run_backtest(data_with_signals, strategy)
            
            # 计算原始涨幅（买入持有）
            first_close = daily_data['Close'].iloc[0]
            last_close = daily_data['Close'].iloc[-1]
            buy_hold_return = ((last_close - first_close) / first_close) * 100
            buy_hold_annual = (1 + buy_hold_return / 100) ** (1 / (len(daily_data) / 252)) - 1
            buy_hold_annual_pct = buy_hold_annual * 100
            
            # 计算超额收益
            excess_return = result['total_return_pct'] - buy_hold_return
            excess_annual = result['annualized_return_pct'] - buy_hold_annual_pct
            
            print(f"原始涨幅（买入持有）:")
            print(f"  起始价格: ¥{first_close:.2f}")
            print(f"  结束价格: ¥{last_close:.2f}")
            print(f"  总收益率: {buy_hold_return:.2f}%")
            print(f"  年化收益率: {buy_hold_annual_pct:.2f}%")
            print()
            
            print(f"策略回测结果:")
            print(f"  初始资金: ¥{engine.initial_capital:,.2f}")
            print(f"  最终资金: ¥{result['final_capital']:,.2f}")
            print(f"  总收益率: {result['total_return_pct']:.2f}%")
            print(f"  年化收益率: {result['annualized_return_pct']:.2f}%")
            print(f"  最大回撤: {result['max_drawdown_pct']:.2f}%")
            print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
            print(f"  总交易次数: {result['total_trades']}")
            print(f"  胜率: {result['win_rate_pct']:.2f}%")
            print(f"  波动率: {result['volatility_pct']:.2f}%")
            print()
            
            print(f"策略 vs 原始涨幅对比:")
            print(f"  超额总收益: {excess_return:+.2f}%")
            print(f"  超额年化收益: {excess_annual:+.2f}%")
            print(f"  策略优势: {'是' if excess_return > 0 else '否'}")
            print("-" * 80)
            print()
            
            # 保存结果到统一文件夹
            output_file = os.path.join(output_dir, f'{symbol}_result.csv')
            data_with_signals.to_csv(output_file)
            print(f"✓ 结果已保存到: {output_file}")
            
            # 保存交易记录到统一文件夹
            if not result['trades'].empty:
                trades_file = os.path.join(output_dir, f'{symbol}_trades.csv')
                result['trades'].to_csv(trades_file, index=False)
                print(f"✓ 交易记录已保存到: {trades_file}")
            
            print()
            
            # 添加到汇总
            results_summary.append({
                'symbol': symbol,
                'name': name,
                'market': market,
                'trades': result['total_trades'],
                'total_return': result['total_return_pct'],
                'annualized_return': result['annualized_return_pct'],
                'max_drawdown': result['max_drawdown_pct'],
                'sharpe_ratio': result['sharpe_ratio'],
                'win_rate': result['win_rate_pct'],
                'buy_hold_return': buy_hold_return,
                'buy_hold_annual': buy_hold_annual_pct,
                'excess_return': excess_return,
                'excess_annual': excess_annual,
                'status': '成功'
            })
            
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                'symbol': symbol,
                'name': name,
                'market': market,
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
    print(f"{'股票代码':<15} {'股票名称':<12} {'市场':<8} {'策略收益':<12} {'原始涨幅':<12} {'超额收益':<12} {'策略年化':<12} {'原始年化':<12} {'超额年化':<12}")
    print("-" * 110)
    
    for result in results_summary:
        print(f"{result['symbol']:<15} {result['name']:<12} {result['market']:<8} {result['total_return']:<12.2f}% {result['buy_hold_return']:<12.2f}% {result['excess_return']:<12.2f}% {result['annualized_return']:<12.2f}% {result['buy_hold_annual']:<12.2f}% {result['excess_annual']:<12.2f}%")
    
    print("-" * 110)
    print()
    
    # 保存汇总结果
    summary_df = pd.DataFrame(results_summary)
    summary_file = os.path.join(output_dir, 'summary.csv')
    summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    print(f"✓ 汇总结果已保存到: {summary_file}")
    print()
    
    # 统计成功的股票
    successful_stocks = [r for r in results_summary if r['status'] == '成功']
    if len(successful_stocks) > 0:
        print(f"✓ 成功回测的股票数量: {len(successful_stocks)}")
        
        # 找出表现最好的股票
        best_stock = max(successful_stocks, key=lambda x: x['total_return'])
        print(f"✓ 表现最好的股票: {best_stock['name']} ({best_stock['symbol']})（策略收益: {best_stock['total_return']:.2f}%）")
        
        # 找出夏普比率最高的股票
        best_sharpe = max(successful_stocks, key=lambda x: x['sharpe_ratio'])
        print(f"✓ 夏普比率最高的股票: {best_sharpe['name']} ({best_sharpe['symbol']})（夏普比率: {best_sharpe['sharpe_ratio']:.2f}）")
        
        # 找出胜率最高的股票
        best_win_rate = max(successful_stocks, key=lambda x: x['win_rate'])
        print(f"✓ 胜率最高的股票: {best_win_rate['name']} ({best_win_rate['symbol']})（胜率: {best_win_rate['win_rate']:.2f}%）")
        
        # 统计超额收益
        excess_positive = [r for r in successful_stocks if r['excess_return'] > 0]
        if len(excess_positive) > 0:
            print(f"✓ 策略跑赢原始涨幅的股票: {len(excess_positive)}/{len(successful_stocks)}")
            avg_excess = sum(r['excess_return'] for r in excess_positive) / len(excess_positive)
            print(f"✓ 平均超额收益: {avg_excess:.2f}%")
        else:
            print(f"⚠️  所有股票策略都未跑赢原始涨幅")
        
        # 绘制表现最好的股票的K线图
        print()
        print("=" * 80)
        print(f"正在绘制表现最好的股票 {best_stock['name']} 的K线图...")
        print("=" * 80)
        
        # 重新获取该股票的数据并生成信号
        try:
            best_stock_data = fetcher.fetch_stock_data(best_stock['symbol'], period=period, adjust='forward')
            
            if not isinstance(best_stock_data.index, pd.DatetimeIndex):
                best_stock_data.index = pd.to_datetime(best_stock_data.index, utc=True)
            else:
                best_stock_data.index = best_stock_data.index.tz_convert(None)
            
            best_stock_signals = strategy.generate_signals(best_stock_data)
            plot_kline_with_signals(best_stock_signals, best_stock['symbol'], best_stock['name'], output_dir)
            kline_file = os.path.join(output_dir, f'{best_stock["symbol"]}_kline.png')
            print(f"✓ K线图已保存到: {kline_file}")
        except Exception as e:
            print(f"✗ 绘制K线图失败: {e}")
    else:
        print("⚠️  没有股票产生交易信号，策略可能需要调整")
    
    print()
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


def plot_kline_with_signals(data: pd.DataFrame, symbol: str, name: str, output_dir: str = None):
    """
    绘制K线图并标记买卖点
    
    Args:
        data: 包含信号的数据
        symbol: 股票代码
        name: 股票名称
        output_dir: 输出目录
    """
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    
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
        title=f'{name} ({symbol}) - Daily Bollinger Strategy - Buy/Sell Signals',
        ylabel='Price (¥)',
        volume=True,
        addplot=apds,
        figsize=(16, 10),
        returnfig=True
    )
    
    # 添加图例
    axes[0].legend(['Upper Band', 'Middle Band', 'Lower Band'], loc='upper left')
    
    # 添加买卖点图例
    custom_lines = []
    if len(buy_markers.dropna()) > 0:
        custom_lines.append(Line2D([0], [0], marker='^', color='w', markerfacecolor='red', markersize=10, label='Buy Signal'))
    if len(sell_markers.dropna()) > 0:
        custom_lines.append(Line2D([0], [0], marker='v', color='w', markerfacecolor='green', markersize=10, label='Sell Signal'))
    
    if custom_lines:
        axes[0].legend(handles=custom_lines, loc='upper right')
    
    # 保存图片到指定目录
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{symbol}_kline.png')
    else:
        output_file = f'{symbol}_kline.png'
    
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ K线图已保存到: {output_file}")


def test_a_stock_interactive():
    """
    A股交互式K线图查看
    """
    print("=" * 80)
    print("A股交互式K线图查看")
    print("=" * 80)
    print()
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 测试股票
    symbol = '600519.SS'
    name = '贵州茅台'
    period = '1y'
    
    print(f"正在获取 {name} ({symbol}) 数据...")
    print()
    
    try:
        # 获取日线数据
        data = fetcher.fetch_stock_data(symbol, period=period, adjust='forward')
        
        # 确保索引是日期时间格式（统一时区）
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index, utc=True)
        else:
            data.index = data.index.tz_convert(None)
        
        print(f"✓ 数据获取成功: {len(data)} 条")
        print(f"时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
        print(f"最新收盘价: ¥{data['Close'].iloc[-1]:.2f}")
        print()
        
        # 创建策略
        strategy = DailyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
        
        # 生成信号
        data_with_signals = strategy.generate_signals(data)
        
        # 创建交互式K线图查看器
        print("正在创建交互式K线图...")
        print()
        print("操作说明：")
        print("  - 鼠标拖拽：左右移动K线")
        print("  - 鼠标滚轮：缩放K线数量")
        print("  - 鼠标悬停：查看详细信息")
        print("  - 红色向上箭头：买入点")
        print("  - 绿色向下箭头：卖出点")
        print()
        
        viewer = InteractiveKLineViewer(
            data=data_with_signals,
            title=f'{name} ({symbol}) - A股交互式K线图',
            signals=data_with_signals
        )
        viewer.show()
        
    except Exception as e:
        print(f"✗ 获取数据失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'interactive':
            test_a_stock_interactive()
        elif mode == 'backtest':
            test_a_stock_backtest()
        else:
            print("使用方法：")
            print("  python test_a_stock.py backtest    # 回测")
            print("  python test_a_stock.py interactive # 交互式查看")
    else:
        print("使用方法：")
        print("  python test_a_stock.py backtest    # 回测")
        print("  python test_a_stock.py interactive # 交互式查看")
        print()
        print("默认运行回测...")
        test_a_stock_backtest()
