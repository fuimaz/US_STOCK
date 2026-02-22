"""
分析卖出时的市场状态
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from moderate_boll_strategy_v4 import ModerateBollStrategyV4

def analyze_sell_signals():
    """
    分析卖出时的市场状态
    """
    print("=" * 100)
    print("分析卖出时的市场状态")
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
    
    # 选择一只股票进行分析
    symbol = '601186.SS'  # 中国铁建
    
    print(f"正在分析股票: {symbol}")
    print()
    
    # 获取数据
    data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
    
    if data is None or len(data) == 0:
        print("✗ 未获取到数据")
        return
    
    print(f"✓ 数据获取完成，共 {len(data)} 条记录")
    print()
    
    # 初始化策略
    strategy = ModerateBollStrategyV4(
        period=20,
        std_dev=2,
        min_uptrend_days=20,
        min_interval_days=10,
        ma_period=60,
        uptrend_threshold=0.5
    )
    
    # 生成信号
    signals_df = strategy.generate_signals(data)
    
    # 找出所有卖出信号
    sell_signals = signals_df[signals_df['signal'] == -1]
    
    print(f"✓ 找到 {len(sell_signals)} 个卖出信号")
    print()
    
    # 分析每个卖出信号
    for idx, row in sell_signals.iterrows():
        print("=" * 100)
        print(f"卖出信号: {idx.strftime('%Y-%m-%d')}")
        print("=" * 100)
        print()
        
        # 获取当天的数据
        i = signals_df.index.get_loc(idx)
        
        # 检查前20天的上行期状态
        print("前20天的上行期状态:")
        print("-" * 100)
        
        # 重新计算上行期状态
        in_uptrend = False
        uptrend_start_idx = 0
        
        for j in range(max(0, i - 20), i + 1):
            current_price = signals_df['Close'].iloc[j]
            ma_long = signals_df['ma_long'].iloc[j]
            ma_short = signals_df['ma_short'].iloc[j]
            
            if pd.isna(ma_long) or pd.isna(ma_short):
                continue
            
            # 判断上行期
            if in_uptrend:
                if current_price < ma_long or ma_short < ma_long:
                    in_uptrend = False
                    uptrend_start_idx = 0
            else:
                if j >= strategy.min_uptrend_days:
                    if current_price > ma_long and ma_short > ma_long:
                        recent_highs = signals_df['High'].iloc[j - strategy.min_uptrend_days:j + 1]
                        new_high_days = 0
                        for k in range(1, len(recent_highs)):
                            if recent_highs.iloc[k] > recent_highs.iloc[k - 1]:
                                new_high_days += 1
                        
                        new_high_ratio = new_high_days / len(recent_highs)
                        price_change = (current_price - signals_df['Close'].iloc[j - strategy.min_uptrend_days]) / signals_df['Close'].iloc[j - strategy.min_uptrend_days]
                        
                        if new_high_ratio >= strategy.uptrend_threshold and price_change > 0:
                            in_uptrend = True
                            uptrend_start_idx = j - strategy.min_uptrend_days
            
            status = "上行期" if in_uptrend else "下行期"
            print(f"  {signals_df.index[j].strftime('%Y-%m-%d')}: {status} (价格: {current_price:.2f}, MA60: {ma_long:.2f}, MA20: {ma_short:.2f})")
        
        print()
        
        # 检查卖出当天的状态
        current_price = signals_df['Close'].iloc[i]
        ma_long = signals_df['ma_long'].iloc[i]
        ma_short = signals_df['ma_short'].iloc[i]
        upper_band = signals_df['upper_band'].iloc[i]
        lower_band = signals_df['lower_band'].iloc[i]
        
        print("卖出当天的数据:")
        print("-" * 100)
        print(f"  收盘价: {current_price:.2f}")
        print(f"  MA60: {ma_long:.2f}")
        print(f"  MA20: {ma_short:.2f}")
        print(f"  上轨: {upper_band:.2f}")
        print(f"  下轨: {lower_band:.2f}")
        print()
        
        # 判断是否在上行期
        is_uptrend = current_price > ma_long and ma_short > ma_long
        print(f"  是否在上行期: {'是' if is_uptrend else '否'}")
        print()
        
        # 检查是否到达上轨
        is_at_upper = current_price >= upper_band
        print(f"  是否到达上轨: {'是' if is_at_upper else '否'}")
        print()
        
        # 找到对应的买入信号
        buy_signals = signals_df.loc[:idx]
        buy_signals = buy_signals[buy_signals['signal'] == 1]
        
        if not buy_signals.empty:
            last_buy = buy_signals.iloc[-1]
            buy_date = last_buy.name
            buy_price = last_buy['Close']
            
            print(f"对应的买入信号:")
            print("-" * 100)
            print(f"  买入日期: {buy_date.strftime('%Y-%m-%d')}")
            print(f"  买入价格: {buy_price:.2f}")
            print(f"  持仓天数: {(idx - buy_date).days} 天")
            print(f"  收益率: {((current_price - buy_price) / buy_price) * 100:.2f}%")
            print()
            
            # 检查买入后是否有2次破下轨
            buy_idx = signals_df.index.get_loc(buy_date)
            post_buy_data = signals_df.iloc[buy_idx:i + 1]
            
            lower_band_breaks = 0
            for k in range(len(post_buy_data)):
                if post_buy_data['Low'].iloc[k] <= post_buy_data['lower_band'].iloc[k]:
                    lower_band_breaks += 1
            
            print(f"  买入后破下轨次数: {lower_band_breaks}")
            print()
        else:
            print("  未找到对应的买入信号")
            print()
    
    print("=" * 100)
    print("分析完成")
    print("=" * 100)

if __name__ == '__main__':
    analyze_sell_signals()