"""
交互式K线图示例

演示如何使用交互式K线图查看器
"""

from data_fetcher import DataFetcher
from interactive_kline import InteractiveKLineViewer


def example_daily():
    """示例：日线图"""
    print("=" * 60)
    print("交互式K线图查看器 - 日线图示例")
    print("=" * 60)
    
    # 初始化
    fetcher = DataFetcher(cache_dir='data_cache', cache_days=1)
    
    # 获取数据
    print("\n正在获取 AAPL 的日线数据...")
    daily_data = fetcher.fetch_stock_data('AAPL', period='1y')
    
    print(f"✓ 成功获取 {len(daily_data)} 条日线数据")
    print(f"✓ 时间范围: {daily_data.index[0].date()} 到 {daily_data.index[-1].date()}")
    
    # 创建交互式查看器
    print(f"\n正在创建交互式图表...")
    print(f"\n操作说明：")
    print(f"  - 鼠标拖拽：左右移动K线")
    print(f"  - 鼠标滚轮：缩放K线数量")
    print(f"  - 鼠标悬停/点击：查看详细信息（包括BOLL和RSI）")
    
    viewer = InteractiveKLineViewer(daily_data, title='AAPL 日线交互式K线图')
    viewer.show()


def example_weekly():
    """示例：周线图"""
    print("=" * 60)
    print("交互式K线图查看器 - 周线图示例")
    print("=" * 60)
    
    # 初始化
    fetcher = DataFetcher(cache_dir='data_cache', cache_days=1)
    
    # 获取日线数据
    print("\n正在获取 MSFT 的日线数据...")
    daily_data = fetcher.fetch_stock_data('MSFT', period='1y')
    
    print(f"✓ 成功获取 {len(daily_data)} 条日线数据")
    
    # 转换为周线
    print(f"\n正在转换为周线数据...")
    weekly_data = fetcher.resample_data(daily_data, timeframe='1w')
    
    print(f"✓ 成功转换为 {len(weekly_data)} 条周线数据")
    print(f"✓ 时间范围: {weekly_data.index[0].date()} 到 {weekly_data.index[-1].date()}")
    
    # 创建交互式查看器
    print(f"\n正在创建交互式图表...")
    print(f"\n操作说明：")
    print(f"  - 鼠标拖拽：左右移动K线")
    print(f"  - 鼠标滚轮：缩放K线数量")
    print(f"  - 鼠标悬停/点击：查看详细信息（包括BOLL和RSI）")
    
    viewer = InteractiveKLineViewer(weekly_data, title='MSFT 周线交互式K线图')
    viewer.show()


def example_monthly():
    """示例：月线图"""
    print("=" * 60)
    print("交互式K线图查看器 - 月线图示例")
    print("=" * 60)
    
    # 初始化
    fetcher = DataFetcher(cache_dir='data_cache', cache_days=1)
    
    # 获取日线数据
    print("\n正在获取 GOOGL 的日线数据...")
    daily_data = fetcher.fetch_stock_data('GOOGL', period='2y')
    
    print(f"✓ 成功获取 {len(daily_data)} 条日线数据")
    
    # 转换为月线
    print(f"\n正在转换为月线数据...")
    monthly_data = fetcher.resample_data(daily_data, timeframe='1m')
    
    print(f"✓ 成功转换为 {len(monthly_data)} 条月线数据")
    print(f"✓ 时间范围: {monthly_data.index[0].date()} 到 {monthly_data.index[-1].date()}")
    
    # 创建交互式查看器
    print(f"\n正在创建交互式图表...")
    print(f"\n操作说明：")
    print(f"  - 鼠标拖拽：左右移动K线")
    print(f"  - 鼠标滚轮：缩放K线数量")
    print(f"  - 鼠标悬停/点击：查看详细信息（包括BOLL和RSI）")
    
    viewer = InteractiveKLineViewer(monthly_data, title='GOOGL 月线交互式K线图')
    viewer.show()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'daily':
            example_daily()
        elif mode == 'weekly':
            example_weekly()
        elif mode == 'monthly':
            example_monthly()
        else:
            print(f"未知模式: {mode}")
            print("可用模式: daily, weekly, monthly")
    else:
        print("请指定模式:")
        print("  python example_interactive.py daily    # 日线图")
        print("  python example_interactive.py weekly   # 周线图")
        print("  python example_interactive.py monthly  # 月线图")
