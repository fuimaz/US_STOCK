# 美股K线数据获取、绘制和回测系统 - 使用指南

## 快速开始

### 1. 安装依赖
```bash
python -m pip install -r requirements.txt
```

### 2. 运行完整示例
```bash
python main.py
```

---

## 使用示例

### 示例1：获取单只股票数据并绘制K线图

```python
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

# 初始化
fetcher = DataFetcher()
plotter = KLinePlotter(style='charles')

# 获取苹果公司1年数据
data = fetcher.fetch_stock_data('AAPL', period='1y')

# 绘制K线图（带5日、10日、20日均线）
plotter.plot_candlestick(data, title='AAPL K线图', mav=[5, 10, 20])
```

### 示例2：获取指定日期范围的数据

```python
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

fetcher = DataFetcher()
plotter = KLinePlotter()

# 获取2023年全年的数据
data = fetcher.fetch_stock_data(
    'AAPL',
    start_date='2023-01-01',
    end_date='2023-12-31'
)

plotter.plot_candlestick(data, title='AAPL 2023年K线图')
```

### 示例3：移动平均线策略回测

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy
from kline_plotter import KLinePlotter

# 获取数据
fetcher = DataFetcher()
data = fetcher.fetch_stock_data('AAPL', period='2y')

# 创建回测引擎（初始资金10万，手续费0.1%）
engine = BacktestEngine(initial_capital=100000, commission=0.001)

# 创建策略（5日均线和20日均线）
strategy = MovingAverageStrategy(short_period=5, long_period=20)

# 运行回测
results = engine.run_backtest(data, strategy)

# 打印结果
engine.print_results(results)

# 绘制带信号的K线图
plotter = KLinePlotter()
signals_df = strategy.generate_signals(data.copy())
buy_signals = signals_df['signal'] == 1
sell_signals = signals_df['signal'] == -1

plotter.plot_with_signals(
    data,
    buy_signals,
    sell_signals,
    title='AAPL 移动平均线策略',
    mav=[5, 20]
)

# 绘制绩效曲线
plotter.plot_performance(
    results['equity_curve']['equity'],
    benchmark=data['Close'],
    title='策略绩效 vs 基准'
)
```

### 示例4：RSI策略回测

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import RSIStrategy

fetcher = DataFetcher()
engine = BacktestEngine(initial_capital=100000)
data = fetcher.fetch_stock_data('AAPL', period='2y')

# RSI策略（14周期，超买70，超卖30）
strategy = RSIStrategy(period=14, overbought=70, oversold=30)
results = engine.run_backtest(data, strategy)
engine.print_results(results)
```

### 示例5：布林带策略回测

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import BollingerBandsStrategy

fetcher = DataFetcher()
engine = BacktestEngine(initial_capital=100000)
data = fetcher.fetch_stock_data('AAPL', period='2y')

# 布林带策略（20周期，2倍标准差）
strategy = BollingerBandsStrategy(period=20, std_dev=2)
results = engine.run_backtest(data, strategy)
engine.print_results(results)
```

### 示例6：MACD策略回测

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import MACDStrategy

fetcher = DataFetcher()
engine = BacktestEngine(initial_capital=100000)
data = fetcher.fetch_stock_data('AAPL', period='2y')

# MACD策略（12-26-9）
strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
results = engine.run_backtest(data, strategy)
engine.print_results(results)
```

### 示例7：多策略对比

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import (
    MovingAverageStrategy, 
    RSIStrategy, 
    BollingerBandsStrategy,
    MACDStrategy
)

fetcher = DataFetcher()
engine = BacktestEngine(initial_capital=100000)
data = fetcher.fetch_stock_data('AAPL', period='2y')

# 定义多个策略
strategies = [
    MovingAverageStrategy(short_period=5, long_period=20),
    MovingAverageStrategy(short_period=10, long_period=30),
    RSIStrategy(period=14, overbought=70, oversold=30),
    BollingerBandsStrategy(period=20, std_dev=2),
    MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
]

