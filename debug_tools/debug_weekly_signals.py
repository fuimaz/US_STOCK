import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from weekly_boll_strategy import WeeklyBollingerStrategy


def debug_weekly_signals():
    """
    调试周线信号生成
    """
    print("=" * 80)
    print("调试周线信号生成")
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
    print(f"时间范围: {daily_data.index[0].strftime('%Y-%m-%d')} 到 {daily_data.index[-1].strftime('%Y-%m-%d')}")
    
    # 创建策略
    strategy = WeeklyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
    
    # 生成信号
    print("\n正在生成交易信号...")
    data_with_signals = strategy.generate_signals(daily_data)
    
    # 转换为周线数据
    weekly_df = strategy._resample_to_weekly(daily_data)
    weekly_df['Middle'] = weekly_df['Close'].rolling(window=strategy.period).mean()
    weekly_df['Upper'] = weekly_df['Middle'] + weekly_df['Close'].rolling(window=strategy.period).std() * strategy.std_dev
    weekly_df['Lower'] = weekly_df['Middle'] - weekly_df['Close'].rolling(window=strategy.period).std() * strategy.std_dev
    
    # 计算市场阶段
    weekly_df['market_phase'] = ''
    weekly_df['recovered_from_down'] = False
    weekly_df['middle_distance'] = 0.0
    
    for i in range(len(weekly_df)):
        if i < strategy.period:
            weekly_df.loc[weekly_df.index[i], 'market_phase'] = '初始化'
            continue
        
        current_close = weekly_df['Close'].iloc[i]
        current_middle = weekly_df['Middle'].iloc[i]
        current_lower = weekly_df['Lower'].iloc[i]
        prev_market_phase = weekly_df['market_phase'].iloc[i-1]
        prev_recovered = weekly_df['recovered_from_down'].iloc[i-1]
        
        # 市场阶段判断
        if current_close >= current_lower:
            weekly_df.loc[weekly_df.index[i], 'market_phase'] = '上行期'
        else:
            weekly_df.loc[weekly_df.index[i], 'market_phase'] = '下跌期'
        
        # 反弹标志
        if prev_market_phase == '下跌期' and current_close >= current_lower:
            weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = True
        else:
            weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = prev_recovered
        
        # 计算与中线的距离
        weekly_df.loc[weekly_df.index[i], 'middle_distance'] = abs(current_close - current_middle) / current_middle
    
    # 统计
    print(f"\n周线数据统计:")
    print(f"  总周数: {len(weekly_df)}")
    print(f"  上行期周数: {len(weekly_df[weekly_df['market_phase'] == '上行期'])}")
    print(f"  下跌期周数: {len(weekly_df[weekly_df['market_phase'] == '下跌期'])}")
    print(f"  从下跌期反弹的周数: {len(weekly_df[weekly_df['recovered_from_down'] == True])}")
    print(f"  反弹后靠近中线的周数（5%内）: {len(weekly_df[(weekly_df['recovered_from_down'] == True) & (weekly_df['middle_distance'] <= 0.05)])}")
    
    # 显示最近的周线数据
    print(f"\n最近20周数据:")
    print("-" * 120)
    print(f"{'日期':<12} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10} {'市场阶段':<10} {'反弹':<8} {'中线距离':<10}")
    print("-" * 120)
    
    recent_weeks = weekly_df.tail(20)
    for idx, row in recent_weeks.iterrows():
        recovered = '是' if row['recovered_from_down'] else '否'
        print(f"{idx.strftime('%Y-%m-%d'):<12} {row['Close']:<10.2f} {row['Middle']:<10.2f} {row['Upper']:<10.2f} {row['Lower']:<10.2f} {row['market_phase']:<10} {recovered:<8} {row['middle_distance']:<10.4f}")
    
    print("-" * 120)
    
    # 显示日线信号
    print(f"\n日线信号统计:")
    signals = data_with_signals[data_with_signals['signal'] != 0]
    buy_signals = data_with_signals[data_with_signals['signal'] == 1]
    sell_signals = data_with_signals[data_with_signals['signal'] == -1]
    
    print(f"  总信号数: {len(signals)}")
    print(f"  买入信号: {len(buy_signals)}")
    print(f"  卖出信号: {len(sell_signals)}")
    
    if len(signals) > 0:
        print(f"\n最近20个信号:")
        print("-" * 120)
        print(f"{'日期':<12} {'信号':<8} {'阶段':<10} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10}")
        print("-" * 120)
        
        recent_signals = signals.tail(20)
        for idx, row in recent_signals.iterrows():
            signal_text = "买入" if row['signal'] == 1 else "卖出"
            print(f"{idx.strftime('%Y-%m-%d'):<12} {signal_text:<8} {row['phase']:<10} {row['Close']:<10.2f} {row['Middle']:<10.2f} {row['Upper']:<10.2f} {row['Lower']:<10.2f}")
        
        print("-" * 120)
    
    print("\n调试完成！")


if __name__ == '__main__':
    debug_weekly_signals()
