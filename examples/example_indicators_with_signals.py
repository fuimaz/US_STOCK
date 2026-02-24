import pandas as pd
import numpy as np
from datetime import datetime
from kline_plotter import KLinePlotter
from backtest_engine import BacktestEngine
from strategies import BollingerBandsStrategy

print("=" * 60)
print("示例：带有BOLL、成交量、RSI指标和交易信号的K线图")
print("=" * 60)

def generate_mock_data(symbol: str, days: int = 252) -> pd.DataFrame:
    """生成模拟股票数据"""
    np.random.seed(42)
    
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='D')
    
    close_prices = 150 * (1 + np.cumsum(np.random.normal(0, 0.02, days)))
    
    data = pd.DataFrame({
        'Open': close_prices * (1 + np.random.uniform(-0.01, 0.01, days)),
        'High': close_prices * (1 + np.random.uniform(0, 0.02, days)),
        'Low': close_prices * (1 + np.random.uniform(-0.02, 0, days)),
        'Close': close_prices,
        'Volume': np.random.randint(1000000, 50000000, days)
    }, index=dates)
    
    data.index.name = 'datetime'
    
    return data

# 初始化
plotter = KLinePlotter(style='charles')
engine = BacktestEngine(initial_capital=100000, commission=0.001)

# 生成模拟数据
symbol = 'AAPL'
print(f"\n正在生成 {symbol} 的模拟数据...")
data = generate_mock_data(symbol, days=252)

print(f"✓ 成功生成 {len(data)} 条数据")
print(f"✓ 时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
print(f"✓ 最新收盘价: ${data['Close'].iloc[-1]:.2f}")

# 使用布林带策略生成交易信号
strategy = BollingerBandsStrategy(period=20, std_dev=2)
print(f"✓ 策略: {strategy.name}")

# 运行回测
print(f"\n正在运行回测...")
results = engine.run_backtest(data, strategy)

# 打印回测结果
engine.print_results(results)

# 绘制带有指标的K线图和交易信号
print(f"\n正在绘制K线图（包含BOLL、成交量、RSI指标 + 交易信号）...")
print("  - BOLL: 布林带（上轨、中轨、下轨）")
print("  - 成交量: 底部柱状图")
print("  - RSI: 相对强弱指标")
print("  - 交易信号: 绿色三角=买入，红色三角=卖出")

# 获取交易信号
signals_df = strategy.generate_signals(data.copy())
buy_signals = signals_df['signal'] == 1
sell_signals = signals_df['signal'] == -1

# 绘制图表
plotter.plot_with_signals_and_indicators(
    data,
    buy_signals,
    sell_signals,
    title=f'{symbol} K线图（BOLL + 成交量 + RSI + 交易信号）',
    show_boll=True,
    show_rsi=True,
    show_volume=True,
    boll_period=20,
    boll_std=2,
    rsi_period=14,
    figsize=(16, 12)
)

print("\n✓ 完成！")
print("\n图表说明：")
print("  - 主图：K线图 + 布林带（橙色：上下轨，蓝色：中轨）")
print("         绿色三角：买入信号，红色三角：卖出信号")
print("  - 副图1：成交量柱状图")
print("  - 副图2：RSI指标（紫色曲线）")
print(f"\n回测结果：")
print(f"  - 总收益率: {results['total_return_pct']:.2f}%")
print(f"  - 总交易次数: {results['total_trades']}")
print(f"  - 夏普比率: {results['sharpe_ratio']:.2f}")
print(f"  - 最大回撤: {results['max_drawdown_pct']:.2f}%")
