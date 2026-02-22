# 美股K线数据获取、绘制和回测系统

一个功能完整的美股量化交易回测系统，支持数据获取、K线图绘制和策略回测。

## 功能特性

- 📊 **数据获取**: 使用yfinance获取美股实时和历史数据
- 💾 **智能缓存**: 本地缓存数据，优先加载缓存，提升速度
- 📈 **K线绘制**: 使用mplfinance绘制专业K线图
- 🖱️ **交互功能**: 支持鼠标悬停查看价格、拖拽移动K线、滚轮缩放
- 🌐 **中文支持**: 自动配置中文字体，解决乱码问题
- 🧪 **策略回测**: 完整的回测引擎，支持多种策略
- 📉 **绩效分析**: 计算收益率、夏普比率、最大回撤等指标
- 🎯 **多种策略**: 内置移动平均线、RSI、布林带、MACD等策略

## 快速开始

### 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2. 运行示例

```bash
# 示例1：获取单只股票数据并绘制K线图
python example_1_basic_mock.py

# 示例2：移动平均线策略回测
python example_2_ma_strategy_mock.py

# 示例3：多策略对比回测
python example_3_compare_strategies_mock.py

# 示例4：多只股票对比
python example_4_compare_stocks_mock.py

# 示例5：带有BOLL、成交量、RSI指标的K线图
python example_indicators.py

# 示例6：带有BOLL、成交量、RSI指标和交易信号的K线图
python example_indicators_with_signals.py

# 示例7：K线图切换日线、周线、月线
python example_timeframe.py
```

### 3. 使用命令行工具

```bash
# 绘制日线图（使用缓存）
python kline_tool.py -t 1d

# 绘制周线图（使用缓存）
python kline_tool.py -t 1w

# 绘制月线图（使用缓存）
python kline_tool.py -t 1m

# 指定股票代码和数据周期
python kline_tool.py -s MSFT -p 2y

# 强制从网络获取数据（不使用缓存）
python kline_tool.py --no-cache

# 不显示布林带
python kline_tool.py --no-boll

# 不显示RSI
python kline_tool.py --no-rsi

# 不显示成交量
python kline_tool.py --no-volume

# 组合使用
python kline_tool.py -t 1w -s GOOGL --no-volume
```

### 4. 使用交互式K线图查看器

```bash
# 交互式查看器（支持鼠标拖拽、滚轮缩放、悬停查看）
python interactive_kline.py -s AAPL

# 指定股票代码
python interactive_kline.py -s MSFT

# 指定数据周期
python interactive_kline.py -s GOOGL -p 2y

# 使用周线
python interactive_kline.py -s AAPL -t 1w

# 使用月线
python interactive_kline.py -s AAPL -t 1m

# 不使用缓存
python interactive_kline.py -s NVDA --no-cache

# 组合使用
python interactive_kline.py -s MSFT -t 1w -p 2y
```

**交互式查看器功能**:
- 🖱️ **鼠标拖拽**: 左右拖动查看不同时间段的K线
- 🔄 **滚轮缩放**: 向上/向下滚动调整显示的K线数量
- 📊 **悬停/点击查看**: 鼠标悬停或点击K线显示详细信息（日期、开盘、最高、最低、收盘、涨跌、成交量、BOLL、RSI）
- 📈 **实时更新**: 拖拽和缩放时实时更新图表
- 📅 **多周期支持**: 支持日线、周线、月线切换

**数据缓存说明**: 
- 默认使用**本地缓存**，缓存有效期为1天
- 缓存文件保存在 `data_cache` 目录
- 使用 `--no-cache` 参数可强制从网络获取最新数据
- 优先加载缓存，大幅提升加载速度

### 3. 运行真实数据示例（需要网络）

```bash
# 注意：yfinance可能有请求频率限制
# 示例1：获取单只股票数据并绘制K线图
python example_1_basic.py

# 示例2：移动平均线策略回测
python example_2_ma_strategy.py

# 示例3：多策略对比回测
python example_3_compare_strategies.py

# 示例4：多只股票对比
python example_4_compare_stocks.py

# 示例5：获取股票基本信息
python example_5_stock_info.py

# 示例6：不同手续费下的策略表现
python example_6_commission_test.py
```

## 运行结果展示

### 示例1：K线图绘制
程序会生成252条模拟数据，并绘制包含5日、10日、20日均线的K线图。

### 示例2：策略回测
```
==================================================
回测结果 - 策略
==================================================
初始资金: $100,000.00
最终资金: $97,973.65
总收益率: -1.92%
年化收益率: -0.97%
夏普比率: 0.07
最大回撤: 23.78%
胜率: 33.33%
波动率: 22.70%
总交易次数: 31
==================================================
```

