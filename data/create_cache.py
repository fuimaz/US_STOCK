import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import pickle

def generate_realistic_stock_data(symbol: str, days: int = 252, start_price: float = 150.0) -> pd.DataFrame:
    """
    鐢熸垚閫肩湡鐨勮偂绁ㄦ暟鎹敤浜庣紦瀛?    
    Args:
        symbol: 鑲＄エ浠ｇ爜
        days: 鏁版嵁澶╂暟锛?52澶╃害绛変簬1骞达級
        start_price: 璧峰浠锋牸
    
    Returns:
        DataFrame鍖呭惈OHLCV鏁版嵁
    """
    np.random.seed(hash(symbol) % 2**32)
    
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='B')  # 宸ヤ綔鏃?    
    close_prices = [start_price]
    for i in range(1, days):
        change = np.random.normal(0, 0.02)  # 2%鐨勬棩娉㈠姩
        new_price = close_prices[-1] * (1 + change)
        close_prices.append(max(new_price, 10.0))  # 鏈€浣庝环鏍?0
    
    close_prices = np.array(close_prices)
    
    data = pd.DataFrame({
        'Open': close_prices * (1 + np.random.uniform(-0.01, 0.01, days)),
        'High': close_prices * (1 + np.random.uniform(0, 0.02, days)),
        'Low': close_prices * (1 + np.random.uniform(-0.02, 0, days)),
        'Close': close_prices,
        'Volume': np.random.randint(10000000, 100000000, days)
    }, index=dates)
    
    data.index.name = 'datetime'
    
    return data

def create_cache_data():
    """鍒涘缓缂撳瓨鏁版嵁"""
    cache_dir = 'data_cache'
    
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    stocks = [
        ('AAPL', 175.0, '1y'),
        ('MSFT', 380.0, '1y'),
        ('GOOGL', 140.0, '1y'),
        ('AMZN', 175.0, '1y'),
        ('TSLA', 200.0, '1y'),
        ('META', 480.0, '1y'),
        ('NVDA', 880.0, '1y'),
    ]
    
    print("=" * 60)
    print("鍒涘缓缂撳瓨鏁版嵁")
    print("=" * 60)
    
    for symbol, start_price, period in stocks:
        print(f"\n姝ｅ湪鐢熸垚 {symbol} 鐨勬暟鎹?..")
        
        data = generate_realistic_stock_data(symbol, days=252, start_price=start_price)
        
        cache_file = os.path.join(cache_dir, f'{symbol}_{period}_1d.pkl')
        
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"  鉁?宸蹭繚瀛樺埌 {cache_file}")
        print(f"  鉁?鏁版嵁鏉℃暟: {len(data)}")
        print(f"  鉁?鏃堕棿鑼冨洿: {data.index[0].date()} 鍒?{data.index[-1].date()}")
        print(f"  鉁?鏈€鏂版敹鐩樹环: ${data['Close'].iloc[-1]:.2f}")
    
    print("\n" + "=" * 60)
    print("鉁?缂撳瓨鏁版嵁鍒涘缓瀹屾垚锛?)
    print("=" * 60)
    print(f"\n缂撳瓨鐩綍: {os.path.abspath(cache_dir)}")
    print(f"缂撳瓨鏂囦欢鏁? {len(os.listdir(cache_dir))}")
    print("\n鐜板湪鍙互浣跨敤浠ヤ笅鍛戒护杩愯锛?)
    print("  python kline_tool.py -t 1d -s AAPL")
    print("  python kline_tool.py -t 1w -s MSFT")
    print("  python kline_tool.py -t 1m -s GOOGL")

if __name__ == '__main__':
    create_cache_data()

