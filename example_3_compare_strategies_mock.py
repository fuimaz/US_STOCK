import pandas as pd
import numpy as np
from datetime import datetime
from backtest_engine import BacktestEngine
from strategies import (
    MovingAverageStrategy,
    RSIStrategy,
    BollingerBandsStrategy,
    MACDStrategy
)

print("=" * 60)
print("示例：多策略对比回测（使用模拟数据）")
print("=" * 60)

def generate_mock_data(symbol: str, days: int = 500) -> pd.DataFrame:
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

# 获取数据
print("\n正在生成AAPL模拟数据...")
data = generate_mock_data('AAPL', days=500)
print(f"✓ 生成 {len(data)} 条数据")

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000, commission=0.001)

# 定义多个策略
strategies = [
    MovingAverageStrategy(short_period=5, long_period=20),
    RSIStrategy(period=14, overbought=70, oversold=30),
    BollingerBandsStrategy(period=20, std_dev=2),
    MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
]

print(f"\n正在对比 {len(strategies)} 个策略...")
print("-" * 80)

# 对比回测
results_list = []
for strategy in strategies:
    results = engine.run_backtest(data, strategy)
    results['strategy_name'] = strategy.name
    results_list.append(results)

# 打印对比结果
print(f"{'策略名称':<30} {'总收益率':<12} {'年化收益率':<12} {'夏普比率':<10} {'最大回撤':<10}")
print("-" * 80)

for results in results_list:
    print(f"{results['strategy_name']:<30} "
          f"{results['total_return_pct']:>10.2f}% "
          f"{results['annualized_return_pct']:>10.2f}% "
          f"{results['sharpe_ratio']:>10.2f} "
          f"{results['max_drawdown_pct']:>9.2f}%")

print("-" * 80)

# 找出最佳策略
best_strategy = max(results_list, key=lambda x: x['total_return_pct'])
print(f"\n🏆 最佳策略: {best_strategy['strategy_name']}")
print(f"   总收益率: {best_strategy['total_return_pct']:.2f}%")
print(f"   夏普比率: {best_strategy['sharpe_ratio']:.2f}")
print(f"   最大回撤: {best_strategy['max_drawdown_pct']:.2f}%")
print(f"   交易次数: {best_strategy['total_trades']}")

print("\n✓ 完成！")
