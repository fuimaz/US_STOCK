import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from weekly_boll_strategy import WeeklyBollingerStrategy


def debug_strategy_signals():
    """
    调试策略信号生成
    """
    print("=" * 80)
    print("调试策略信号生成")
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
    weekly_df['Middle'] = weekly_df['Close'].rolling(window=strategy.period).mean()
    weekly_df['Upper'] = weekly_df['Middle'] + weekly_df['Close'].rolling(window=strategy.period).std() * strategy.std_dev
    weekly_df['Lower'] = weekly_df['Middle'] - weekly_df['Close'].rolling(window=strategy.period).std() * strategy.std_dev
    
    # 初始化策略信号列
    weekly_df['signal'] = 0
    weekly_df['phase'] = ''
    weekly_df['below_middle_count'] = 0
    weekly_df['market_phase'] = ''
    weekly_df['ready_to_buy'] = False
    weekly_df['ready_to_sell'] = False
    weekly_df['recovered_from_down'] = False
    weekly_df['touched_middle_nearby'] = False
    
    # 生成信号
    for i in range(len(weekly_df)):
        if i < strategy.period:
            weekly_df.loc[weekly_df.index[i], 'signal'] = 0
            weekly_df.loc[weekly_df.index[i], 'phase'] = '初始化'
            weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
            weekly_df.loc[weekly_df.index[i], 'market_phase'] = '初始化'
            weekly_df.loc[weekly_df.index[i], 'ready_to_buy'] = False
            weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
            weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
            weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
            continue
        
        current_close = weekly_df['Close'].iloc[i]
        current_middle = weekly_df['Middle'].iloc[i]
        current_upper = weekly_df['Upper'].iloc[i]
        current_lower = weekly_df['Lower'].iloc[i]
        prev_signal = weekly_df['signal'].iloc[i-1]
        prev_phase = weekly_df['phase'].iloc[i-1]
        prev_below_count = weekly_df['below_middle_count'].iloc[i-1]
        prev_ready_to_buy = weekly_df['ready_to_buy'].iloc[i-1]
        prev_ready_to_sell = weekly_df['ready_to_sell'].iloc[i-1]
        prev_market_phase = weekly_df['market_phase'].iloc[i-1]
        prev_recovered = weekly_df['recovered_from_down'].iloc[i-1]
        prev_touched_middle = weekly_df['touched_middle_nearby'].iloc[i-1]
        
        # 市场阶段判断
        if current_close >= current_lower:
            weekly_df.loc[weekly_df.index[i], 'market_phase'] = '上行期'
        else:
            weekly_df.loc[weekly_df.index[i], 'market_phase'] = '下跌期'
        
        # 反弹标志
        if prev_market_phase == '下跌期' and current_close >= current_lower:
            weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = True
        elif prev_recovered:
            weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
        else:
            weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
        
        # 买入信号逻辑
        if prev_signal == 0:
            weekly_df.loc[weekly_df.index[i], 'signal'] = 0
            weekly_df.loc[weekly_df.index[i], 'phase'] = '空仓'
            weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
            
            middle_distance = abs(current_close - current_middle) / current_middle
            
            if prev_recovered and middle_distance <= strategy.middle_threshold:
                weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = True
                weekly_df.loc[weekly_df.index[i], 'signal'] = 1
                weekly_df.loc[weekly_df.index[i], 'phase'] = '买入'
                weekly_df.loc[weekly_df.index[i], 'ready_to_buy'] = False
                weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
            else:
                weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = prev_touched_middle
                weekly_df.loc[weekly_df.index[i], 'ready_to_buy'] = False
                weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
        
        elif prev_signal == 1:
            if current_close < current_middle:
                new_below_count = prev_below_count + 1
                weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = new_below_count
                weekly_df.loc[weekly_df.index[i], 'signal'] = 1
                weekly_df.loc[weekly_df.index[i], 'phase'] = '持有'
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
                
                if new_below_count >= 3:
                    weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = True
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '准备卖出'
                else:
                    weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
            elif current_close > current_upper and prev_ready_to_sell:
                weekly_df.loc[weekly_df.index[i], 'signal'] = -1
                weekly_df.loc[weekly_df.index[i], 'phase'] = '卖出'
                weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
                weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
            else:
                weekly_df.loc[weekly_df.index[i], 'signal'] = 1
                weekly_df.loc[weekly_df.index[i], 'phase'] = '持有'
                weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = prev_below_count
                weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = prev_ready_to_sell
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
    
    # 统计
    print(f"\n周线数据统计:")
    print(f"  总周数: {len(weekly_df)}")
    print(f"  上行期周数: {len(weekly_df[weekly_df['market_phase'] == '上行期'])}")
    print(f"  下跌期周数: {len(weekly_df[weekly_df['market_phase'] == '下跌期'])}")
    print(f"  从下跌期反弹的周数: {len(weekly_df[weekly_df['recovered_from_down'] == True])}")
    
    # 显示反弹的周
    recovered_weeks = weekly_df[weekly_df['recovered_from_down'] == True]
    print(f"\n反弹的周（{len(recovered_weeks)}周）:")
    print("-" * 120)
    print(f"{'日期':<12} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10} {'市场阶段':<10} {'反弹':<8} {'中线距离':<10}")
    print("-" * 120)
    
    for idx, row in recovered_weeks.iterrows():
        middle_distance = abs(row['Close'] - row['Middle']) / row['Middle']
        print(f"{idx.strftime('%Y-%m-%d'):<12} {row['Close']:<10.2f} {row['Middle']:<10.2f} {row['Upper']:<10.2f} {row['Lower']:<10.2f} {row['market_phase']:<10} {'是':<8} {middle_distance:<10.4f}")
    
    print("-" * 120)
    
    # 显示反弹后的周
    print(f"\n反弹后的周（{len(weekly_df[weekly_df['recovered_from_down'] == False])}周）:")
    print("-" * 120)
    print(f"{'日期':<12} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10} {'市场阶段':<10} {'反弹':<8} {'中线距离':<10}")
    print("-" * 120)
    
    not_recovered_weeks = weekly_df[weekly_df['recovered_from_down'] == False]
    for idx, row in not_recovered_weeks.head(20).iterrows():
        middle_distance = abs(row['Close'] - row['Middle']) / row['Middle']
        print(f"{idx.strftime('%Y-%m-%d'):<12} {row['Close']:<10.2f} {row['Middle']:<10.2f} {row['Upper']:<10.2f} {row['Lower']:<10.2f} {row['market_phase']:<10} {'否':<8} {middle_distance:<10.4f}")
    
    print("-" * 120)
    
    # 统计信号
    signals = weekly_df[weekly_df['signal'] != 0]
    buy_signals = weekly_df[weekly_df['signal'] == 1]
    sell_signals = weekly_df[weekly_df['signal'] == -1]
    
    print(f"\n周线信号统计:")
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
    debug_strategy_signals()
