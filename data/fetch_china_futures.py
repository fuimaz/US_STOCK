"""
获取国内期货分钟级数据并缓存到本地
使用 akshare 库获取数据
"""
import akshare as ak
import pandas as pd
import os
from datetime import datetime

# 热门期货品种列表
FUTURES_SYMBOLS = {
    # 黑色系
    'I0': '铁矿石',
    'RB0': '螺纹钢',
    'JM0': '焦煤',
    'J0': '焦炭',
    'HC0': '热卷',
    # 能源化工
    'SC0': '原油',
    'RU0': '橡胶',
    'TA0': 'PTA',
    'MA0': '甲醇',
    'FG0': '玻璃',
    # 有色金属
    'CU0': '沪铜',
    'AL0': '沪铝',
    'ZN0': '沪锌',
    'PB0': '沪铅',
    'NI0': '沪镍',
    # 农产品
    'M0': '豆粕',
    'Y0': '豆油',
    'C0': '玉米',
    'CS0': '玉米淀粉',
    'SR0': '白糖',
    'CF0': '棉花',
    # 贵金属
    'AU0': '黄金',
    'AG0': '白银',
}

# 时间周期选项
PERIODS = ['5', '15', '30', '60']

def fetch_futures_minute_data(symbol: str, period: str = '5') -> pd.DataFrame:
    """获取期货分钟级数据"""
    try:
        df = ak.futures_zh_minute_sina(symbol=symbol, period=period)
        return df
    except Exception as e:
        print(f"  ✗ 获取 {symbol} {period}分钟数据失败: {e}")
        return None

def save_to_cache(data: pd.DataFrame, symbol: str, period: str):
    """保存数据到本地缓存"""
    cache_dir = os.path.join(os.path.dirname(__file__), 'data_cache', 'china_futures')
    os.makedirs(cache_dir, exist_ok=True)
    
    filename = f"{symbol}_{period}min.csv"
    filepath = os.path.join(cache_dir, filename)
    
    data.to_csv(filepath)
    print(f"  ✓ 已保存: {filepath}")

def main():
    print("=" * 60)
    print("国内期货分钟级数据获取工具")
    print("=" * 60)
    
    # 只获取5分钟数据（最新的）
    period = '5'
    
    success_count = 0
    fail_count = 0
    
    for symbol, name in FUTURES_SYMBOLS.items():
        print(f"\n正在获取 {name}({symbol}) {period}分钟数据...")
        
        df = fetch_futures_minute_data(symbol, period)
        
        if df is not None and not df.empty:
            save_to_cache(df, symbol, period)
            print(f"  ✓ 成功获取 {len(df)} 条数据")
            success_count += 1
        else:
            print(f"  ✗ 获取数据失败")
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"完成! 成功: {success_count}, 失败: {fail_count}")
    print(f"数据保存位置: {os.path.join(os.path.dirname(__file__), 'data_cache', 'china_futures')}")
    print("=" * 60)

if __name__ == '__main__':
    main()
