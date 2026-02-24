"""
缠论实时买点扫描 - 演示版本
使用历史数据模拟，展示信号检测效果
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from chan_theory_realtime import ChanTheoryRealtime


def scan_stock_demo(symbol, name):
    """扫描单个股票的买点信号"""
    # 加载缓存数据
    cache_file = f'data_cache/{symbol}_20y_1d_forward.csv'
    if not os.path.exists(cache_file):
        return None
    
    try:
        data = pd.read_csv(cache_file)
        if 'datetime' in data.columns:
            data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
            data = data.set_index('datetime')
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        data = data.dropna()
        
        # 只使用近1个月数据演示
        data = data.tail(30)
        
        # 使用缠论分析
        chan = ChanTheoryRealtime(k_type='day')
        result = chan.analyze(data)
        
        # 获取买点信号
        if not chan.buy_points:
            return None
        
        # 找出所有买点
        signals = []
        for bp in chan.buy_points:
            signals.append({
                'symbol': symbol,
                'name': name,
                'date': bp['index'].strftime('%Y-%m-%d'),
                'type': f"第{bp['type']}类买点",
                'price': round(bp['price'], 2),
            })
        
        return signals
        
    except Exception as e:
        print(f"Error scanning {symbol}: {e}")
        return None


def main():
    """演示主函数"""
    print("=" * 100)
    print("Chan Theory Real-time Buy Signal Scan - DEMO")
    print("=" * 100)
    print()
    
    # 测试几只股票
    test_stocks = [
        ('000001.SZ', 'Ping An Bank'),
        ('000333.SZ', 'Midea Group'),
        ('600519.SS', 'Kweichow Moutai'),
        ('002594.SZ', 'BYD'),
        ('601012.SS', 'LONGi Green Energy'),
    ]
    
    all_signals = []
    
    for symbol, name in test_stocks:
        print(f"Scanning: {name} ({symbol})")
        signals = scan_stock_demo(symbol, name)
        
        if signals:
            print(f"  Found {len(signals)} buy signals:")
            for s in signals:
                print(f"    - Date: {s['date']}, Type: {s['type']}, Price: {s['price']}")
            all_signals.extend(signals)
        else:
            print(f"  No buy signals in recent 30 days")
        print()
    
    # 汇总
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    
    if all_signals:
        print(f"Total buy signals found: {len(all_signals)}")
        print()
        print(f"{'Symbol':<12} {'Name':<20} {'Date':<12} {'Type':<12} {'Price':<10}")
        print("-" * 70)
        for s in all_signals:
            print(f"{s['symbol']:<12} {s['name']:<20} {s['date']:<12} {s['type']:<12} {s['price']:<10}")
    else:
        print("No buy signals found in test stocks")
    
    print("=" * 100)
    print()
    print("Note: This is a demo using historical data.")
    print("For real-time scanning, use: python scan_buy_signals_realtime.py")


if __name__ == '__main__':
    main()
