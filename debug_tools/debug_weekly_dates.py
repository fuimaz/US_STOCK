import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from weekly_boll_strategy import WeeklyBollingerStrategy


def debug_weekly_dates():
    """
    调试周线日期匹配
    """
    print("=" * 80)
    print("调试周线日期匹配")
    print("=" * 80)
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 获取AAPL数据
    symbol = 'AAPL'
    period = '20y'
    
    print(f"\n正在获取 {symbol} 数据...")
    daily_data = fetcher.fetch_stock_data(symbol, period=period, adjust='forward')
    
    # 确保索引是日期时间格式（统一时区）
    if not isinstance(daily_data.index, pd.DatetimeIndex):
        daily_data.index = pd.to_datetime(daily_data.index, utc=True)
    else:
        daily_data.index = daily_data.index.tz_convert(None)
    
    print(f"✓ 数据获取成功: {len(daily_data)} 条")
    
    # 创建策略
    strategy = WeeklyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
    
    # 转换为周线数据
    weekly_df = strategy._resample_to_weekly(daily_data)
    
    print(f"\n周线数据统计:")
    print(f"  总周数: {len(weekly_df)}")
    print(f"  周线数据索引类型: {type(weekly_df.index)}")
    print(f"  周线数据索引频率: {weekly_df.index.freq}")
    
    # 显示最近10周的数据
    print(f"\n最近10周数据:")
    print("-" * 80)
    print(f"{'周线日期':<12} {'星期':<6} {'收盘价':<10}")
    print("-" * 80)
    
    for idx, row in weekly_df.tail(10).iterrows():
        weekday = idx.strftime('%A')
        print(f"{idx.strftime('%Y-%m-%d'):<12} {weekday:<6} {row['Close']:<10.2f}")
    
    print("-" * 80)
    
    # 显示最近10天的日线数据
    print(f"\n最近10天日线数据:")
    print("-" * 80)
    print(f"{'日线日期':<12} {'星期':<6} {'收盘价':<10}")
    print("-" * 80)
    
    for idx, row in daily_data.tail(10).iterrows():
        weekday = idx.strftime('%A')
        print(f"{idx.strftime('%Y-%m-%d'):<12} {weekday:<6} {row['Close']:<10.2f}")
    
    print("-" * 80)
    
    # 检查日期匹配
    print(f"\n日期匹配检查:")
    print("-" * 80)
    
    for idx, row in weekly_df.tail(10).iterrows():
        week_start = idx - pd.Timedelta(days=idx.weekday())
        week_end = week_start + pd.Timedelta(days=6)
        
        matching_days = daily_data[(daily_data.index >= week_start) & (daily_data.index <= week_end)]
        
        print(f"\n周线日期: {idx.strftime('%Y-%m-%d')} ({idx.strftime('%A')})")
        print(f"  周范围: {week_start.strftime('%Y-%m-%d')} 到 {week_end.strftime('%Y-%m-%d')}")
        print(f"  匹配的交易日数: {len(matching_days)}")
        
        if len(matching_days) > 0:
            print(f"  第一个交易日: {matching_days.index[0].strftime('%Y-%m-%d')} ({matching_days.index[0].strftime('%A')})")
            print(f"  最后一个交易日: {matching_days.index[-1].strftime('%Y-%m-%d')} ({matching_days.index[-1].strftime('%A')})")
            
            # 检查周线日期是否在日线数据中
            if idx in daily_data.index:
                print(f"  ✓ 周线日期在日线数据中")
            else:
                print(f"  ✗ 周线日期不在日线数据中")
    
    print("-" * 80)
    
    print("\n调试完成！")


if __name__ == '__main__':
    debug_weekly_dates()
