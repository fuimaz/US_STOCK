from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

print("=" * 60)
print("示例：多只股票对比")
print("=" * 60)

# 初始化
fetcher = DataFetcher()
plotter = KLinePlotter(style='charles')

# 获取多只股票数据
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
print(f"\n正在获取 {len(symbols)} 只股票的数据...")

data_dict = fetcher.fetch_multiple_stocks(symbols, period='1y')

print(f"\n✓ 成功获取 {len(data_dict)} 只股票的数据:")
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
