import pandas as pd
from data_fetcher import DataFetcher

fetcher = DataFetcher(cache_dir='data_cache', cache_days=0)

print("正在获取AAPL的模拟数据...")
data = fetcher.fetch_stock_data('AAPL', period='1y', interval='1d', use_cache=False)

print(f"\n数据统计:")
print(f"数据条数: {len(data)}")
print(f"时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
print(f"最新收盘价: ${data['Close'].iloc[-1]:.2f}")
print(f"最高价: ${data['High'].max():.2f}")
print(f"最低价: ${data['Low'].min():.2f}")
print(f"平均价: ${data['Close'].mean():.2f}")

print(f"\n最近5天的数据:")
print(data[['Open', 'High', 'Low', 'Close']].tail())