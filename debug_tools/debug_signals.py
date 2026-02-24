import pandas as pd
import numpy as np
from data_fetcher import DataFetcher
from weekly_boll_strategy import WeeklyBollingerStrategy

# 初始化数据获取器
fetcher = DataFetcher(
    cache_dir='data_cache',
    cache_days=365,
    proxy='http://127.0.0.1:7897',
    retry_count=5,
    retry_delay=5.0
)

# 获取数据
symbol = 'AAPL'
period = '5y'

daily_data = fetcher.fetch_stock_data(symbol, period=period, adjust='forward')

# 确保索引是日期时间格式（统一时区）
if not isinstance(daily_data.index, pd.DatetimeIndex):
    daily_data.index = pd.to_datetime(daily_data.index, utc=True)
else:
    daily_data.index = daily_data.index.tz_convert(None)

# 创建策略
strategy = WeeklyBollingerStrategy(period=20, std_dev=2, middle_threshold=0.02)

# 生成信号
data_with_signals = strategy.generate_signals(daily_data)

# 统计信号
signals = data_with_signals[data_with_signals['signal'] != 0]
buy_signals = data_with_signals[data_with_signals['signal'] == 1]
sell_signals = data_with_signals[data_with_signals['signal'] == -1]
ready_to_buy = data_with_signals[data_with_signals['ready_to_buy'] == True]
ready_to_sell = data_with_signals[data_with_signals['ready_to_sell'] == True]

print("=" * 100)
print(f"{symbol} 策略信号分析")
print("=" * 100)
print()
print(f"总信号数: {len(signals)}")
print(f"买入信号: {len(buy_signals)}")
print(f"卖出信号: {len(sell_signals)}")
print(f"准备买入: {len(ready_to_buy)}")
print(f"准备卖出: {len(ready_to_sell)}")
print()

# 显示准备买入的情况
if len(ready_to_buy) > 0:
    print("准备买入的情况：")
    print("-" * 100)
    for i in range(min(20, len(ready_to_buy))):
        idx = ready_to_buy.index[i]
        close = ready_to_buy['Close'].iloc[i]
        middle = ready_to_buy['Middle'].iloc[i]
        upper = ready_to_buy['Upper'].iloc[i]
        lower = ready_to_buy['Lower'].iloc[i]
        market_phase = ready_to_buy['market_phase'].iloc[i]
        prev_market_phase = data_with_signals.loc[data_with_signals.index.get_loc(idx) - 1, 'market_phase'] if data_with_signals.index.get_loc(idx) > 0 else 'N/A'
        print(f"{idx.strftime('%Y-%m-%d')}: 收盘价 ${close:.2f} | 中线 ${middle:.2f} | 上轨 ${upper:.2f} | 下轨 ${lower:.2f} | 市场状态: {market_phase} | 前一日状态: {prev_market_phase}")
    print("-" * 100)
    print()

# 显示准备卖出的情况
if len(ready_to_sell) > 0:
    print("准备卖出的情况：")
    print("-" * 100)
    for i in range(min(20, len(ready_to_sell))):
        idx = ready_to_sell.index[i]
        close = ready_to_sell['Close'].iloc[i]
        middle = ready_to_sell['Middle'].iloc[i]
        upper = ready_to_sell['Upper'].iloc[i]
        lower = ready_to_sell['Lower'].iloc[i]
        below_count = ready_to_sell['below_middle_count'].iloc[i]
        print(f"{idx.strftime('%Y-%m-%d')}: 收盘价 ${close:.2f} | 中线 ${middle:.2f} | 上轨 ${upper:.2f} | 下轨 ${lower:.2f} | 跌破中线次数: {below_count}")
    print("-" * 100)
    print()

# 显示买入信号
if len(buy_signals) > 0:
    print("买入信号：")
    print("-" * 100)
    for i in range(min(20, len(buy_signals))):
        idx = buy_signals.index[i]
        close = buy_signals['Close'].iloc[i]
        middle = buy_signals['Middle'].iloc[i]
        upper = buy_signals['Upper'].iloc[i]
        lower = buy_signals['Lower'].iloc[i]
        print(f"{idx.strftime('%Y-%m-%d')}: 收盘价 ${close:.2f} | 中线 ${middle:.2f} | 上轨 ${upper:.2f} | 下轨 ${lower:.2f}")
    print("-" * 100)
    print()

# 显示卖出信号
if len(sell_signals) > 0:
    print("卖出信号：")
    print("-" * 100)
    for i in range(min(20, len(sell_signals))):
        idx = sell_signals.index[i]
        close = sell_signals['Close'].iloc[i]
        middle = sell_signals['Middle'].iloc[i]
        upper = sell_signals['Upper'].iloc[i]
        lower = sell_signals['Lower'].iloc[i]
        print(f"{idx.strftime('%Y-%m-%d')}: 收盘价 ${close:.2f} | 中线 ${middle:.2f} | 上轨 ${upper:.2f} | 下轨 ${lower:.2f}")
    print("-" * 100)
    print()

# 检查是否有下跌期的情况
down_phase = data_with_signals[data_with_signals['market_phase'] == '下跌期']
print(f"下跌期天数: {len(down_phase)}")
if len(down_phase) > 0:
    print("下跌期的情况（最近20个）：")
    print("-" * 100)
    for i in range(max(0, len(down_phase) - 20), len(down_phase)):
        idx = down_phase.index[i]
        close = down_phase['Close'].iloc[i]
        middle = down_phase['Middle'].iloc[i]
        upper = down_phase['Upper'].iloc[i]
        lower = down_phase['Lower'].iloc[i]
        print(f"{idx.strftime('%Y-%m-%d')}: 收盘价 ${close:.2f} | 中线 ${middle:.2f} | 上轨 ${upper:.2f} | 下轨 ${lower:.2f}")
    print("-" * 100)
