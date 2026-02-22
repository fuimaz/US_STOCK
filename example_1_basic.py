from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

print("=" * 60)
print("示例：获取单只股票数据并绘制K线图")
print("=" * 60)

# 初始化
fetcher = DataFetcher()
plotter = KLinePlotter(style='charles')

# 获取苹果公司1年数据
symbol = 'AAPL'
print(f"\n正在获取 {symbol} 的数据...")
data = fetcher.fetch_stock_data(symbol, period='1y')

print(f"✓ 成功获取 {len(data)} 条数据")
print(f"✓ 时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
print(f"✓ 最新收盘价: ${data['Close'].iloc[-1]:.2f}")

# 绘制K线图（带5日、10日、20日均线）
print(f"\n正在绘制K线图...")
plotter.plot_candlestick(data, title=f'{symbol} K线图', mav=[5, 10, 20])

print("\n✓ 完成！")
