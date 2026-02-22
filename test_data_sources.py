import os
from data_fetcher import DataFetcher

print("=" * 60)
print("数据源配置检查")
print("=" * 60)

# 检查环境变量
print("\n环境变量配置:")
print(f"  ALPHA_VANTAGE_API_KEY: {'已设置' if os.environ.get('ALPHA_VANTAGE_API_KEY') else '未设置'}")
print(f"  POLYGON_API_KEY: {'已设置' if os.environ.get('POLYGON_API_KEY') else '未设置'}")
print(f"  TWELVE_DATA_API_KEY: {'已设置' if os.environ.get('TWELVE_DATA_API_KEY') else '未设置'}")

print("\n" + "=" * 60)
print("数据源可用性测试")
print("=" * 60)

fetcher = DataFetcher(cache_dir='data_cache', cache_days=0)

# 测试获取AAPL数据
print("\n正在测试获取 AAPL 数据...")
try:
    data = fetcher.fetch_stock_data('AAPL', period='1y', use_cache=False)
    print(f"\n✓ 成功获取数据！")
    print(f"  数据条数: {len(data)}")
    print(f"  时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"  最新收盘价: ${data['Close'].iloc[-1]:.2f}")
    print(f"  最高价: ${data['High'].max():.2f}")
    print(f"  最低价: ${data['Low'].min():.2f}")
except Exception as e:
    print(f"\n✗ 获取数据失败: {e}")
    print("\n建议:")
    print("  1. 配置至少一个备用数据源的API密钥")
    print("  2. 查看 API_KEYS.md 了解如何配置")
    print("  3. 等待yfinance限流解除后重试")

print("\n" + "=" * 60)