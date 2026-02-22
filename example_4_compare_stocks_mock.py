import pandas as pd
import numpy as np
from datetime import datetime
from kline_plotter import KLinePlotter

print("=" * 60)
print("示例：多只股票对比（使用模拟数据）")
print("=" * 60)

def generate_mock_data(symbol: str, days: int = 252) -> pd.DataFrame:
    """生成模拟股票数据"""
    np.random.seed(hash(symbol) % 1000)
    
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='D')
    
    base_price = 100 + np.random.randint(0, 100)
    close_prices = base_price * (1 + np.cumsum(np.random.normal(0, 0.02, days)))
    
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

# 获取多只股票数据
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
print(f"\n正在生成 {len(symbols)} 只股票的模拟数据...")

data_dict = {}
for symbol in symbols:
    data_dict[symbol] = generate_mock_data(symbol, days=252)

print(f"\n✓ 成功生成 {len(data_dict)} 只股票的数据:")
print("-" * 60)
for symbol, data in data_dict.items():
    print(f"  {symbol:<8} {len(data):>4} 条数据  最新价格: ${data['Close'].iloc[-1]:>8.2f}")
print("-" * 60)

# 绘制对比图（归一化）
print("\n正在绘制对比图...")
plotter.plot_comparison(
    data_dict,
    title='科技股对比 (归一化)',
    normalize=True
)

print("\n✓ 完成！")
