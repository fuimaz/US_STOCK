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

# 计算市场状态
daily_data['market_phase'] = '初始化'
valid_data = daily_data.dropna(subset=['Middle'])
daily_data.loc[valid_data.index, 'market_phase'] = valid_data.apply(
    lambda row: '上行期' if row['Close'] >= row['Lower'] else '下跌期',
    axis=1
)

# 查找下跌期之后突破上轨的情况
print("=" * 100)
print(f"{symbol} 下跌期后突破上轨的情况分析")
print("=" * 100)
print()

down_to_up_breaks = []
for i in range(period, len(daily_data)):
    prev_phase = daily_data['market_phase'].iloc[i-1]
    current_phase = daily_data['market_phase'].iloc[i]
    current_close = daily_data['Close'].iloc[i]
    current_upper = daily_data['Upper'].iloc[i]
    
    if prev_phase == '下跌期' and current_close > current_upper:
        down_to_up_breaks.append({
            'date': daily_data.index[i],
            'close': current_close,
            'upper': current_upper,
            'middle': daily_data['Middle'].iloc[i],
            'lower': daily_data['Lower'].iloc[i]
        })

print(f"下跌期后突破上轨的次数: {len(down_to_up_breaks)}")
print()

if len(down_to_up_breaks) > 0:
    print("所有下跌期后突破上轨的情况：")
    print("-" * 100)
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
        break_idx = daily_data.index.get_loc(break_date)
        
        # 检查突破后30天内是否有回落到中线附近
        found_near_middle = False
        for j in range(break_idx + 1, min(break_idx + 30, len(daily_data))):
            close = daily_data['Close'].iloc[j]
            middle = daily_data['Middle'].iloc[j]
            threshold = middle * 0.02
            
            if abs(close - middle) <= threshold:
                found_near_middle = True
                print(f"{i+1}. {break_date.strftime('%Y-%m-%d')} 突破后，{daily_data.index[j].strftime('%Y-%m-%d')} 回落到中线附近: 收盘价 ${close:.2f} | 中线 ${middle:.2f} | 偏差 {abs(close - middle):.2f}")
                break
        
        if not found_near_middle:
            print(f"{i+1}. {break_date.strftime('%Y-%m-%d')} 突破后30天内未回落到中线附近")
    print("-" * 100)
else:
    print("没有找到下跌期后突破上轨的情况")
    print()
    print("分析原因：")
    print("-" * 100)
    print("1. 下跌期天数较少，大部分时间在上行期")
    print("2. 下跌期后价格可能没有突破上轨")
    print("3. 策略条件过于严格")
    print("-" * 100)

print()
print("建议：")
print("-" * 100)
print("1. 调整布林带周期参数（如改为10日或15日）")
print("2. 调整标准差倍数（如改为1.5或2.5）")
print("3. 放宽买入条件（如允许在上行期买入）")
print("4. 使用更宽松的市场状态定义")
print("-" * 100)
