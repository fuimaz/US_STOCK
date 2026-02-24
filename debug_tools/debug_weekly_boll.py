import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from weekly_boll_strategy import WeeklyBollingerStrategy


def debug_weekly_boll_signals():
    """
    调试周布林带策略信号生成
    """
    print("=" * 80)
    print("周布林带策略信号生成调试")
    print("=" * 80)
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 测试AAPL
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
    print(f"时间范围: {daily_data.index[0].strftime('%Y-%m-%d')} 到 {daily_data.index[-1].strftime('%Y-%m-%d')}")
    
    # 创建策略
    strategy = WeeklyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
    
    # 生成信号
    data_with_signals = strategy.generate_signals(daily_data)
    
    # 统计信号
    signals = data_with_signals[data_with_signals['signal'] != 0]
    buy_signals = data_with_signals[data_with_signals['signal'] == 1]
    sell_signals = data_with_signals[data_with_signals['signal'] == -1]
    
    print(f"\n信号统计:")
    print(f"  总信号数: {len(signals)}")
    print(f"  买入信号: {len(buy_signals)}")
    print(f"  卖出信号: {len(sell_signals)}")
    
    # 统计准备买入状态
    ready_to_buy = data_with_signals[data_with_signals['ready_to_buy'] == True]
    print(f"\n准备买入状态:")
    print(f"  总次数: {len(ready_to_buy)}")
    
    # 统计反弹标志
    recovered = data_with_signals[data_with_signals['recovered_from_down'] == True]
    print(f"\n反弹标志:")
    print(f"  总次数: {len(recovered)}")
    
    # 统计触碰中轨标志
    touched_middle = data_with_signals[data_with_signals['touched_middle_nearby'] == True]
    print(f"\n触碰中轨标志:")
    print(f"  总次数: {len(touched_middle)}")
    
    # 显示准备买入的周
    if len(ready_to_buy) > 0:
        print(f"\n准备买入的交易日（共{len(ready_to_buy)}天）:")
        print("-" * 140)
        print(f"{'日期':<12} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10} {'市场阶段':<8} {'中线距离':<10} {'反弹':<6} {'触碰中轨':<8} {'准备买入':<8}")
        print("-" * 140)
        
        for idx, row in ready_to_buy.head(50).iterrows():
            middle_distance = abs(row['Close'] - row['Middle']) / row['Middle']
            print(f"{idx.strftime('%Y-%m-%d'):<12} ${row['Close']:<9.2f} ${row['Middle']:<9.2f} ${row['Upper']:<9.2f} ${row['Lower']:<9.2f} {row['market_phase']:<8} {middle_distance:.4f} {str(row['recovered_from_down']):<6} {str(row['touched_middle_nearby']):<8} {str(row['ready_to_buy']):<8}")
        
        print("-" * 140)
    else:
        print(f"\n没有准备买入的交易日")
    
    # 显示触碰中轨的交易日
    if len(touched_middle) > 0:
        print(f"\n触碰中轨的交易日（共{len(touched_middle)}天）:")
        print("-" * 140)
        print(f"{'日期':<12} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10} {'市场阶段':<8} {'中线距离':<10} {'反弹':<6} {'触碰中轨':<8} {'准备买入':<8}")
        print("-" * 140)
        
        for idx, row in touched_middle.head(50).iterrows():
            middle_distance = abs(row['Close'] - row['Middle']) / row['Middle']
            print(f"{idx.strftime('%Y-%m-%d'):<12} ${row['Close']:<9.2f} ${row['Middle']:<9.2f} ${row['Upper']:<9.2f} ${row['Lower']:<9.2f} {row['market_phase']:<8} {middle_distance:.4f} {str(row['recovered_from_down']):<6} {str(row['touched_middle_nearby']):<8} {str(row['ready_to_buy']):<8}")
        
        print("-" * 140)
    else:
        print(f"\n没有触碰中轨的交易日")
    
    # 显示反弹的交易日
    if len(recovered) > 0:
        print(f"\n反弹的交易日（共{len(recovered)}天）:")
        print("-" * 140)
        print(f"{'日期':<12} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10} {'市场阶段':<8} {'中线距离':<10} {'反弹':<6} {'触碰中轨':<8} {'准备买入':<8}")
        print("-" * 140)
        
        for idx, row in recovered.head(50).iterrows():
            middle_distance = abs(row['Close'] - row['Middle']) / row['Middle']
            print(f"{idx.strftime('%Y-%m-%d'):<12} ${row['Close']:<9.2f} ${row['Middle']:<9.2f} ${row['Upper']:<9.2f} ${row['Lower']:<9.2f} {row['market_phase']:<8} {middle_distance:.4f} {str(row['recovered_from_down']):<6} {str(row['touched_middle_nearby']):<8} {str(row['ready_to_buy']):<8}")
        
        print("-" * 140)
    else:
        print(f"\n没有反弹的交易日")
    
    print(f"\n调试完成！")


if __name__ == '__main__':
    debug_weekly_boll_signals()
