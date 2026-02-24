"""
调试缠论买卖点逻辑
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from chan_theory_v4 import ChanTheory

def debug_buy_sell_logic():
    """
    调试买卖点逻辑
    """
    print("=" * 100)
    print("调试缠论买卖点逻辑")
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
    
    # 选择股票进行调试
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
    
    # 初始化缠论指标
    chan = ChanTheory(k_type='day')
    
    # 完整分析
    result = chan.analyze(data)
    
    # 分析买卖点
    buy_points = chan.buy_points
    sell_points = chan.sell_points
    
    print(f"买点数量: {len(buy_points)}")
    print(f"卖点数量: {len(sell_points)}")
    print()
    
    # 分析每个买点
    print("买点分析:")
    print("-" * 100)
    for i, buy_point in enumerate(buy_points):
        buy_date = buy_point['index']
        buy_price = buy_point['price']
        
        # 获取买入时的价格信息
        buy_idx = data.index.get_loc(buy_date)
        buy_close = data['Close'].iloc[buy_idx]
        buy_high = data['High'].iloc[buy_idx]
        buy_low = data['Low'].iloc[buy_idx]
        
        print(f"\n买点{i+1}: {buy_date.strftime('%Y-%m-%d')}")
        print(f"  类型: 第{buy_point['type']}类买点")
        print(f"  价格: {buy_price:.2f}")
        print(f"  收盘价: {buy_close:.2f}")
        print(f"  最高价: {buy_high:.2f}")
        print(f"  最低价: {buy_low:.2f}")
        
        # 检查买入后10天的价格
        print(f"  买入后价格变化:")
        for j in range(1, 11):
            if buy_idx + j < len(data):
                future_date = data.index[buy_idx + j]
                future_price = data['Close'].iloc[buy_idx + j]
                change = (future_price - buy_price) / buy_price * 100
                print(f"    +{j}天 ({future_date.strftime('%Y-%m-%d')}): {future_price:.2f} ({change:+.2f}%)")
            else:
                break
    
    # 分析每个卖点
    print("\n\n卖点分析:")
    print("-" * 100)
    for i, sell_point in enumerate(sell_points):
        sell_date = sell_point['index']
        sell_price = sell_point['price']
        
        # 获取卖出时的价格信息
        sell_idx = data.index.get_loc(sell_date)
        sell_close = data['Close'].iloc[sell_idx]
        sell_high = data['High'].iloc[sell_idx]
        sell_low = data['Low'].iloc[sell_idx]
        
        print(f"\n卖点{i+1}: {sell_date.strftime('%Y-%m-%d')}")
        print(f"  类型: 第{sell_point['type']}类卖点")
        print(f"  价格: {sell_price:.2f}")
        print(f"  收盘价: {sell_close:.2f}")
        print(f"  最高价: {sell_high:.2f}")
        print(f"  最低价: {sell_low:.2f}")
        
        # 检查卖出前10天的价格
        print(f"  卖出前价格变化:")
        for j in range(1, 11):
            if sell_idx - j >= 0:
                past_date = data.index[sell_idx - j]
                past_price = data['Close'].iloc[sell_idx - j]
                change = (sell_price - past_price) / past_price * 100
                print(f"    -{j}天 ({past_date.strftime('%Y-%m-%d')}): {past_price:.2f} ({change:+.2f}%)")
            else:
                break
    
    # 分析买卖点匹配
    print("\n\n买卖点匹配分析:")
    print("-" * 100)
    
    for i, buy_point in enumerate(buy_points):
        buy_date = buy_point['index']
        buy_price = buy_point['price']
        
        # 找到下一个卖点
        next_sell = None
        for sell_point in sell_points:
            if sell_point['index'] > buy_date:
                next_sell = sell_point
                break
        
        if next_sell:
            sell_date = next_sell['index']
            sell_price = next_sell['price']
            
            # 计算收益
            return_pct = (sell_price - buy_price) / buy_price * 100
            holding_days = (sell_date - buy_date).days
            
            # 检查期间的最高价和最低价
            buy_idx = data.index.get_loc(buy_date)
            sell_idx = data.index.get_loc(sell_date)
            period_high = data['High'].iloc[buy_idx:sell_idx].max()
            period_low = data['Low'].iloc[buy_idx:sell_idx].min()
            
            print(f"\n交易{i+1}:")
            print(f"  买入: {buy_date.strftime('%Y-%m-%d')} @ {buy_price:.2f}")
            print(f"  卖出: {sell_date.strftime('%Y-%m-%d')} @ {sell_price:.2f}")
            print(f"  收益: {return_pct:.2f}%")
            print(f"  持仓天数: {holding_days}天")
            print(f"  期间最高价: {period_high:.2f} (最高涨幅: {(period_high - buy_price) / buy_price * 100:.2f}%)")
            print(f"  期间最低价: {period_low:.2f} (最大跌幅: {(period_low - buy_price) / buy_price * 100:.2f}%)")
            
            # 分析问题
            if return_pct < 0:
                print(f"  ❌ 问题: 亏损交易！")
                if sell_price < buy_price * 0.5:
                    print(f"     卖出价格只有买入价格的{sell_price/buy_price*100:.1f}%，可能是卖点识别错误")
    
    print()
    print("=" * 100)
    print("调试完成")
    print("=" * 100)

if __name__ == '__main__':
    debug_buy_sell_logic()