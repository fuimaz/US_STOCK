import pandas as pd
import numpy as np
from data_fetcher import DataFetcher

# 初始化数据获取器
fetcher = DataFetcher(
    cache_dir='data_cache',
    cache_days=365,
    proxy='http://127.0.0.1:7897',
    retry_count=5,
    retry_delay=5.0
)

# 获取数据
symbol = 'AAPL'
period = '5y'

daily_data = fetcher.fetch_stock_data(symbol, period=period, adjust='forward')

# 确保索引是日期时间格式（统一时区）
if not isinstance(daily_data.index, pd.DatetimeIndex):
    daily_data.index = pd.to_datetime(daily_data.index, utc=True)
else:
    daily_data.index = daily_data.index.tz_convert(None)

# 计算布林带
period = 20
std_dev = 2

daily_data['Middle'] = daily_data['Close'].rolling(window=period).mean()
daily_data['Upper'] = daily_data['Middle'] + daily_data['Close'].rolling(window=period).std() * std_dev
daily_data['Lower'] = daily_data['Middle'] - daily_data['Close'].rolling(window=period).std() * std_dev

# 显示最近50条数据
print("=" * 100)
print(f"{symbol} 布林带数据检查")
print("=" * 100)
print()
print("最近50条数据：")
print("-" * 100)
print(f"{'日期':<12} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10} {'市场状态':<10}")
print("-" * 100)

for i in range(max(0, len(daily_data) - 50), len(daily_data)):
    idx = daily_data.index[i]
    close = daily_data['Close'].iloc[i]
    middle = daily_data['Middle'].iloc[i]
    upper = daily_data['Upper'].iloc[i]
    lower = daily_data['Lower'].iloc[i]
    
    if pd.isna(middle):
        market_phase = '初始化'
    elif close >= lower:
        market_phase = '上行期'
    else:
        market_phase = '下跌期'
    
    print(f"{idx.strftime('%Y-%m-%d'):<12} {close:<10.2f} {middle:<10.2f} {upper:<10.2f} {lower:<10.2f} {market_phase:<10}")

print("-" * 100)
print()

# 统计市场状态
print("市场状态统计：")
print("-" * 100)
valid_data = daily_data.dropna(subset=['Middle'])
up_phase = (valid_data['Close'] >= valid_data['Lower']).sum()
down_phase = (valid_data['Close'] < valid_data['Lower']).sum()
print(f"上行期天数: {up_phase}")
print(f"下跌期天数: {down_phase}")
print(f"上行期占比: {up_phase / len(valid_data) * 100:.2f}%")
print("-" * 100)
print()

# 检查是否有突破上轨的情况
print("突破上轨的情况：")
print("-" * 100)
break_upper = valid_data[valid_data['Close'] > valid_data['Upper']]
print(f"突破上轨次数: {len(break_upper)}")
if len(break_upper) > 0:
    print("最近10次突破上轨：")
    for i in range(max(0, len(break_upper) - 10), len(break_upper)):
        idx = break_upper.index[i]
        close = break_upper['Close'].iloc[i]
        upper = break_upper['Upper'].iloc[i]
        print(f"  {idx.strftime('%Y-%m-%d')}: 收盘价 ${close:.2f} > 上轨 ${upper:.2f}")
print("-" * 100)
