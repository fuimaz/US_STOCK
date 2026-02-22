import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import pickle

def generate_realistic_stock_data(symbol: str, days: int = 252, start_price: float = 150.0) -> pd.DataFrame:
    """
    生成逼真的股票数据用于缓存
    
    Args:
        symbol: 股票代码
        days: 数据天数（252天约等于1年）
        start_price: 起始价格
    
    Returns:
        DataFrame包含OHLCV数据
    """
    np.random.seed(hash(symbol) % 2**32)
    
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='B')  # 工作日
    
    close_prices = [start_price]
    for i in range(1, days):
        change = np.random.normal(0, 0.02)  # 2%的日波动
        new_price = close_prices[-1] * (1 + change)
        close_prices.append(max(new_price, 10.0))  # 最低价格10
    
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
    """创建缓存数据"""
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
    print("创建缓存数据")
    print("=" * 60)
    
    for symbol, start_price, period in stocks:
        print(f"\n正在生成 {symbol} 的数据...")
        
        data = generate_realistic_stock_data(symbol, days=252, start_price=start_price)
        
        cache_file = os.path.join(cache_dir, f'{symbol}_{period}_1d.pkl')
        
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"  ✓ 已保存到 {cache_file}")
        print(f"  ✓ 数据条数: {len(data)}")
        print(f"  ✓ 时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
        print(f"  ✓ 最新收盘价: ${data['Close'].iloc[-1]:.2f}")
    
    print("\n" + "=" * 60)
    print("✓ 缓存数据创建完成！")
    print("=" * 60)
    print(f"\n缓存目录: {os.path.abspath(cache_dir)}")
    print(f"缓存文件数: {len(os.listdir(cache_dir))}")
    print("\n现在可以使用以下命令运行：")
    print("  python kline_tool.py -t 1d -s AAPL")
    print("  python kline_tool.py -t 1w -s MSFT")
    print("  python kline_tool.py -t 1m -s GOOGL")

if __name__ == '__main__':
    create_cache_data()
