"""
调试调整后的适中策略
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from moderate_boll_strategy_v2 import ModerateBollStrategyV2
import os

def debug_strategy():
    """
    调试策略，查看为什么没有产生交易信号
    """
    print("=" * 100)
    print("调试调整后的适中布林带策略")
    print("=" * 100)
    print()
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 选择一只股票进行调试
    symbol = '601186.SS'  # 中国铁建
    
    print(f"正在调试股票: {symbol}")
    print()
    
    # 获取数据
    data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
    
    if data is None or len(data) == 0:
        print("✗ 未获取到数据")
        return
    
    print(f"✓ 数据量: {len(data)} 条")
    print(f"✓ 时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    print()
    
    # 初始化策略
    strategy = ModerateBollStrategyV2(
        period=20,
        std_dev=2,
        min_uptrend_days=20,
        min_interval_days=10,
        ma_period=60,
        uptrend_threshold=0.5
    )
    
    # 生成信号
    signals_df = strategy.generate_signals(data)
    
    # 统计信号
    buy_signals = (signals_df['signal'] == 1).sum()
    sell_signals = (signals_df['signal'] == -1).sum()
    
    print(f"✓ 买入信号数量: {buy_signals}")
    print(f"✓ 卖出信号数量: {sell_signals}")
    print()
    
    # 检查布林带计算
    print("=" * 100)
    print("布林带统计")
    print("=" * 100)
    print()
    
    # 统计价格与布林带的关系
    above_upper = (signals_df['Close'] > signals_df['upper_band']).sum()
    below_lower = (signals_df['Close'] < signals_df['lower_band']).sum()
    between = ((signals_df['Close'] >= signals_df['lower_band']) & (signals_df['Close'] <= signals_df['upper_band'])).sum()
    
    print(f"价格在上轨之上: {above_upper} 天 ({above_upper/len(signals_df)*100:.2f}%)")
    print(f"价格在下轨之下: {below_lower} 天 ({below_lower/len(signals_df)*100:.2f}%)")
    print(f"价格在上下轨之间: {between} 天 ({between/len(signals_df)*100:.2f}%)")
    print()
    
    # 手动模拟策略逻辑
    print("=" * 100)
    print("手动模拟策略逻辑")
    print("=" * 100)
    print()
    
    min_uptrend_days = 20
    min_interval_days = 10
    ma_period = 60
    uptrend_threshold = 0.5
    
    # 状态变量
    in_uptrend = False
    uptrend_start_idx = 0
    lower_band_breaks = []
    upper_band_crosses = []
    middle_band_crosses = []
    last_lower_band_break_idx = -1
    last_upper_band_cross_idx = -1
    last_middle_band_cross_idx = -1
    
    uptrend_periods = []
    
    for i in range(len(signals_df)):
        current_price = signals_df['Close'].iloc[i]
        current_high = signals_df['High'].iloc[i]
        current_low = signals_df['Low'].iloc[i]
        middle_band = signals_df['middle_band'].iloc[i]
        upper_band = signals_df['upper_band'].iloc[i]
        lower_band = signals_df['lower_band'].iloc[i]
        ma_long = signals_df['ma_long'].iloc[i]
        ma_short = signals_df['ma_short'].iloc[i]
        
        # 检查是否有足够的数据
        if pd.isna(middle_band) or pd.isna(upper_band) or pd.isna(lower_band) or pd.isna(ma_long):
            continue
        
        # 1. 判断是否处于上行期
        if in_uptrend:
            if current_price < ma_long or ma_short < ma_long:
                if uptrend_start_idx > 0:
                    uptrend_periods.append((uptrend_start_idx, i))
                in_uptrend = False
                uptrend_start_idx = 0
                lower_band_breaks = []
                upper_band_crosses = []
                middle_band_crosses = []
        else:
            if i >= min_uptrend_days:
                if current_price > ma_long and ma_short > ma_long:
                    recent_highs = signals_df['High'].iloc[i - min_uptrend_days:i + 1]
                    new_high_days = 0
                    for j in range(1, len(recent_highs)):
                        if recent_highs.iloc[j] > recent_highs.iloc[j - 1]:
                            new_high_days += 1
                    
                    new_high_ratio = new_high_days / len(recent_highs)
                    price_change = (current_price - signals_df['Close'].iloc[i - min_uptrend_days]) / signals_df['Close'].iloc[i - min_uptrend_days]
                    
                    if new_high_ratio >= uptrend_threshold and price_change > 0:
                        in_uptrend = True
                        uptrend_start_idx = i - min_uptrend_days
                        lower_band_breaks = []
                        upper_band_crosses = []
                        middle_band_crosses = []
        
        # 2. 检测破下轨
        if in_uptrend and current_low <= lower_band:
            if last_lower_band_break_idx == -1 or i - last_lower_band_break_idx >= min_interval_days:
                lower_band_breaks.append(i)
                last_lower_band_break_idx = i
        
        # 3. 检测穿上轨
        if in_uptrend:
            if i > 0:
                prev_price = signals_df['Close'].iloc[i - 1]
                prev_upper_band = signals_df['upper_band'].iloc[i - 1]
                
                if prev_price <= prev_upper_band and current_price > upper_band:
                    if last_upper_band_cross_idx == -1 or i - last_upper_band_cross_idx >= min_interval_days:
                        upper_band_crosses.append(i)
                        last_upper_band_cross_idx = i
        
        # 4. 检测穿中轨
        if in_uptrend:
            if i > 0:
                prev_price = signals_df['Close'].iloc[i - 1]
                prev_middle_band = signals_df['middle_band'].iloc[i - 1]
                
                if prev_price <= prev_middle_band and current_price > middle_band:
                    if last_middle_band_cross_idx == -1 or i - last_middle_band_cross_idx >= min_interval_days:
                        middle_band_crosses.append(i)
                        last_middle_band_cross_idx = i
    
    # 检查最后一个上行期
    if in_uptrend and uptrend_start_idx > 0:
        uptrend_periods.append((uptrend_start_idx, len(signals_df) - 1))
    
    print(f"✓ 检测到的上行期数量: {len(uptrend_periods)}")
    print()
    
    if len(uptrend_periods) > 0:
        print("上行期详情:")
        for i, (start_idx, end_idx) in enumerate(uptrend_periods[:5], 1):
            start_date = signals_df.index[start_idx].strftime('%Y-%m-%d')
            end_date = signals_df.index[end_idx].strftime('%Y-%m-%d')
            duration = end_idx - start_idx + 1
            
            # 统计该上行期内的破下轨次数
            period_lower_breaks = [b for b in lower_band_breaks if start_idx <= b <= end_idx]
            period_upper_crosses = [u for u in upper_band_crosses if start_idx <= u <= end_idx]
            period_middle_crosses = [m for m in middle_band_crosses if start_idx <= m <= end_idx]
            
            print(f"  {i}. {start_date} 到 {end_date} ({duration} 天)")
            print(f"     破下轨: {len(period_lower_breaks)} 次")
            print(f"     穿上轨: {len(period_upper_crosses)} 次")
            print(f"     穿中轨: {len(period_middle_crosses)} 次")
            
            # 检查买入条件
            if len(period_lower_breaks) >= 2 and len(period_middle_crosses) >= 3:
                if len(period_middle_crosses) >= len(period_upper_crosses) + 2:
                    print(f"     ✓ 满足买入条件！")
                else:
                    print(f"     ✗ 不满足买入条件：穿中轨次数({len(period_middle_crosses)}) < 穿上轨次数({len(period_upper_crosses)}) + 2")
            else:
                print(f"     ✗ 不满足买入条件：破下轨({len(period_lower_breaks)}) < 2 或 穿中轨({len(period_middle_crosses)}) < 3")
        
        if len(uptrend_periods) > 5:
            print(f"  ... 还有 {len(uptrend_periods) - 5} 个上行期")
    else:
        print("✗ 未检测到任何上行期")
    
    print()
    
    # 保存调试数据
    output_dir = 'debug'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'{symbol}_debug_v2.csv')
    signals_df.to_csv(output_file)
    print(f"✓ 调试数据已保存到: {output_file}")
    print()
    
    print("=" * 100)
    print("问题分析")
    print("=" * 100)
    print()
    print("买入条件分析：")
    print("  1. 至少2次破下轨")
    print("  2. 至少3次穿中轨")
    print("  3. 穿中轨次数 >= 穿上轨次数 + 2")
    print()
    print("这个条件组合过于严格，因为：")
    print("  - 要求3次穿中轨，但前2次反弹都不能穿上轨")
    print("  - 这意味着前2次反弹的强度都很弱，只到中轨")
    print("  - 在实际市场中，这种情况非常罕见")
    print()
    print("建议调整：")
    print("  1. 降低穿中轨次数要求（从3次改为2次）")
    print("  2. 或者调整穿上轨和穿中轨的关系条件")
    print("  3. 或者放宽反弹强度的要求")
    print()
    
    print("=" * 100)
    print("调试完成")
    print("=" * 100)

if __name__ == '__main__':
    debug_strategy()