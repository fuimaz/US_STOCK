import pandas as pd

# 加载数据
df = pd.read_csv('data_cache/china_futures/TA0_5min.csv')
df['DateTime'] = pd.to_datetime(df['datetime'])
df.set_index('DateTime', inplace=True)

# 查看2026-01-28 09:50附近的价格
print('2026-01-28 09:45-09:55的价格:')
print(df.loc['2026-01-28 09:45':'2026-01-28 09:55', ['close']])

# 检查数据精度
print('\n价格精度检查:')
print('Close类型:', df['close'].dtype)
print('价格示例:', df['close'].iloc[10:15].tolist())
