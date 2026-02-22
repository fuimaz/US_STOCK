from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy
from kline_plotter import KLinePlotter

print("=" * 60)
print("示例：移动平均线策略回测")
print("=" * 60)

# 获取数据
fetcher = DataFetcher()
print("\n正在获取AAPL数据...")
data = fetcher.fetch_stock_data('AAPL', period='2y')
print(f"✓ 获取到 {len(data)} 条数据")

# 创建回测引擎（初始资金10万，手续费0.1%）
engine = BacktestEngine(initial_capital=100000, commission=0.001)

# 创建策略（5日均线和20日均线）
strategy = MovingAverageStrategy(short_period=5, long_period=20)
print(f"✓ 策略: {strategy.name}")

# 运行回测
print("\n正在运行回测...")
results = engine.run_backtest(data, strategy)

# 打印结果
engine.print_results(results)

# 绘制带信号的K线图
print("\n正在绘制交易信号图...")
plotter = KLinePlotter()
signals_df = strategy.generate_signals(data.copy())
buy_signals = signals_df['signal'] == 1
sell_signals = signals_df['signal'] == -1

plotter.plot_with_signals(
    data,
    buy_signals,
    sell_signals,
    title='AAPL 移动平均线策略交易信号',
    mav=[5, 20]
)

# 绘制绩效曲线
print("正在绘制绩效曲线...")
plotter.plot_performance(
    results['equity_curve']['equity'],
    benchmark=data['Close'],
    title='策略绩效 vs 基准'
)

print("\n✓ 完成！")
