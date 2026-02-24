import pandas as pd
import numpy as np
from datetime import datetime
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

print("=" * 60)
print("示例：K线图切换日线、周线、月线")
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

# 初始化
fetcher = DataFetcher()
plotter = KLinePlotter(style='charles')

# 生成模拟数据
symbol = 'AAPL'
print(f"\n正在生成 {symbol} 的模拟数据...")
daily_data = generate_mock_data(symbol, days=500)

print(f"✓ 成功生成 {len(daily_data)} 条日线数据")
print(f"✓ 时间范围: {daily_data.index[0].date()} 到 {daily_data.index[-1].date()}")

# 转换为周线
print(f"\n正在转换为周线数据...")
weekly_data = fetcher.resample_data(daily_data, timeframe='1w')
print(f"✓ 周线数据: {len(weekly_data)} 条")

# 转换为月线
print(f"\n正在转换为月线数据...")
monthly_data = fetcher.resample_data(daily_data, timeframe='1m')
print(f"✓ 月线数据: {len(monthly_data)} 条")

print("\n" + "=" * 60)
print("数据对比")
print("=" * 60)
print(f"{'周期':<10} {'数据条数':<12} {'最新收盘价':<15} {'最高价':<15} {'最低价':<15}")
print("-" * 70)
print(f"{'日线':<10} {len(daily_data):<12} ${daily_data['Close'].iloc[-1]:>10.2f} ${daily_data['High'].max():>12.2f} ${daily_data['Low'].min():>12.2f}")
print(f"{'周线':<10} {len(weekly_data):<12} ${weekly_data['Close'].iloc[-1]:>10.2f} ${weekly_data['High'].max():>12.2f} ${weekly_data['Low'].min():>12.2f}")
print(f"{'月线':<10} {len(monthly_data):<12} ${monthly_data['Close'].iloc[-1]:>10.2f} ${monthly_data['High'].max():>12.2f} ${monthly_data['Low'].min():>12.2f}")
print("-" * 70)

# 绘制日线图
print("\n正在绘制日线K线图...")
plotter.plot_with_indicators(
    daily_data,
    title=f'{symbol} 日线K线图（BOLL + 成交量 + RSI）',
    show_boll=True,
    show_rsi=True,
    show_volume=True,
    boll_period=20,
    boll_std=2,
    rsi_period=14,
    figsize=(16, 12)
)

# 绘制周线图
print("\n正在绘制周线K线图...")
plotter.plot_with_indicators(
    weekly_data,
    title=f'{symbol} 周线K线图（BOLL + 成交量 + RSI）',
    show_boll=True,
    show_rsi=True,
    show_volume=True,
    boll_period=10,
    boll_std=2,
    rsi_period=14,
    figsize=(16, 12)
)

# 绘制月线图
print("\n正在绘制月线K线图...")
plotter.plot_with_indicators(
    monthly_data,
    title=f'{symbol} 月线K线图（BOLL + 成交量 + RSI）',
    show_boll=True,
    show_rsi=True,
    show_volume=True,
    boll_period=5,
    boll_std=2,
    rsi_period=14,
    figsize=(16, 12)
)

print("\n✓ 完成！")
print("\n图表说明：")
print("  - 日线图：显示每日的价格走势，适合短线分析")
print("  - 周线图：显示每周的价格走势，适合中线分析")
print("  - 月线图：显示每月的价格走势，适合长线分析")
print("\n每个图表都包含：")
print("  - K线图（红涨绿跌）")
print("  - 布林带（橙色：上下轨，蓝色：中轨）")
print("  - 成交量柱状图")
print("  - RSI指标（紫色曲线）")
