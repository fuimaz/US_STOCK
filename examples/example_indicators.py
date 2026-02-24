import pandas as pd
import numpy as np
from datetime import datetime
from kline_plotter import KLinePlotter

print("=" * 60)
print("示例：带有BOLL、成交量、RSI指标的K线图")
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

# 生成模拟数据
symbol = 'AAPL'
print(f"\n正在生成 {symbol} 的模拟数据...")
data = generate_mock_data(symbol, days=252)

print(f"✓ 成功生成 {len(data)} 条数据")
print(f"✓ 时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
print(f"✓ 最新收盘价: ${data['Close'].iloc[-1]:.2f}")
print(f"✓ 最高价: ${data['High'].max():.2f}")
print(f"✓ 最低价: ${data['Low'].min():.2f}")

# 绘制带有BOLL、成交量、RSI指标的K线图
print(f"\n正在绘制K线图（包含BOLL、成交量、RSI指标）...")
print("  - BOLL: 布林带（上轨、中轨、下轨）")
print("  - 成交量: 底部柱状图")
print("  - RSI: 相对强弱指标")

plotter.plot_with_indicators(
    data,
    title=f'{symbol} K线图（BOLL + 成交量 + RSI）',
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
print("  - 副图1：成交量柱状图")
print("  - 副图2：RSI指标（紫色曲线）")
