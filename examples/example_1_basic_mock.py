import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from kline_plotter import KLinePlotter

print("=" * 60)
print("示例：获取单只股票数据并绘制K线图（使用模拟数据）")
print("=" * 60)

def generate_mock_data(symbol: str, days: int = 252) -> pd.DataFrame:
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

# 初始化
plotter = KLinePlotter(style='charles')

# 生成模拟数据
symbol = 'AAPL'
print(f"\n正在生成 {symbol} 的模拟数据...")
data = generate_mock_data(symbol, days=252)

print(f"✓ 成功生成 {len(data)} 条数据")
print(f"✓ 时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
print(f"✓ 最新收盘价: ${data['Close'].iloc[-1]:.2f}")
print(f"✓ 最高价: ${data['High'].max():.2f}")
print(f"✓ 最低价: ${data['Low'].min():.2f}")

# 绘制K线图（带5日、10日、20日均线）
print(f"\n正在绘制K线图...")
plotter.plot_candlestick(data, title=f'{symbol} K线图（模拟数据）', mav=[5, 10, 20])

print("\n✓ 完成！")
