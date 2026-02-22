"""
调试严格布林带策略
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from strict_boll_strategy import StrictBollingerStrategy
import os

def debug_strategy():
    """
    调试策略，查看为什么没有产生交易信号
    """
    print("=" * 100)
    print("调试严格布林带策略")
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
    
    # 选择一只表现较好的股票进行调试
    symbol = '600519.SS'  # 贵州茅台
    
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
    strategy = StrictBollingerStrategy(
        period=20,
        std_dev=2,
        min_uptrend_days=20,  # 一个月约20个交易日
        min_interval_days=10  # 2周约10个交易日
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
    
    # 检查上行期检测
    print("=" * 100)
    print("手动检测上行期")
    print("=" * 100)
    print()
    
    # 手动实现上行期检测逻辑
    min_uptrend_days = 20
    
    uptrend_periods = []
    in_uptrend = False
    uptrend_start_idx = 0
    highest_high = 0
    last_high_idx = 0
    
    for i in range(len(signals_df)):
        current_high = signals_df['High'].iloc[i]
        
        # 检查是否有足够的数据
        if i < min_uptrend_days:
            continue
        
        # 检查布林带是否有效
        if pd.isna(signals_df['upper_band'].iloc[i]):
            continue
        
        if in_uptrend:
            # 检查是否还在创新高
            if current_high > highest_high:
                highest_high = current_high
                last_high_idx = i
            
            # 检查上行期是否结束
            if i - last_high_idx > min_uptrend_days:
                uptrend_periods.append((uptrend_start_idx, last_high_idx))
                in_uptrend = False
                uptrend_start_idx = 0
                highest_high = 0
                last_high_idx = 0
        else:
            # 检查是否开始新的上行期
            recent_highs = signals_df['High'].iloc[i - min_uptrend_days:i + 1]
            
            if len(recent_highs) > 0:
                is_making_higher_highs = True
                for j in range(1, len(recent_highs)):
                    if recent_highs.iloc[j] <= recent_highs.iloc[j - 1]:
                        is_making_higher_highs = False
                        break
                
                if is_making_higher_highs:
                    in_uptrend = True
                    uptrend_start_idx = i - min_uptrend_days
                    highest_high = current_high
                    last_high_idx = i
    
    # 检查最后一个上行期
    if in_uptrend:
        uptrend_periods.append((uptrend_start_idx, last_high_idx))
    
    print(f"✓ 检测到的上行期数量: {len(uptrend_periods)}")
    print()
    
    if len(uptrend_periods) > 0:
        print("上行期详情:")
        for i, (start_idx, end_idx) in enumerate(uptrend_periods[:5], 1):  # 只显示前5个
            start_date = signals_df.index[start_idx].strftime('%Y-%m-%d')
            end_date = signals_df.index[end_idx].strftime('%Y-%m-%d')
            duration = end_idx - start_idx + 1
            print(f"  {i}. {start_date} 到 {end_date} ({duration} 天)")
        
        if len(uptrend_periods) > 5:
            print(f"  ... 还有 {len(uptrend_periods) - 5} 个上行期")
    else:
        print("✗ 未检测到任何上行期")
        print()
        print("问题分析：")
        print("  当前上行期检测逻辑要求过去20个交易日每一天都必须比前一天创新高")
        print("  这个条件过于严格，在实际市场中几乎不可能满足")
        print()
        print("建议修改：")
        print("  1. 改为检测总体上升趋势，而不是要求每一天都创新高")
        print("  2. 使用移动平均线或趋势线来判断上行期")
        print("  3. 允许一定程度的回调，只要整体趋势向上")
    
    print()
    
    # 检查破下轨情况
    print("=" * 100)
    print("破下轨情况分析")
    print("=" * 100)
    print()
    
    lower_band_breaks = []
    for i in range(len(signals_df)):
        if pd.isna(signals_df['lower_band'].iloc[i]):
            continue
        if signals_df['Low'].iloc[i] <= signals_df['lower_band'].iloc[i]:
            lower_band_breaks.append(i)
    
    print(f"✓ 破下轨次数: {len(lower_band_breaks)}")
    print(f"✓ 破下轨比例: {len(lower_band_breaks)/len(signals_df)*100:.2f}%")
    print()
    
    if len(lower_band_breaks) > 0:
        print("前10次破下轨:")
        for i, idx in enumerate(lower_band_breaks[:10], 1):
            date = signals_df.index[idx].strftime('%Y-%m-%d')
            price = signals_df['Close'].iloc[idx]
            lower_band = signals_df['lower_band'].iloc[idx]
            print(f"  {i}. {date}: 价格={price:.2f}, 下轨={lower_band:.2f}")
    
    print()
    
    # 检查穿中轨情况
    print("=" * 100)
    print("穿中轨情况分析")
    print("=" * 100)
    print()
    
    middle_band_crosses_up = []
    middle_band_crosses_down = []
    
    for i in range(1, len(signals_df)):
        if pd.isna(signals_df['middle_band'].iloc[i]) or pd.isna(signals_df['middle_band'].iloc[i-1]):
            continue
        
        prev_price = signals_df['Close'].iloc[i-1]
        curr_price = signals_df['Close'].iloc[i]
        prev_middle = signals_df['middle_band'].iloc[i-1]
        curr_middle = signals_df['middle_band'].iloc[i]
        
        # 向上穿过中轨
        if prev_price <= prev_middle and curr_price > curr_middle:
            middle_band_crosses_up.append(i)
        
        # 向下穿过中轨
        if prev_price > prev_middle and curr_price <= curr_middle:
            middle_band_crosses_down.append(i)
    
    print(f"✓ 向上穿中轨次数: {len(middle_band_crosses_up)}")
    print(f"✓ 向下穿中轨次数: {len(middle_band_crosses_down)}")
    print()
    
    # 保存调试数据
    output_dir = 'debug'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'{symbol}_debug.csv')
    signals_df.to_csv(output_file)
    print(f"✓ 调试数据已保存到: {output_file}")
    print()
    
    print("=" * 100)
    print("调试完成")
    print("=" * 100)

if __name__ == '__main__':
    debug_strategy()