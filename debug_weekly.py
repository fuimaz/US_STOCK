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

# 转换为周线数据
weekly_df = daily_data.resample('W').agg({
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'
}).dropna()

# 计算布林带
period = 20
std_dev = 2

weekly_df['Middle'] = weekly_df['Close'].rolling(window=period).mean()
weekly_df['Upper'] = weekly_df['Middle'] + weekly_df['Close'].rolling(window=period).std() * std_dev
weekly_df['Lower'] = weekly_df['Middle'] - weekly_df['Close'].rolling(window=period).std() * std_dev

# 计算市场状态
weekly_df['market_phase'] = '初始化'
valid_weekly = weekly_df.dropna(subset=['Middle'])
weekly_df.loc[valid_weekly.index, 'market_phase'] = valid_weekly.apply(
    lambda row: '上行期' if row['Close'] >= row['Lower'] else '下跌期',
    axis=1
)

print("=" * 100)
print(f"{symbol} 周线数据分析")
print("=" * 100)
print()
print(f"总周数: {len(weekly_df)}")
print(f"有效周数: {len(valid_weekly)}")
print()

# 统计市场状态
up_phase = (valid_weekly['Close'] >= valid_weekly['Lower']).sum()
down_phase = (valid_weekly['Close'] < valid_weekly['Lower']).sum()
print(f"上行期周数: {up_phase}")
print(f"下跌期周数: {down_phase}")
print(f"上行期占比: {up_phase / len(valid_weekly) * 100:.2f}%")
print()

# 显示最近50周数据
print("最近50周数据：")
print("-" * 100)
print(f"{'日期':<12} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10} {'市场状态':<10}")
print("-" * 100)
for i in range(max(0, len(weekly_df) - 50), len(weekly_df)):
    idx = weekly_df.index[i]
    close = weekly_df['Close'].iloc[i]
    middle = weekly_df['Middle'].iloc[i]
    upper = weekly_df['Upper'].iloc[i]
    lower = weekly_df['Lower'].iloc[i]
    market_phase = weekly_df['market_phase'].iloc[i]
    
    if pd.isna(middle):
        market_phase = '初始化'
    
    print(f"{idx.strftime('%Y-%m-%d'):<12} {close:<10.2f} {middle:<10.2f} {upper:<10.2f} {lower:<10.2f} {market_phase:<10}")
print("-" * 100)
print()

# 查找下跌期后突破上轨的情况
print("下跌期后突破上轨的情况：")
print("-" * 100)
down_to_up_breaks = []
for i in range(period, len(weekly_df)):
    prev_phase = weekly_df['market_phase'].iloc[i-1]
    current_phase = weekly_df['market_phase'].iloc[i]
    current_close = weekly_df['Close'].iloc[i]
    current_upper = weekly_df['Upper'].iloc[i]
    
    if prev_phase == '下跌期' and current_close > current_upper:
        down_to_up_breaks.append({
            'date': weekly_df.index[i],
            'close': current_close,
            'upper': current_upper,
            'middle': weekly_df['Middle'].iloc[i],
            'lower': weekly_df['Lower'].iloc[i]
        })

print(f"下跌期后突破上轨的次数: {len(down_to_up_breaks)}")
print()

if len(down_to_up_breaks) > 0:
    print("所有下跌期后突破上轨的情况：")
    for i, break_info in enumerate(down_to_up_breaks):
        idx = break_info['date']
        close = break_info['close']
        upper = break_info['upper']
        middle = break_info['middle']
        lower = break_info['lower']
        print(f"{i+1}. {idx.strftime('%Y-%m-%d')}: 收盘价 ${close:.2f} > 上轨 ${upper:.2f} | 中线 ${middle:.2f} | 下轨 ${lower:.2f}")
    print("-" * 100)
    print()
    
    # 检查突破后回落到中线附近的情况
    print("突破后回落到中线附近的情况（阈值2%）：")
    print("-" * 100)
    for i, break_info in enumerate(down_to_up_breaks):
        break_date = break_info['date']
        break_idx = weekly_df.index.get_loc(break_date)
        
        # 检查突破后10周内是否有回落到中线附近
        found_near_middle = False
        for j in range(break_idx + 1, min(break_idx + 10, len(weekly_df))):
            close = weekly_df['Close'].iloc[j]
            middle = weekly_df['Middle'].iloc[j]
            threshold = middle * 0.02
            
            if abs(close - middle) <= threshold:
                found_near_middle = True
                print(f"{i+1}. {break_date.strftime('%Y-%m-%d')} 突破后，{weekly_df.index[j].strftime('%Y-%m-%d')} 回落到中线附近: 收盘价 ${close:.2f} | 中线 ${middle:.2f} | 偏差 {abs(close - middle):.2f}")
                break
        
        if not found_near_middle:
            print(f"{i+1}. {break_date.strftime('%Y-%m-%d')} 突破后10周内未回落到中线附近")
    print("-" * 100)
