"""
调试缠论买卖点识别
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from chan_theory import ChanTheory

def debug_buy_sell_points():
    """
    调试买卖点识别
    """
    print("=" * 100)
    print("调试缠论买卖点识别")
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
    
    # 识别分型
    data = chan.identify_fenxing(data)
    print(f"✓ 识别分型完成，共 {len(data[data['fenxing_type'] != 0])} 个分型")
    
    # 识别笔
    data = chan.identify_bi(data)
    print(f"✓ 识别笔完成，共 {len(data[data['bi_type'] != 0])} 个笔")
    
    # 识别线段
    data = chan.identify_xianduan(data)
    print(f"✓ 识别线段完成，共 {len(data[data['xianduan_type'] != 0])} 个线段")
    
    # 识别中枢
    data = chan.identify_zhongshu(data)
    print(f"✓ 识别中枢完成，共 {len(data[data['zhongshu_type'] != 0])} 个中枢")
    print()
    
    # 分析中枢数据
    zhongshu_data = data[data['zhongshu_type'] != 0]
    
    if len(zhongshu_data) > 0:
        print("中枢数据分析:")
        print("-" * 100)
        
        for idx, row in zhongshu_data.head(10).iterrows():
            print(f"  {idx.strftime('%Y-%m-%d')}: 中枢区间 [{row['zhongshu_low']:.2f}, {row['zhongshu_high']:.2f}]")
            print(f"    线段类型: {'向上' if row['xianduan_type'] == 1 else '向下'}")
            print(f"    线段起点: {row['xianduan_start']:.2f}")
            print(f"    线段终点: {row['xianduan_end']:.2f}")
            print()
    
    # 分析线段数据
    xianduan_data = data[data['xianduan_type'] != 0]
    
    if len(xianduan_data) > 0:
        print("线段数据分析:")
        print("-" * 100)
        
        last_zhongshu_high = None
        last_zhongshu_low = None
        last_xianduan_type = None
        
        for idx, row in xianduan_data.head(20).iterrows():
            xianduan_type = row['xianduan_type']
            zhongshu_high = row['zhongshu_high']
            zhongshu_low = row['zhongshu_low']
            
            print(f"  {idx.strftime('%Y-%m-%d')}:")
            print(f"    线段类型: {'向上' if xianduan_type == 1 else '向下'}")
            print(f"    线段终点: {row['xianduan_end']:.2f}")
            print(f"    是否在中枢: {'是' if pd.notna(zhongshu_high) else '否'}")
            
            if pd.notna(zhongshu_high) and pd.notna(zhongshu_low):
                print(f"    中枢区间: [{zhongshu_low:.2f}, {zhongshu_high:.2f}]")
                last_zhongshu_high = zhongshu_high
                last_zhongshu_low = zhongshu_low
            else:
                print(f"    前一个中枢: [{last_zhongshu_low:.2f}, {last_zhongshu_high:.2f}]" if last_zhongshu_high is not None else "    前一个中枢: 无")
            
            # 检查第一类买卖点
            if last_xianduan_type is not None and last_zhongshu_high is not None:
                if last_xianduan_type == -1 and xianduan_type == 1:
                    # 向下线段结束后，出现向上线段
                    if row['xianduan_end'] > last_zhongshu_high:
                        print(f"    ✓ 第一类买点！线段终点 {row['xianduan_end']:.2f} > 中枢高点 {last_zhongshu_high:.2f}")
                    else:
                        print(f"    ✗ 不是第一类买点：线段终点 {row['xianduan_end']:.2f} <= 中枢高点 {last_zhongshu_high:.2f}")
                elif last_xianduan_type == 1 and xianduan_type == -1:
                    # 向上线段结束后，出现向下线段
                    if row['xianduan_end'] < last_zhongshu_low:
                        print(f"    ✓ 第一类卖点！线段终点 {row['xianduan_end']:.2f} < 中枢低点 {last_zhongshu_low:.2f}")
                    else:
                        print(f"    ✗ 不是第一类卖点：线段终点 {row['xianduan_end']:.2f} >= 中枢低点 {last_zhongshu_low:.2f}")
            else:
                print(f"    ✗ 无法检查买卖点：last_xianduan_type={last_xianduan_type}, last_zhongshu_high={last_zhongshu_high}")
            
            last_xianduan_type = xianduan_type
            print()
    
    print("=" * 100)
    print("调试完成")
    print("=" * 100)

if __name__ == '__main__':
    debug_buy_sell_points()