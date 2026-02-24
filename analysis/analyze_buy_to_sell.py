"""
分析买入后的市场状态和上行期情况
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from moderate_boll_strategy_v7 import ModerateBollStrategyV7

def analyze_buy_to_sell():
    """
    分析买入后的市场状态
    """
    print("=" * 100)
    print("分析买入后的市场状态")
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
    daily_data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
    
    if daily_data is None or len(daily_data) == 0:
        print("✗ 未获取到数据")
        return
    
    # 转换为周K
    weekly = pd.DataFrame()
    weekly['Open'] = daily_data['Open'].resample('W').first()
    weekly['High'] = daily_data['High'].resample('W').max()
    weekly['Low'] = daily_data['Low'].resample('W').min()
    weekly['Close'] = daily_data['Close'].resample('W').last()
    weekly['Volume'] = daily_data['Volume'].resample('W').sum()
    weekly = weekly.dropna()
    
    print(f"✓ 数据获取完成，共 {len(weekly)} 条周K记录")
    print()
    
    # 初始化策略
    strategy = ModerateBollStrategyV7(
        period=20,
        std_dev=2,
        min_uptrend_days=20,
        min_interval_days=10,
        ma_period=60,
        uptrend_threshold=0.5,
        max_hold_days=120,
        sell_threshold=2.5
    )
    
    # 生成信号
    signals_df = strategy.generate_signals(weekly)
    
    # 找出所有买入和卖出信号
    buy_signals = signals_df[signals_df['signal'] == 1]
    sell_signals = signals_df[signals_df['signal'] == -1]
    
    print(f"✓ 找到 {len(buy_signals)} 个买入信号")
    print(f"✓ 找到 {len(sell_signals)} 个卖出信号")
    print()
    
    # 分析每笔交易
    trade_pairs = []
    
    for buy_idx, buy_row in buy_signals.iterrows():
        # 找到对应的卖出信号（买入后的第一个卖出）
        post_buy_sells = sell_signals[sell_signals.index > buy_idx]
        
        if not post_buy_sells.empty:
            sell_idx = post_buy_sells.index[0]
            sell_row = post_buy_sells.iloc[0]
            
            trade_pairs.append({
                'buy_date': buy_idx,
                'sell_date': sell_idx,
                'buy_price': buy_row['Close'],
                'sell_price': sell_row['Close'],
                'return_pct': ((sell_row['Close'] - buy_row['Close']) / buy_row['Close']) * 100
            })
    
    print("=" * 100)
    print("交易详情分析")
    print("=" * 100)
    print()
    
    for i, trade in enumerate(trade_pairs):
        print(f"交易 {i+1}: {trade['buy_date'].strftime('%Y-%m-%d')} 买入 -> {trade['sell_date'].strftime('%Y-%m-%d')} 卖出")
        print("-" * 100)
        
        buy_idx = signals_df.index.get_loc(trade['buy_date'])
        sell_idx = signals_df.index.get_loc(trade['sell_date'])
        
        # 分析买入时的状态
        buy_price = signals_df['Close'].iloc[buy_idx]
        buy_ma_long = signals_df['ma_long'].iloc[buy_idx]
        buy_ma_short = signals_df['ma_short'].iloc[buy_idx]
        buy_middle_band = signals_df['middle_band'].iloc[buy_idx]
        
        print(f"买入时状态:")
        print(f"  价格: {buy_price:.2f}")
        print(f"  MA60: {buy_ma_long:.2f}")
        print(f"  MA20: {buy_ma_short:.2f}")
        print(f"  中线: {buy_middle_band:.2f}")
        print(f"  是否在上行期: {'是' if buy_price > buy_ma_long and buy_ma_short > buy_ma_long else '否'}")
        print()
        
        # 分析卖出时的状态
        sell_price = signals_df['Close'].iloc[sell_idx]
        sell_ma_long = signals_df['ma_long'].iloc[sell_idx]
        sell_ma_short = signals_df['ma_short'].iloc[sell_idx]
        sell_middle_band = signals_df['middle_band'].iloc[sell_idx]
        
        print(f"卖出时状态:")
        print(f"  价格: {sell_price:.2f}")
        print(f"  MA60: {sell_ma_long:.2f}")
        print(f"  MA20: {sell_ma_short:.2f}")
        print(f"  中线: {sell_middle_band:.2f}")
        print(f"  是否在上行期: {'是' if sell_price > sell_ma_long and sell_ma_short > sell_ma_long else '否'}")
        print(f"  价格/中线: {sell_price / sell_middle_band:.2f}x")
        print(f"  是否达到卖出阈值（2.5x）: {'是' if sell_price >= sell_middle_band * 2.5 else '否'}")
        print()
        
        # 分析持仓期间是否进入过上行期
        print(f"持仓期间状态分析:")
        print("-" * 100)
        
        entered_uptrend = False
        max_price_ratio = 0
        max_price_ratio_date = None
        
        for j in range(buy_idx + 1, sell_idx + 1):
            current_price = signals_df['Close'].iloc[j]
            ma_long = signals_df['ma_long'].iloc[j]
            ma_short = signals_df['ma_short'].iloc[j]
            middle_band = signals_df['middle_band'].iloc[j]
            
            # 判断是否在上行期
            is_uptrend = current_price > ma_long and ma_short > ma_long
            
            if is_uptrend:
                if not entered_uptrend:
                    entered_uptrend = True
                    print(f"  {signals_df.index[j].strftime('%Y-%m-%d')}: 进入上行期 (价格: {current_price:.2f}, MA60: {ma_long:.2f}, MA20: {ma_short:.2f})")
            
            # 计算价格/中线比率
            price_ratio = current_price / middle_band
            if price_ratio > max_price_ratio:
                max_price_ratio = price_ratio
                max_price_ratio_date = signals_df.index[j]
        
        print()
        print(f"  持仓期间是否进入上行期: {'是' if entered_uptrend else '否'}")
        print(f"  持仓期间最高价格/中线: {max_price_ratio:.2f}x (日期: {max_price_ratio_date.strftime('%Y-%m-%d')})")
        print(f"  是否达到卖出阈值（2.5x）: {'是' if max_price_ratio >= 2.5 else '否'}")
        print()
        
        print(f"交易结果:")
        print(f"  买入价格: {trade['buy_price']:.2f}")
        print(f"  卖出价格: {trade['sell_price']:.2f}")
        print(f"  收益率: {trade['return_pct']:.2f}%")
        print(f"  持仓周数: {(trade['sell_date'] - trade['buy_date']).days // 7} 周")
        print()
        print()
    
    print("=" * 100)
    print("分析完成")
    print("=" * 100)

if __name__ == '__main__':
    analyze_buy_to_sell()