# 对比回测
print("策略对比结果:")
print("-" * 80)
print(f"{'策略名称':<30} {'收益率':<12} {'夏普比率':<10} {'最大回撤':<10}")
print("-" * 80)

for strategy in strategies:
    results = engine.run_backtest(data, strategy)
    print(f"{strategy.name:<30} "
          f"{results['total_return_pct']:>8.2f}% "
          f"{results['sharpe_ratio']:>8.2f} "
          f"{results['max_drawdown_pct']:>8.2f}%")
print("-" * 80)
```

### 示例8：多只股票对比

```python
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

fetcher = DataFetcher()
plotter = KLinePlotter()

# 获取多只股票数据
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
data_dict = fetcher.fetch_multiple_stocks(symbols, period='1y')

# 绘制对比图（归一化）
plotter.plot_comparison(
    data_dict,
    title='科技股对比 (归一化)',
    normalize=True
)
```

### 示例9：获取股票基本信息

```python
from data_fetcher import DataFetcher

fetcher = DataFetcher()

# 获取苹果公司信息
info = fetcher.get_stock_info('AAPL')

print(f"公司名称: {info['name']}")
print(f"行业: {info['industry']}")
print(f"板块: {info['sector']}")
print(f"市值: ${info['market_cap']:,.0f}")
print(f"当前价格: ${info['current_price']:.2f}")
```

### 示例10：保存图表到文件

```python
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

fetcher = DataFetcher()
plotter = KLinePlotter()

data = fetcher.fetch_stock_data('AAPL', period='1y')

# 保存K线图
plotter.plot_candlestick(
    data,
    title='AAPL K线图',
    save_path='aapl_kline.png'
)

# 保存绩效图
plotter.plot_performance(
    results['equity_curve']['equity'],
    title='策略绩效',
    save_path='strategy_performance.png'
)
```

### 示例11：自定义参数回测

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy

fetcher = DataFetcher()

# 不同的手续费设置
commissions = [0.001, 0.003, 0.005]
data = fetcher.fetch_stock_data('AAPL', period='2y')

print("不同手续费下的回测结果:")
print("-" * 60)
print(f"{'手续费率':<12} {'最终资金':<15} {'收益率':<12} {'夏普比率':<10}")
print("-" * 60)

for comm in commissions:
    engine = BacktestEngine(initial_capital=100000, commission=comm)
    strategy = MovingAverageStrategy(short_period=5, long_period=20)
    results = engine.run_backtest(data, strategy)
    
    print(f"{comm*100:>8.2f}% "
          f"${results['final_capital']:>12,.2f} "
          f"{results['total_return_pct']:>8.2f}% "
          f"{results['sharpe_ratio']:>8.2f}")
print("-" * 60)
```

### 示例12：不同时间周期数据

```python
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

fetcher = DataFetcher()
plotter = KLinePlotter()

# 获取不同时间周期的数据
periods = {
    '1个月': '1mo',
    '3个月': '3mo',
    '6个月': '6mo',
    '1年': '1y',
    '2年': '2y'
}

for name, period in periods.items():
    data = fetcher.fetch_stock_data('AAPL', period=period)
    print(f"{name}: {len(data)} 条数据")
    
    # 绘制并保存
    plotter.plot_candlestick(
        data,
        title=f'AAPL {name} K线图',
        save_path=f'aapl_{period}.png'
    )
```

### 示例13：查看交易记录

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy

fetcher = DataFetcher()
engine = BacktestEngine(initial_capital=100000)
data = fetcher.fetch_stock_data('AAPL', period='1y')

strategy = MovingAverageStrategy(short_period=5, long_period=20)
results = engine.run_backtest(data, strategy)

# 查看所有交易记录
print("\n交易记录:")
print("-" * 80)
trades_df = results['trades']
print(trades_df.to_string())
print("-" * 80)