### 示例3：多策略对比
```
--------------------------------------------------------------------------------      
策略名称                           总收益率         年化收益率        夏普比率        最大回撤
--------------------------------------------------------------------------------
MA5-20                              -1.92%      -0.97%       0.07     23.78%
RSI14                              -15.83%      -8.32%      -0.33     22.43%
BB20                               -22.51%     -12.06%      -0.42     30.47%
MACD12-26                           -8.35%      -4.30%      -0.07     28.17%
--------------------------------------------------------------------------------      

🏆 最佳策略: MA5-20
   总收益率: -1.92%
   夏普比率: 0.07
   最大回撤: 23.78%
   交易次数: 31
```

### 示例4：多股票对比
程序会生成5只科技股的模拟数据，并绘制归一化对比图。

## 代码示例

### 获取数据并绘制K线图

```python
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter

fetcher = DataFetcher()
plotter = KLinePlotter()

data = fetcher.fetch_stock_data('AAPL', period='1y')
plotter.plot_candlestick(data, title='AAPL K线图', mav=[5, 10, 20])
```

### 策略回测

```python
from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy

fetcher = DataFetcher()
engine = BacktestEngine(initial_capital=100000)
data = fetcher.fetch_stock_data('AAPL', period='2y')

strategy = MovingAverageStrategy(short_period=5, long_period=20)
results = engine.run_backtest(data, strategy)
engine.print_results(results)
```

## 内置策略

| 策略 | 说明 |
|------|------|
| MovingAverageStrategy | 移动平均线策略（金叉买入，死叉卖出） |
| RSIStrategy | RSI策略（超卖买入，超买卖出） |
| BollingerBandsStrategy | 布林带策略（触及下轨买入，触及上轨卖出） |
| MACDStrategy | MACD策略（MACD金叉买入，死叉卖出） |

## 项目结构

```
us_stock/
├── requirements.txt                      # 项目依赖
├── data_fetcher.py                      # 数据获取模块
├── kline_plotter.py                     # K线图绘制模块
├── backtest_engine.py                   # 回测引擎
├── strategies.py                        # 交易策略库
├── main.py                              # 主程序入口
├── example_1_basic.py                   # 示例1：基础K线图（真实数据）
├── example_1_basic_mock.py              # 示例1：基础K线图（模拟数据）
├── example_2_ma_strategy.py             # 示例2：移动平均线策略（真实数据）
├── example_2_ma_strategy_mock.py        # 示例2：移动平均线策略（模拟数据）
├── example_3_compare_strategies.py      # 示例3：多策略对比（真实数据）
├── example_3_compare_strategies_mock.py # 示例3：多策略对比（模拟数据）
├── example_4_compare_stocks.py          # 示例4：多股票对比（真实数据）
├── example_4_compare_stocks_mock.py     # 示例4：多股票对比（模拟数据）
├── example_5_stock_info.py               # 示例5：股票信息
├── example_6_commission_test.py         # 示例6：手续费测试
├── example_indicators.py                # 示例7：BOLL+成交量+RSI指标
├── example_indicators_with_signals.py    # 示例8：BOLL+成交量+RSI+交易信号
├── example_timeframe.py                # 示例9：日线/周线/月线切换
├── kline_tool.py                       # 命令行K线工具
├── README.md                            # 项目说明文档
└── USAGE_GUIDE.md                       # 详细使用指南
```

## 常用参数

### 时间周期 (period)
- `1mo`: 1个月
- `3mo`: 3个月
- `6mo`: 6个月
- `1y`: 1年
- `2y`: 2年
- `5y`: 5年

### 数据间隔 (interval)
- `1d`: 1天
- `1wk`: 1周
- `1mo`: 1月

### 图表样式 (style)
- `charles`: 经典样式（默认）
- `yahoo`: Yahoo风格
- `nightclouds`: 深色主题

## 常见股票代码

### 科技股
- AAPL: 苹果
- MSFT: 微软
- GOOGL: 谷歌
- AMZN: 亚马逊
- TSLA: 特斯拉
- NVDA: 英伟达

### 指数ETF
- SPY: 标普500 ETF
- QQQ: 纳斯达克100 ETF
- DIA: 道琼斯ETF

## 注意事项

1. **API限制**: yfinance免费版有请求频率限制，建议使用模拟数据示例进行测试
2. **回测偏差**: 回测结果仅供参考，实际交易会有滑点和其他成本
3. **策略风险**: 任何策略都有风险，请谨慎使用
4. **数据准确性**: 历史数据可能存在调整，建议多方验证

## 详细文档

查看 `USAGE_GUIDE.md` 获取更多使用示例和详细说明。

查看 `DATA_SOURCE.md` 了解模拟数据和真实数据的区别及使用方法。
