import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy

print("=" * 60)
print("示例：移动平均线策略回测（使用模拟数据）")
print("=" * 60)

def generate_mock_data(symbol: str, days: int = 500) -> pd.DataFrame:
    """
    生成模拟股票数据
    
    Args:
        symbol: 股票代码
        days: 生成天数
    
    Returns:
        包含OHLCV数据的DataFrame
    """
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

# 获取数据
print("\n正在生成AAPL模拟数据...")
data = generate_mock_data('AAPL', days=500)
print(f"✓ 生成 {len(data)} 条数据")
print(f"✓ 时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
print(f"✓ 最新收盘价: ${data['Close'].iloc[-1]:.2f}")

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

# 显示交易记录
print("\n交易记录:")
print("-" * 80)
trades_df = results['trades']
if len(trades_df) > 0:
    print(trades_df.to_string())
else:
    print("没有交易记录")
print("-" * 80)

# 统计交易次数
buy_trades = len(trades_df[trades_df['type'] == 'buy'])
sell_trades = len(trades_df[trades_df['type'] == 'sell'])
print(f"\n买入次数: {buy_trades}")
print(f"卖出次数: {sell_trades}")

print("\n✓ 完成！")
