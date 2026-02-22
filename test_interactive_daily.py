import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.lines import Line2D
from data_fetcher import DataFetcher
from daily_boll_strategy import DailyBollingerStrategy


# 配置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def test_interactive_daily_signals():
    """
    测试交互式日线K线图与买卖点标记
    """
    print("=" * 80)
    print("测试交互式日线K线图与买卖点标记")
    print("=" * 80)
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 测试股票
    symbol = 'AAPL'
    period = '5y'
    
    print(f"\n正在获取 {symbol} 数据...")
    daily_data = fetcher.fetch_stock_data(symbol, period=period, adjust='forward')
    
    # 确保索引是日期时间格式
    if not isinstance(daily_data.index, pd.DatetimeIndex):
        daily_data.index = pd.to_datetime(daily_data.index, utc=True)
    else:
        daily_data.index = daily_data.index.tz_convert(None)
    
    print(f"✓ 数据获取成功: {len(daily_data)} 条")
    print(f"时间范围: {daily_data.index[0].strftime('%Y-%m-%d')} 到 {daily_data.index[-1].strftime('%Y-%m-%d')}")
    print()
    
    # 创建策略
    strategy = DailyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.05)
    
    print("正在生成交易信号...")
    data_with_signals = strategy.generate_signals(daily_data)
    
    # 统计信号
    signals = data_with_signals[data_with_signals['signal'] != 0]
    buy_signals = data_with_signals[data_with_signals['signal'] == 1]
    sell_signals = data_with_signals[data_with_signals['signal'] == -1]
    
    print(f"✓ 信号生成完成")
    print(f"  总信号数: {len(signals)}")
    print(f"  买入信号: {len(buy_signals)}")
    print(f"  卖出信号: {len(sell_signals)}")
    print()
    
    # 保存信号文件
    output_file = f'daily_boll_{symbol}_signals.csv'
    data_with_signals.to_csv(output_file)
    print(f"✓ 信号文件已保存到: {output_file}")
    print()
    
    # 创建交互式图表
    print("正在创建交互式图表...")
    from interactive_kline import InteractiveKLineViewer
    
    viewer = InteractiveKLineViewer(
        data_with_signals,
        title=f'{symbol} 日线布林带策略',
        signals=data_with_signals[['signal']]
    )
    
    print()
    print("操作说明：")
    print("  - 鼠标拖拽：左右移动K线")
    print("  - 鼠标滚轮：缩放K线数量")
    print("  - 鼠标悬停：查看详细信息")
    print("  - 红色向上箭头：买入点")
    print("  - 绿色向下箭头：卖出点")
    print()
    
    plt.show()


if __name__ == '__main__':
    test_interactive_daily_signals()
