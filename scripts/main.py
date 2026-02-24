from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy, RSIStrategy, BollingerBandsStrategy, MACDStrategy


def example_fetch_and_plot():
    """示例：获取数据并绘制K线图"""
    print("示例1：获取AAPL数据并绘制K线图")
    print("-" * 50)
    
    fetcher = DataFetcher()
    plotter = KLinePlotter(style='charles')
    
    data = fetcher.fetch_stock_data('AAPL', period='1y')
    print(f"获取到 {len(data)} 条数据")
    print(f"数据时间范围: {data.index[0]} 到 {data.index[-1]}")
    print(f"最新收盘价: ${data['Close'].iloc[-1]:.2f}")
    
    plotter.plot_candlestick(data, title='AAPL - 苹果公司 K线图', mav=[5, 10, 20])


def example_backtest():
    """示例：策略回测"""
    print("\n示例2：移动平均线策略回测")
    print("-" * 50)
    
    fetcher = DataFetcher()
    engine = BacktestEngine(initial_capital=100000, commission=0.001)
    plotter = KLinePlotter(style='charles')
    
    data = fetcher.fetch_stock_data('AAPL', period='2y')
    
    strategy = MovingAverageStrategy(short_period=5, long_period=20)
    
    results = engine.run_backtest(data, strategy)
    engine.print_results(results)
    
    signals_df = strategy.generate_signals(data.copy())
    buy_signals = signals_df['signal'] == 1
    sell_signals = signals_df['signal'] == -1
    
    plotter.plot_with_signals(
        data,
        buy_signals,
        sell_signals,
        title='AAPL - 移动平均线策略交易信号',
        mav=[5, 20]
    )
    
    plotter.plot_performance(
        results['equity_curve']['equity'],
        benchmark=data['Close'],
        title='策略绩效 vs 基准'
    )


def example_multiple_strategies():
    """示例：多策略对比"""
    print("\n示例3：多策略对比回测")
    print("-" * 50)
    
    fetcher = DataFetcher()
    engine = BacktestEngine(initial_capital=100000, commission=0.001)
    
    data = fetcher.fetch_stock_data('AAPL', period='2y')
    
    strategies = [
        MovingAverageStrategy(short_period=5, long_period=20),
        RSIStrategy(period=14, overbought=70, oversold=30),
        BollingerBandsStrategy(period=20, std_dev=2),
        MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
    ]
    
    results_list = []
    for strategy in strategies:
        results = engine.run_backtest(data, strategy)
        results['strategy_name'] = strategy.name
        results_list.append(results)
        engine.print_results(results)
    
    print("\n策略对比汇总:")
    print("-" * 80)
    print(f"{'策略名称':<20} {'总收益率':<12} {'年化收益率':<12} {'夏普比率':<10} {'最大回撤':<10}")
    print("-" * 80)
    for results in results_list:
        print(f"{results['strategy_name']:<20} "
              f"{results['total_return_pct']:>10.2f}% "
              f"{results['annualized_return_pct']:>10.2f}% "
              f"{results['sharpe_ratio']:>10.2f} "
              f"{results['max_drawdown_pct']:>9.2f}%")
    print("-" * 80)


def example_multiple_stocks():
    """示例：多只股票对比"""
    print("\n示例4：多只股票对比")
    print("-" * 50)
    
    fetcher = DataFetcher()
    plotter = KLinePlotter(style='charles')
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    data_dict = fetcher.fetch_multiple_stocks(symbols, period='1y')
    
    print(f"成功获取 {len(data_dict)} 只股票的数据")
    for symbol, data in data_dict.items():
        print(f"{symbol}: {len(data)} 条数据, 最新价格 ${data['Close'].iloc[-1]:.2f}")
    
    plotter.plot_comparison(data_dict, title='科技股对比 (归一化)', normalize=True)


def example_stock_info():
    """示例：获取股票信息"""
    print("\n示例5：获取股票基本信息")
    print("-" * 50)
    
    fetcher = DataFetcher()
    
    symbol = 'AAPL'
    info = fetcher.get_stock_info(symbol)
    
    print(f"股票代码: {symbol}")
    print(f"公司名称: {info['name']}")
    print(f"行业: {info['industry']}")
    print(f"板块: {info['sector']}")
    print(f"市值: ${info['market_cap']:,.0f}")
    print(f"当前价格: ${info['current_price']:.2f}")
    print(f"前收盘价: ${info['previous_close']:.2f}")


if __name__ == "__main__":
    print("=" * 50)
    print("美股K线数据获取、绘制和回测系统")
    print("=" * 50)
    
    example_stock_info()
    example_fetch_and_plot()
    example_backtest()
    example_multiple_strategies()
    example_multiple_stocks()
    
    print("\n" + "=" * 50)
    print("所有示例运行完成！")
    print("=" * 50)
