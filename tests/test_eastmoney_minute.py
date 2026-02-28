"""
东方财富接口获取A股分钟级数据
不需要代理，在其他网络环境下使用
"""
import akshare as ak
import pandas as pd
from datetime import datetime

# ==================== A股分钟数据 ====================

def fetch_a_stock_minute_eastmoney(symbol='600519', period='5', start_date='', end_date='', adjust=''):
    """
    获取A股分钟级数据（东方财富接口）
    
    参数:
        symbol: 股票代码，如 '600519' (茅台), '000001' (平安银行)
        period: 周期 ('1', '5', '15', '30', '60')
        start_date: 开始日期，格式 'YYYY-MM-DD HH:MM:SS'，默认为空
        end_date: 结束日期，格式 'YYYY-MM-DD HH:MM:SS'，默认为空
        adjust: 复权类型: '' (不复权), 'qfq' (前复权), 'hfq' (后复权)
    
    返回:
        DataFrame
    """
    df = ak.stock_zh_a_hist_min_em(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        period=period,
        adjust=adjust
    )
    return df


# ==================== 期货分钟数据 ====================

def fetch_futures_minute_sina(symbol='RB0', period='5'):
    """
    获取期货分钟级数据（新浪接口）
    
    参数:
        symbol: 期货代码，如 'RB0' (螺纹钢), 'I0' (铁矿石), 'SC0' (原油)
        period: 周期 ('1', '5', '15', '30', '60')
    
    返回:
        DataFrame
    """
    df = ak.futures_zh_minute_sina(symbol=symbol, period=period)
    return df


# ==================== 测试代码 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("A股分钟级数据 - 东方财富接口")
    print("=" * 60)
    
    symbol = '600519'  # 茅台
    
    # 测试不同周期
    periods = [('5', '5分钟'), ('15', '15分钟'), ('30', '30分钟'), ('60', '60分钟')]
    
    for period, name in periods:
        print(f"\n{name}数据:")
        try:
            df = fetch_a_stock_minute_eastmoney(symbol=symbol, period=period)
            if df is not None and not df.empty:
                print(f"   数据条数: {len(df)}")
                print(f"   前3行:\n{df.head(3)}")
            else:
                print(f"   无数据")
        except Exception as e:
            print(f"   获取失败: {e}")
    
    print("\n" + "=" * 60)
    print("期货分钟级数据 - 新浪接口")
    print("=" * 60)
    
    futures_symbol = 'RB0'  # 螺纹钢
    
    for period, name in periods:
        print(f"\n{name}数据:")
        try:
            df = fetch_futures_minute_sina(symbol=futures_symbol, period=period)
            if df is not None and not df.empty:
                print(f"   数据条数: {len(df)}")
                print(f"   前3行:\n{df.head(3)}")
            else:
                print(f"   无数据")
        except Exception as e:
            print(f"   获取失败: {e}")
