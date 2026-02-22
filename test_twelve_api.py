import requests
import os

api_key = "c06d1a5f78f7429c941a8a6cce1aee0"

print("=" * 60)
print("Twelve Data API 测试")
print("=" * 60)

print(f"\nAPI密钥: {api_key}")
print(f"密钥长度: {len(api_key)}")

url = f"https://api.twelvedata.com/time_series?symbol=AAPL&interval=1day&outputsize=5&apikey={api_key}"

print(f"\n请求URL: {url}")

try:
    response = requests.get(url)
    print(f"\n状态码: {response.status_code}")
    
    result = response.json()
    print(f"\n响应内容:")
    import json
    print(json.dumps(result, indent=2))
    
    if 'status' in result:
        print(f"\n状态: {result['status']}")
        if result['status'] == 'error':
            print(f"错误信息: {result.get('message', '未知错误')}")
    
    if 'values' in result:
        print(f"\n✓ 成功获取数据！")
        print(f"数据条数: {len(result['values'])}")
        
except Exception as e:
    print(f"\n✗ 请求失败: {e}")

print("\n" + "=" * 60)