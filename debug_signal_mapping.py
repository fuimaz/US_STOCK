import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from weekly_boll_strategy import WeeklyBollingerStrategy


def debug_signal_mapping():
    """
    调试信号映射
    """
    print("=" * 80)
    print("调试信号映射")
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
    
    # 转换为周线数据
    weekly_df = strategy._resample_to_weekly(daily_data)
    weekly_df['Middle'] = weekly_df['Close'].rolling(window=strategy.period).mean()
    weekly_df['Upper'] = weekly_df['Middle'] + weekly_df['Close'].rolling(window=strategy.period).std() * strategy.std_dev
    weekly_df['Lower'] = weekly_df['Middle'] - weekly_df['Close'].rolling(window=strategy.period).std() * strategy.std_dev
    
    # 确保周线索引也是naive datetime
    weekly_df.index = weekly_df.index.tz_localize(None)
    
    # 生成周线信号
    weekly_df['signal'] = 0
    weekly_df['phase'] = ''
    weekly_df['below_middle_count'] = 0
    weekly_df['market_phase'] = ''
    weekly_df['ready_to_buy'] = False
    weekly_df['ready_to_sell'] = False
    weekly_df['recovered_from_down'] = False
    weekly_df['touched_middle_nearby'] = False
    
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
        
        elif prev_signal == -1:
            weekly_df.loc[weekly_df.index[i], 'signal'] = 0
            weekly_df.loc[weekly_df.index[i], 'phase'] = '空仓'
            weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
            weekly_df.loc[weekly_df.index[i], 'ready_to_buy'] = False
            weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
            weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
            weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
    
    # 显示2012-01-23到2012-01-27期间的信号
    print("\n2012-01-23到2012-01-27期间的日线信号:")
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
    
    print("-" * 120)
    
    # 显示对应的周线信号
    print("\n对应的周线信号:")
    print("-" * 120)
    print(f"{'日期':<12} {'信号':<8} {'阶段':<10} {'收盘价':<10} {'中线':<10} {'上轨':<10} {'下轨':<10}")
    print("-" * 120)
    
    week_start = pd.Timestamp('2012-01-23').tz_localize(None) - pd.Timedelta(days=pd.Timestamp('2012-01-23').tz_localize(None).weekday())
    week_end = week_start + pd.Timedelta(days=6)
    
    matching_week = weekly_df[(weekly_df.index >= week_start) & (weekly_df.index <= week_end)]
    for idx, row in matching_week.iterrows():
        signal_text = "买入" if row['signal'] == 1 else ("卖出" if row['signal'] == -1 else "空仓")
        print(f"{idx.strftime('%Y-%m-%d'):<12} {signal_text:<8} {row['phase']:<10} {row['Close']:<10.2f} {row['Middle']:<10.2f} {row['Upper']:<10.2f} {row['Lower']:<10.2f}")
    
    print("-" * 120)
    
    # 检查该周的最后一个交易日
    week_trading_days = daily_data[(daily_data.index >= week_start) & (daily_data.index <= week_end)]
    print(f"\n该周的交易日:")
    print("-" * 80)
    print(f"{'日期':<12} {'星期':<6} {'收盘价':<10}")
    print("-" * 80)
    
    for idx, row in week_trading_days.iterrows():
        weekday = idx.strftime('%A')
        print(f"{idx.strftime('%Y-%m-%d'):<12} {weekday:<6} {row['Close']:<10.2f}")
    
    print("-" * 80)
    print(f"最后一个交易日: {week_trading_days.index[-1].strftime('%Y-%m-%d')} ({week_trading_days.index[-1].strftime('%A')})")
    
    print("\n调试完成！")


if __name__ == '__main__':
    debug_signal_mapping()
