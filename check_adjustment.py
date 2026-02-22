import requests
import pandas as pd

api_key = "c06d1a5f78f7429c941a8a6cce1aee0e"
symbol = "AAPL"

url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=5&apikey={api_key}"

response = requests.get(url)
result = response.json()

print("=" * 60)
print("Twelve Data API 数据结构分析")
print("=" * 60)

print(f"\n完整响应:")
import json
print(json.dumps(result, indent=2))

if 'values' in result and result['values']:
    print(f"\n第一条数据:")
    first_data = result['values'][0]
    for key, value in first_data.items():
        print(f"  {key}: {value}")

print("\n" + "=" * 60)
print("数据类型分析")
print("=" * 60)

print("\nTwelve Data API 默认返回的是:")
print("  - 不复权数据（原始价格）")
print("  - 不包含复权因子")
print("  - 不包含分红、拆股信息")

print("\n如果需要复权数据，需要:")
print("  1. 使用其他API（如yfinance支持复权参数）")
print("  2. 手动计算复权价格（需要拆股、分红历史）")
print("  3. 使用专业金融数据源")

print("\n" + "=" * 60)