# 统计交易次数
buy_trades = len(trades_df[trades_df['type'] == 'buy'])
sell_trades = len(trades_df[trades_df['type'] == 'sell'])
print(f"\n买入次数: {buy_trades}")
print(f"卖出次数: {sell_trades}")
```

### 示例14：实时数据获取

```python
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

fetcher = DataFetcher()
plotter = KLinePlotter()

# 获取最近5天的数据（包括今天）
data = fetcher.fetch_stock_data('AAPL', period='5d')

print(f"最新收盘价: ${data['Close'].iloc[-1]:.2f}")
print(f"最新成交量: {data['Volume'].iloc[-1]:,.0f}")
print(f"当日涨跌: {((data['Close'].iloc[-1] / data['Close'].iloc[-2] - 1) * 100):.2f}%")

plotter.plot_candlestick(data, title='AAPL 最近5天')
```

### 示例15：创建自定义策略

```python
from backtest_engine import BaseStrategy
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
import pandas as pd

class MyCustomStrategy(BaseStrategy):
    """自定义策略示例：价格突破策略"""
    
    def __init__(self, period: int = 20):
        super().__init__(name="价格突破策略")
        self.period = period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        
        # 计算20日最高价和最低价
        df['High_20'] = df['High'].rolling(window=self.period).max()
        df['Low_20'] = df['Low'].rolling(window=self.period).min()
        
        # 生成信号
        df['signal'] = 0
        
        # 价格突破20日最高价买入
        df.loc[df['Close'] > df['High_20'].shift(1), 'signal'] = 1
        
        # 价格跌破20日最低价卖出
        df.loc[df['Close'] < df['Low_20'].shift(1), 'signal'] = -1
        
        # 只保留信号变化
        df['signal'] = df['signal'].diff()
        df.loc[df['signal'] == 2, 'signal'] = 1
        df.loc[df['signal'] == -2, 'signal'] = -1
        
        return df

# 使用自定义策略
fetcher = DataFetcher()
engine = BacktestEngine(initial_capital=100000)
data = fetcher.fetch_stock_data('AAPL', period='2y')

strategy = MyCustomStrategy(period=20)
results = engine.run_backtest(data, strategy)
engine.print_results(results)
```

---

## 常用参数说明

### 时间周期 (period)
- `1d`: 1天
- `5d`: 5天
- `1mo`: 1个月
- `3mo`: 3个月
- `6mo`: 6个月
- `1y`: 1年
- `2y`: 2年
- `5y`: 5年
- `10y`: 10年
- `ytd`: 年初至今
- `max`: 最大可用数据

### 数据间隔 (interval)
- `1m`: 1分钟
- `5m`: 5分钟
- `15m`: 15分钟
- `30m`: 30分钟
- `1h`: 1小时
- `1d`: 1天
- `1wk`: 1周
- `1mo`: 1月

### 图表样式 (style)
- `charles`: 经典样式（默认）
- `default`: 默认样式
- `yahoo`: Yahoo风格
- `nightclouds`: 深色主题
- `sas`: SAS风格
- `starsandstripes`: 星条旗风格

---

## 常见股票代码

### 科技股
- AAPL: 苹果
- MSFT: 微软
- GOOGL: 谷歌
- AMZN: 亚马逊
- META: Meta(Facebook)
- TSLA: 特斯拉
- NVDA: 英伟达

### 金融股
- JPM: 摩根大通
- BAC: 美国银行
- V: Visa
- MA: 万事达卡

### 指数ETF
- SPY: 标普500 ETF
- QQQ: 纳斯达克100 ETF
- DIA: 道琼斯ETF
- IWM: 罗素2000 ETF

---

## 注意事项

1. **数据限制**: yfinance免费版有请求频率限制
2. **回测偏差**: 回测结果仅供参考，实际交易会有滑点和其他成本
3. **策略风险**: 任何策略都有风险，请谨慎使用
4. **数据准确性**: 历史数据可能存在调整，建议多方验证
