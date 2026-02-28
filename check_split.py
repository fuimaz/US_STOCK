#!/usr/bin/env python
"""检查股票拆分/复权问题"""
import pandas as pd
import os

# 检查比亚迪的数据文件
symbol = '002594.SZ'
period = '60min'
filepath = f'data_cache/a_stock_minute/{symbol}_{period}.csv'

if not os.path.exists(filepath):
    print(f"文件不存在: {filepath}")
    exit(1)

df = pd.read_csv(filepath)
df['datetime'] = pd.to_datetime(df['datetime'])

# 查看2025年7月29日前后的数据
print('=== 比亚迪 002594.SZ 2025年7月29日前后数据 ===')
print()
mask = (df['datetime'] >= '2025-07-25') & (df['datetime'] <= '2025-08-05')
data = df[mask][['datetime', 'open', 'high', 'low', 'close', 'volume']]
print(data.to_string())
print()

# 计算价格变化率
print('=== 价格变化分析 ===')
data_copy = data.copy()
data_copy['prev_close'] = data_copy['close'].shift(1)
data_copy['price_change_pct'] = (data_copy['close'] / data_copy['prev_close'] - 1) * 100
print(data_copy[['datetime', 'close', 'prev_close', 'price_change_pct']].to_string())
print()

# 检查2024年是否有拆分
print('=== 检查2024年是否有大幅价格跳跃 ===')
mask_2024 = (df['datetime'] >= '2024-01-01') & (df['datetime'] <= '2024-12-31')
df_2024 = df[mask_2024].copy()
df_2024['prev_close'] = df_2024['close'].shift(1)
df_2024['jump_pct'] = abs(df_2024['close'] / df_2024['prev_close'] - 1) * 100
jumps = df_2024[df_2024['jump_pct'] > 20]  # 单日变化超过20%
if len(jumps) > 0:
    print("发现大幅价格跳跃(>20%):")
    print(jumps[['datetime', 'close', 'prev_close', 'jump_pct']].head(10).to_string())
else:
    print("2024年未发现单日>20%的价格跳跃")
