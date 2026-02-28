#!/usr/bin/env python
"""检查跳空低开导致的超损情况"""
import pandas as pd
import os

# 检查301018.SZ在2025年4月7日附近的数据
symbol = '301018.SZ'
period = '60min'
filepath = f'data_cache/a_stock_minute/{symbol}_{period}.csv'

if not os.path.exists(filepath):
    print(f"文件不存在: {filepath}")
    exit(1)

df = pd.read_csv(filepath)
df['datetime'] = pd.to_datetime(df['datetime'])

# 查看2025年4月7日前后的数据
print('=' * 80)
print(f'【{symbol} 2025年4月7日前后数据】')
print('=' * 80)
mask = (df['datetime'] >= '2025-04-01') & (df['datetime'] <= '2025-04-10')
data = df[mask][['datetime', 'open', 'high', 'low', 'close', 'volume']]
print(data.to_string())

print()
print('=' * 80)
print('【分析跳空情况】')
print('=' * 80)

# 计算跳空
data_copy = data.copy()
data_copy['prev_close'] = data_copy['close'].shift(1)
data_copy['gap_pct'] = (data_copy['open'] / data_copy['prev_close'] - 1) * 100
data_copy['low_vs_prev_close'] = (data_copy['low'] / data_copy['prev_close'] - 1) * 100

for _, row in data_copy.iterrows():
    if pd.notna(row['gap_pct']):
        print(f"{row['datetime']}: 开盘跳空 {row['gap_pct']:+.2f}%, 最低价较前收 {row['low_vs_prev_close']:+.2f}%")

# 查看交易记录
print()
print('=' * 80)
print('【交易记录】')
print('=' * 80)
trades_file = f'results/volume_breakout_minute/{symbol}_trades.csv'
if os.path.exists(trades_file):
    trades = pd.read_csv(trades_file)
    for _, trade in trades.iterrows():
        if '2025-04-01' <= str(trade['date']) <= '2025-04-15':
            print(f"{trade['date']}: {trade['type']}, 价格{trade['price']:.2f}, 原因: {trade['reason']}")
