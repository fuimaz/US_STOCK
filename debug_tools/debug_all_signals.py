import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from weekly_boll_strategy import WeeklyBollingerStrategy


def debug_all_signals():
    """
    调试所有信号
    """
    print("=" * 80)
    print("调试所有信号")
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
    
    # 确保索引是naive datetime
    daily_data.index = daily_data.index.tz_localize(None)
    
    print(f"✓ 数据获取成功: {len(daily_data)} 条")
    
    # 创建策略
    strategy = WeeklyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
    
    # 生成信号
    print("\n正在生成交易信号...")
    data_with_signals = strategy.generate_signals(daily_data)
    
    # 显示2012-01-23到2012-01-27期间的所有信号
    print("\n2012-01-23到2012-01-27期间的所有信号:")
    print("-" * 120)
    print(f"{'日期':<12} {'信号':<8} {'阶段':<10} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10}")
    print("-" * 120)
    
    target_dates = pd.date_range('2012-01-23', '2012-01-27')
    for date in target_dates:
        date_naive = pd.Timestamp(date).tz_localize(None)
        if date_naive in data_with_signals.index:
            row = data_with_signals.loc[date_naive]
            signal_text = "买入" if row['signal'] == 1 else ("卖出" if row['signal'] == -1 else "空仓")
            print(f"{date_naive.strftime('%Y-%m-%d'):<12} {signal_text:<8} {row['phase']:<10} {row['Close']:<10.2f} {row['Middle']:<10.2f} {row['Upper']:<10.2f} {row['Lower']:<10.2f}")
        else:
            print(f"{date_naive.strftime('%Y-%m-%d'):<12} {'无数据':<8} {'':<10} {'':<10} {'':<10} {'':<10} {'':<10}")
    
    print("-" * 120)
    
    # 统计信号
    signals = data_with_signals[data_with_signals['signal'] != 0]
    buy_signals = data_with_signals[data_with_signals['signal'] == 1]
    sell_signals = data_with_signals[data_with_signals['signal'] == -1]
    
    print(f"\n日线信号统计:")
    print(f"  总信号数: {len(signals)}")
    print(f"  买入信号: {len(buy_signals)}")
    print(f"  卖出信号: {len(sell_signals)}")
    
    if len(signals) > 0:
        print(f"\n所有信号:")
        print("-" * 120)
        print(f"{'日期':<12} {'信号':<8} {'阶段':<10} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10}")
        print("-" * 120)
        
        for idx, row in signals.iterrows():
            signal_text = "买入" if row['signal'] == 1 else "卖出"
            print(f"{idx.strftime('%Y-%m-%d'):<12} {signal_text:<8} {row['phase']:<10} {row['Close']:<10.2f} {row['Middle']:<10.2f} {row['Upper']:<10.2f} {row['Lower']:<10.2f}")
        
        print("-" * 120)
    
    print("\n调试完成！")


if __name__ == '__main__':
    debug_all_signals()
