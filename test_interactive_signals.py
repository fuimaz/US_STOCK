import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from weekly_boll_strategy import WeeklyBollingerStrategy
from interactive_kline import InteractiveKLineViewer


def test_interactive_with_signals():
    """
    测试交互式K线图与买卖点标记
    """
    print("=" * 80)
    print("测试交互式K线图与买卖点标记")
    print("=" * 80)
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 获取AAPL数据
    symbol = 'AAPL'
    period = '20y'
    
    print(f"\n正在获取 {symbol} 数据...")
    daily_data = fetcher.fetch_stock_data(symbol, period=period, adjust='forward')
    
    # 确保索引是日期时间格式（统一时区）
    if not isinstance(daily_data.index, pd.DatetimeIndex):
        daily_data.index = pd.to_datetime(daily_data.index, utc=True)
    else:
        daily_data.index = daily_data.index.tz_convert(None)
    
    print(f"✓ 数据获取成功: {len(daily_data)} 条")
    print(f"时间范围: {daily_data.index[0].strftime('%Y-%m-%d')} 到 {daily_data.index[-1].strftime('%Y-%m-%d')}")
    
    # 创建策略
    strategy = WeeklyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
    
    # 生成信号
    print("\n正在生成交易信号...")
    data_with_signals = strategy.generate_signals(daily_data)
    
    # 统计信号
    signals = data_with_signals[data_with_signals['signal'] != 0]
    buy_signals = data_with_signals[data_with_signals['signal'] == 1]
    sell_signals = data_with_signals[data_with_signals['signal'] == -1]
    
    print(f"✓ 信号生成完成")
    print(f"  总信号数: {len(signals)}")
    print(f"  买入信号: {len(buy_signals)}")
    print(f"  卖出信号: {len(sell_signals)}")
    
    # 保存信号文件
    signals_file = 'weekly_boll_AAPL_signals.csv'
    data_with_signals.to_csv(signals_file)
    print(f"✓ 信号文件已保存到: {signals_file}")
    
    # 创建交互式查看器
    print(f"\n正在创建交互式图表...")
    print(f"\n操作说明：")
    print(f"  - 鼠标拖拽：左右移动K线")
    print(f"  - 鼠标滚轮：缩放K线数量")
    print(f"  - 鼠标悬停：查看详细信息")
    print(f"  - 红色向上箭头：买入点")
    print(f"  - 绿色向下箭头：卖出点")
    
    viewer = InteractiveKLineViewer(daily_data, title=f'{symbol} 交互式K线图（含买卖点标记）', signals=data_with_signals)
    viewer.show()


if __name__ == '__main__':
    test_interactive_with_signals()
