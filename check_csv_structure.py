"""
查看CSV文件结构
"""
import pandas as pd

filepath = 'data_cache/600519.SS_20y_1d_forward.csv'

print(f"查看文件: {filepath}")
print()

# 读取前几行
data = pd.read_csv(filepath, nrows=5)
print("前5行数据:")
print(data)
print()

print("列名:")
print(data.columns.tolist())
print()

# 尝试读取完整数据
try:
    data = pd.read_csv(filepath, index_col='Date', parse_dates=True)
    print(f"✓ 成功读取数据，共 {len(data)} 条记录")
except Exception as e:
    print(f"✗ 读取失败: {e}")
    import traceback
    traceback.print_exc()