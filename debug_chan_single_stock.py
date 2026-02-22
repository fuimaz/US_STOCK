"""
调试缠论回测问题
"""
import pandas as pd
import os
from chan_theory_v5 import ChanTheory

def debug_single_stock():
    """
    调试单只股票
    """
    # 选择一个股票进行调试
    filepath = 'data_cache/600519.SS_20y_1d_forward.csv'
    symbol = '600519.SS'
    
    print("=" * 100)
    print(f"调试股票: {symbol}")
    print("=" * 100)
    print()
    
    # 读取数据
    data = pd.read_csv(filepath, index_col='Date', parse_dates=True)
    
    print(f"✓ 数据读取完成，共 {len(data)} 条记录")
    print(f"  时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    print()
    
    # 初始化缠论指标
    chan = ChanTheory(k_type='day')
    
    try:
        # 识别分型
        print("正在识别分型...")
        data = chan.identify_fenxing(data)
        print(f"✓ 分型识别完成，共 {len(chan.fenxing_list)} 个分型")
        print()
        
        # 识别笔
        print("正在识别笔...")
        data = chan.identify_bi(data)
        print(f"✓ 笔识别完成，共 {len(chan.bi_list)} 个笔")
        print()
        
        # 识别线段
        print("正在识别线段...")
        data = chan.identify_xianduan(data)
        print(f"✓ 线段识别完成，共 {len(chan.xianduan_list)} 个线段")
        print()
        
        # 识别中枢
        print("正在识别中枢...")
        data = chan.identify_zhongshu(data)
        print(f"✓ 中枢识别完成，共 {len(chan.zhongshu_list)} 个中枢")
        print()
        
        # 识别买卖点
        print("正在识别买卖点...")
        data = chan.identify_buy_sell_points(data)
        print(f"✓ 买卖点识别完成，买点: {len(chan.buy_points)}, 卖点: {len(chan.sell_points)}")
        print()
        
        print("=" * 100)
        print("调试完成！")
        print("=" * 100)
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_single_stock()