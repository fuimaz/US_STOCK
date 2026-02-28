"""
获取A股股票的分钟级数据（5分钟、15分钟、30分钟）
保存到缓存目录
"""
import akshare as ak
import pandas as pd
import os
import time
from datetime import datetime

# 缓存目录
CACHE_DIR = 'data_cache'
OUTPUT_DIR = os.path.join(CACHE_DIR, 'a_stock_minute')

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 获取A股股票列表
def get_a_stock_list():
    """从缓存目录获取A股股票列表"""
    files = os.listdir(CACHE_DIR)
    a_stocks = set()
    for f in files:
        if f.endswith('.csv') and ('.SZ' in f or '.SS' in f) and 'china_futures' not in f:
            stock = f.split('_')[0]
            a_stocks.add(stock)
    return sorted(list(a_stocks))

def convert_to_akshare(symbol):
    """
    转换股票代码格式用于AKShare
    600519.SS -> sh600519
    000001.SZ -> sz000001
    """
    if '.SS' in symbol:
        code = symbol.replace('.SS', '')
        return f"sh{code}"
    elif '.SZ' in symbol:
        code = symbol.replace('.SZ', '')
        return f"sz{code}"
    return symbol

def convert_to_original(akshare_symbol):
    """AKShare格式转换为原始格式"""
    if akshare_symbol.startswith('sh'):
        return akshare_symbol.replace('sh', '') + '.SS'
    elif akshare_symbol.startswith('sz'):
        return akshare_symbol.replace('sz', '') + '.SZ'
    return akshare_symbol

def fetch_minute_data(symbol, period='5', max_retries=3, adjust='qfq'):
    """获取分钟级数据
    
    Args:
        adjust: ''=不复权, 'qfq'=前复权(推荐), 'hfq'=后复权
    """
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_minute(symbol=symbol, period=period, adjust=adjust)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"  ✗ {symbol} {period}分钟数据获取失败: {e}")
    return None

def save_to_cache(df, stock_code, period):
    """保存数据到缓存
    
    Args:
        df: 数据DataFrame
        stock_code: AKShare格式的股票代码 (如 sh600519, sz000001)
        period: 周期
    """
    # 转换为原始格式
    original = convert_to_original(stock_code)
    
    filename = f"{original}_{period}min.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # 重命名列
    df = df.rename(columns={'day': 'datetime'})
    df.to_csv(filepath)
    return filepath

def main():
    print("=" * 60)
    print("A股分钟级数据获取工具")
    print("=" * 60)
    
    # 获取股票列表
    stocks = get_a_stock_list()
    print(f"\n找到 {len(stocks)} 只A股股票")
    
    # 要获取的周期
    periods = ['5', '15', '30']
    
    # 统计
    stats = {'success': 0, 'failed': 0}
    
    # 遍历所有股票
    for i, stock in enumerate(stocks):
        # 转换为AKShare格式
        akshare_symbol = convert_to_akshare(stock)
        
        print(f"\n[{i+1}/{len(stocks)}] 处理 {stock} ({akshare_symbol}):")
        
        for period in periods:
            # 期望的输出文件名
            original = convert_to_original(akshare_symbol)
            filename = f"{original}_{period}min.csv"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            if os.path.exists(filepath):
                print(f"  ✓ {period}分钟数据已存在，跳过")
                stats['success'] += 1
                continue
            
            # 获取数据
            print(f"  获取{period}分钟数据...", end='', flush=True)
            df = fetch_minute_data(akshare_symbol, period)
            
            if df is not None and not df.empty:
                filepath = save_to_cache(df, akshare_symbol, period)
                print(f" ✓ 保存成功 ({len(df)}条)")
                stats['success'] += 1
            else:
                print(f" ✗ 获取失败")
                stats['failed'] += 1
            
            # 避免请求过快
            time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("完成!")
    print(f"成功: {stats['success']}")
    print(f"失败: {stats['failed']}")
    print(f"数据保存位置: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == '__main__':
    main()
