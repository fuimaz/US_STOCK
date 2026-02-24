"""
调试缠论线段识别
"""
import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from chan_theory_v2 import ChanTheory

def debug_xianduan():
    """
    调试线段识别
    """
    print("=" * 100)
    print("调试缠论线段识别")
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
    print(f"✓ 识别分型完成，共 {len(chan.fenxing_list)} 个分型")
    
    # 识别笔
    data = chan.identify_bi(data)
    print(f"✓ 识别笔完成，共 {len(chan.bi_list)} 个笔")
    print()
    
    # 分析笔数据
    print("笔数据分析（前20个）:")
    print("-" * 100)
    
    for i, bi in enumerate(chan.bi_list[:20]):
        print(f"  笔{i+1}: {bi['start'].strftime('%Y-%m-%d')} -> {bi['end'].strftime('%Y-%m-%d')}")
        print(f"    类型: {'向上' if bi['type'] == 1 else '向下'}")
        print(f"    价格: {bi['start_price']:.2f} -> {bi['end_price']:.2f}")
        print(f"    涨跌幅: {((bi['end_price'] - bi['start_price']) / bi['start_price'] * 100):.2f}%")
        print()
    
    # 手动识别线段
    print("手动识别线段:")
    print("-" * 100)
    
    current_xianduan = None
    bi_count = 0
    
    for i, bi in enumerate(chan.bi_list):
        bi_type = bi['type']
        
        print(f"\n笔{i+1}: 类型={'向上' if bi_type == 1 else '向下'}")
        
        if current_xianduan is None:
            print(f"  开始新的线段，类型={'向上' if bi_type == 1 else '向下'}")
            current_xianduan = {
                'type': bi_type,
                'start': bi['start'],
                'end': bi['end'],
                'bi_list': [bi],
                'high': bi['end_price'] if bi_type == 1 else bi['start_price'],
                'low': bi['start_price'] if bi_type == 1 else bi['end_price']
            }
            bi_count = 1
        elif bi_type == current_xianduan['type']:
            print(f"  同方向的笔，继续当前线段（当前笔数：{bi_count}）")
            current_xianduan['bi_list'].append(bi)
            current_xianduan['end'] = bi['end']
            
            if bi_type == 1:
                current_xianduan['high'] = max(current_xianduan['high'], bi['end_price'])
                current_xianduan['low'] = min(current_xianduan['low'], bi['start_price'])
            else:
                current_xianduan['high'] = max(current_xianduan['high'], bi['start_price'])
                current_xianduan['low'] = min(current_xianduan['low'], bi['end_price'])
            
            bi_count += 1
        else:
            print(f"  反向笔，当前笔数：{bi_count}")
            if bi_count >= 3:
                print(f"  ✓ 线段结束！共{bi_count}笔")
                print(f"    起始: {current_xianduan['start'].strftime('%Y-%m-%d')}")
                print(f"    结束: {current_xianduan['end'].strftime('%Y-%m-%d')}")
                print(f"    类型: {'向上' if current_xianduan['type'] == 1 else '向下'}")
                print(f"    高点: {current_xianduan['high']:.2f}")
                print(f"    低点: {current_xianduan['low']:.2f}")
            else:
                print(f"  ✗ 笔数不足（需要至少3笔），重置线段")
            
            current_xianduan = {
                'type': bi_type,
                'start': bi['start'],
                'end': bi['end'],
                'bi_list': [bi],
                'high': bi['end_price'] if bi_type == 1 else bi['start_price'],
                'low': bi['start_price'] if bi_type == 1 else bi['end_price']
            }
            bi_count = 1
    
    # 检查最后一个线段
    if current_xianduan is not None and bi_count >= 3:
        print(f"\n最后一个线段:")
        print(f"  ✓ 线段结束！共{bi_count}笔")
        print(f"    起始: {current_xianduan['start'].strftime('%Y-%m-%d')}")
        print(f"    结束: {current_xianduan['end'].strftime('%Y-%m-%d')}")
        print(f"    类型: {'向上' if current_xianduan['type'] == 1 else '向下'}")
        print(f"    高点: {current_xianduan['high']:.2f}")
        print(f"    低点: {current_xianduan['low']:.2f}")
    
    print()
    print("=" * 100)
    print("调试完成")
    print("=" * 100)

if __name__ == '__main__':
    debug_xianduan()