"""
测试AKShare获取A股超过3个月的分钟级数据
验证数据完整性和时间范围
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

# 测试获取A股分钟级数据
# A股股票代码格式: 'sh600519' (上海), 'sz000001' (深圳)

def analyze_time_range(df):
    """分析数据的时间范围"""
    if df.empty:
        return None
    
    # 找到时间列
    time_col = None
    for col in ['day', 'datetime', '时间', 'date']:
        if col in df.columns:
            time_col = col
            break
    
    if time_col is None:
        # 假设索引是时间
        if hasattr(df.index, 'year'):
            times = df.index
        else:
            return None
    else:
        times = pd.to_datetime(df[time_col])
    
    start_time = times.min()
    end_time = times.max()
    
    return {
        'start': start_time,
        'end': end_time,
        'days': (end_time - start_time).days,
        'count': len(df)
    }

def test_a_stock_minute_data():
    """测试获取A股分钟级数据"""
    print("=" * 60)
    print("测试AKShare获取A股分钟级数据")
    print("=" * 60)
    
    # 测试股票: 茅台 (sh600519)
    symbol = 'sh600519'
    
    print(f"\n1. 测试 stock_zh_a_minute (新浪分钟数据 - 5分钟):")
    try:
        df = ak.stock_zh_a_minute(symbol=symbol, period='5', adjust='')
        print(f"   数据形状: {df.shape}")
        print(f"   列名: {df.columns.tolist()}")
        print(f"   前3行:\n{df.head(3)}")
        print(f"   后3行:\n{df.tail(3)}")
        
        if not df.empty:
            info = analyze_time_range(df)
            if info:
                print(f"\n   ✓ 数据时间范围:")
                print(f"   开始时间: {info['start']}")
                print(f"   结束时间: {info['end']}")
                print(f"   数据跨度: {info['days']} 天")
                print(f"   数据条数: {info['count']}")
                
                if info['days'] > 90:
                    print(f"   ✓ 数据超过3个月!")
    except Exception as e:
        print(f"   ✗ 获取失败: {e}")

def test_long_period_data():
    """测试获取超过3个月的分钟级数据"""
    print("\n" + "=" * 60)
    print("测试获取超过3个月的分钟级数据 - 不同周期对比")
    print("=" * 60)
    
    # 测试股票: 茅台 (sh600519)
    symbol = 'sh600519'
    
    periods = [
        ('1', '1分钟'),
        ('5', '5分钟'),
        ('15', '15分钟'),
        ('30', '30分钟'),
        ('60', '60分钟')
    ]
    
    for period, name in periods:
        print(f"\n{name}数据:")
        try:
            df = ak.stock_zh_a_minute(symbol=symbol, period=period, adjust='')
            if not df.empty:
                info = analyze_time_range(df)
                if info:
                    print(f"   数据条数: {info['count']}")
                    print(f"   开始: {info['start']}")
                    print(f"   结束: {info['end']}")
                    print(f"   跨度: {info['days']} 天 ({info['days']/30:.1f} 个月)")
                    
                    # 判断是否超过3个月
                    if info['days'] > 90:
                        print(f"   ✓ 超过3个月!")
                    else:
                        print(f"   ✗ 不足3个月")
            else:
                print(f"   ✗ 无数据")
        except Exception as e:
            print(f"   ✗ 获取失败: {e}")

def test_different_stocks():
    """测试不同股票"""
    print("\n" + "=" * 60)
    print("测试不同A股股票的分钟数据")
    print("=" * 60)
    
    test_symbols = [
        ('sh600519', '贵州茅台'),
        ('sz000001', '平安银行'),
        ('sh600036', '招商银行'),
        ('sz000858', '五粮液'),
    ]
    
    for symbol, name in test_symbols:
        print(f"\n{name} ({symbol}):")
        try:
            df = ak.stock_zh_a_minute(symbol=symbol, period='5', adjust='')
            if not df.empty:
                info = analyze_time_range(df)
                if info:
                    print(f"   数据条数: {info['count']}")
                    print(f"   跨度: {info['days']} 天")
            else:
                print(f"   ✗ 无数据")
        except Exception as e:
            print(f"   ✗ 获取失败: {e}")

def test_with_adjustment():
    """测试复权数据"""
    print("\n" + "=" * 60)
    print("测试复权数据")
    print("=" * 60)
    
    symbol = 'sh600519'
    
    for adjust in ['', 'qfq', 'hfq']:
        adjust_name = {'': '不复权', 'qfq': '前复权', 'hfq': '后复权'}.get(adjust, adjust)
        print(f"\n{adjust_name}:")
        try:
            df = ak.stock_zh_a_minute(symbol=symbol, period='5', adjust=adjust)
            if not df.empty:
                info = analyze_time_range(df)
                if info:
                    print(f"   数据条数: {info['count']}")
                    print(f"   起始价: {df['open'].iloc[0]:.2f}")
                    print(f"   结束价: {df['close'].iloc[-1]:.2f}")
            else:
                print(f"   ✗ 无数据")
        except Exception as e:
            print(f"   ✗ 获取失败: {e}")

if __name__ == '__main__':
    test_a_stock_minute_data()
    test_long_period_data()
    test_different_stocks()
    test_with_adjustment()
