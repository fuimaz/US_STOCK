# 缠论实时买卖点扫描 - 使用说明

## 概述

`scan_signals_realtime.py` 是一个实时扫描工具，每天下午2点左右运行，检测股票池中哪些股票命中了缠论买卖点信号。

**核心特点：**
- 复用 `chan_theory_realtime.py` 指标代码，与回测逻辑完全一致
- **同时检测买点和卖点信号**
- 优先使用本地缓存数据，减少API调用
- 支持自动获取最新数据（交易时间内）
- 输出格式清晰，便于快速决策

## 文件结构

```
us_stock/
├── chan_theory_realtime.py      # 缠论指标核心代码（复用）
├── scan_signals_realtime.py     # 实时扫描脚本（新建）⭐主脚本
├── scan_signals_demo.py         # 演示脚本（带示例输出）
├── data_fetcher.py              # 数据获取模块
├── data_cache/                  # 本地数据缓存目录
└── results/realtime_scan/       # 扫描结果输出目录
    ├── buy_signals_*.csv        # 买点信号
    ├── sell_signals_*.csv       # 卖点信号
    └── summary_*.json           # 汇总结果
```

## 使用方法

### 1. 手动运行

```bash
python scan_signals_realtime.py
```

### 2. 定时自动运行（Windows任务计划程序）

**设置步骤：**

1. 打开"任务计划程序"
2. 创建基本任务：
   - 名称：ChanTheorySignalScan
   - 触发器：每天 14:00
   - 操作：启动程序
   - 程序：python
   - 参数：`C:\Users\jiman\Documents\trae_projects\us_stock\scan_signals_realtime.py`
   - 起始位置：`C:\Users\jiman\Documents\trae_projects\us_stock`

### 3. 演示模式（查看输出格式）

```bash
python scan_signals_demo.py
```

### 4. Python脚本中调用

```python
from scan_signals_realtime import SignalScanner

# 创建扫描器
scanner = SignalScanner()

# 执行扫描
signals = scanner.scan_all_stocks()

# 处理买点
for buy in signals['buy_signals']:
    print(f"BUY: {buy['symbol']} @ {buy['signal_price']}")

# 处理卖点
for sell in signals['sell_signals']:
    print(f"SELL: {sell['symbol']} @ {sell['signal_price']}")
```

## 股票池配置

在 `scan_signals_realtime.py` 中修改 `STOCK_UNIVERSE` 字典：

```python
STOCK_UNIVERSE = {
    '000001.SZ': '平安银行',
    '000002.SZ': '万科A',
    '600519.SS': '贵州茅台',
    # 添加更多股票...
}
```

## 输出示例

### 控制台输出

```
====================================================================================================
Chan Theory Real-time Signal Scan - 2026-02-22 14:00:00
====================================================================================================
Stock universe: 67 stocks

[1/67] Scanning: 平安银行 (000001.SZ)
  [000001.SZ] Using 20y cached data
  No recent signals

[2/67] Scanning: 美的集团 (000333.SZ)
  [000333.SZ] Using 20y cached data
  >>> BUY SIGNAL: Type 1 Buy @ 77.85 (+1.73%)

[3/67] Scanning: 比亚迪 (002594.SZ)
  [002594.SZ] Using 20y cached data
  >>> SELL SIGNAL: Type 1 Sell @ 285.50 (+3.20%)

[4/67] Scanning: 隆基绿能 (601012.SS)
  [601012.SS] Using 20y cached data
  >>> BUY SIGNAL: Type 2 Buy @ 25.60 (+0.85%)
  >>> SELL SIGNAL: Type 1 Sell @ 28.90 (+5.60%)
...

====================================================================================================
Scan complete
  Buy signals: 2
  Sell signals: 2
  Errors: 0
====================================================================================================

====================================================================================================
SIGNAL SUMMARY
====================================================================================================

[ BUY SIGNALS ] - Total: 2
Symbol       Name       Date         Type           SigPrice   CurPrice   Change  
------------------------------------------------------------------------------------------
000333.SZ    美的集团   2026-02-20   Type 1 Buy        77.85      79.20   +1.73%
601012.SS    隆基绿能   2026-02-21   Type 2 Buy        25.60      25.82   +0.85%

[ SELL SIGNALS ] - Total: 2
Symbol       Name       Date         Type           SigPrice   CurPrice   Change  
------------------------------------------------------------------------------------------
002594.SZ    比亚迪     2026-02-20   Type 1 Sell      285.50     294.64   +3.20%
601012.SS    隆基绿能   2026-02-19   Type 1 Sell       28.90      30.52   +5.60%

====================================================================================================
```

### 保存的文件

扫描结果保存到 `results/realtime_scan/` 目录：

- **buy_signals_YYYYMMDD_HHMMSS.csv** - 买点信号（CSV格式）
- **buy_signals_YYYYMMDD_HHMMSS.json** - 买点信号（JSON格式）
- **sell_signals_YYYYMMDD_HHMMSS.csv** - 卖点信号（CSV格式）
- **sell_signals_YYYYMMDD_HHMMSS.json** - 卖点信号（JSON格式）
- **summary_YYYYMMDD_HHMMSS.json** - 汇总结果（包含买卖信号）

## 信号说明

### 买点信号

| 类型 | 名称 | 特征 | 操作建议 |
|------|------|------|---------|
| Type 1 Buy | 第一类买点 | 下跌线段结束，向上突破中枢 | 建仓或重仓买入 |
| Type 2 Buy | 第二类买点 | 第一类买点后，回调不创新低 | 加仓或买入 |

### 卖点信号

| 类型 | 名称 | 特征 | 操作建议 |
|------|------|------|---------|
| Type 1 Sell | 第一类卖点 | 上涨线段结束，向下跌破中枢 | 清仓或减仓 |
| Type 2 Sell | 第二类卖点 | 第一类卖点后，反弹不创新高 | 减仓或观望 |

### 特殊情况

**同时出现买卖信号（如隆基绿能例子）**
- 可能处于震荡区间
- 建议高抛低吸或观望
- 等待趋势明确

## 与回测代码的关系

```
回测脚本 (backtest_*.py)
    |
    |---> 使用 ChanTheoryRealtime.analyze() 分析历史数据
    |---> 批量计算回测结果
    
实时扫描 (scan_signals_realtime.py)
    |
    |---> 复用 ChanTheoryRealtime.analyze() 分析当前数据
    |---> 实时检测买卖点信号
```

**优势：**
- 指标逻辑完全一致，回测结果可信度高
- 修改指标参数只需修改一处（chan_theory_realtime.py）
- 避免回测和实盘使用不同逻辑导致的差异

## 注意事项

1. **数据更新**
   - 脚本优先使用本地缓存
   - 交易时间内会自动尝试获取最新数据
   - 建议每天开盘前运行一次，确保数据最新

2. **信号时效性**
   - 脚本检测近5个交易日的信号
   - 过早的信号可能已失效

3. **风险控制**
   - 买卖点信号仅供参考，不构成投资建议
   - 建议结合基本面和其他技术指标综合判断
   - 严格设置止损位

4. **同时出现买卖信号**
   - 可能表示股票处于震荡状态
   - 需要更谨慎判断

## 自定义扩展

### 添加推送通知

在 `save_results` 方法中添加推送逻辑：

```python
def save_results(self, signals: Dict):
    # ... 原有保存逻辑 ...
    
    # 发送通知
    if signals['buy_signals'] or signals['sell_signals']:
        message = f"发现 {len(signals['buy_signals'])} 个买点，{len(signals['sell_signals'])} 个卖点"
        self.send_notification(message)

def send_notification(self, message: str):
    # 邮件推送
    # 微信推送
    # 钉钉推送
    pass
```

### 调整信号检测周期

修改 `analyze_signals` 方法中的时间窗口：

```python
# 检测近10个交易日的信号（默认5天）
for bp in chan.buy_points:
    if bp['index'] >= data.index[-10]:  # 改为10天
        ...
```

## 故障排除

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 无信号输出 | 当前无信号或数据过期 | 检查数据日期，确认是否为交易日 |
| 数据获取失败 | 网络问题或API限制 | 检查网络连接，稍后重试 |
| 编码错误 | 中文字符问题 | 已修复，如仍有问题检查系统编码设置 |
| 运行速度慢 | 股票数量多 | 减少股票池数量，或使用多线程 |

## 更新日志

- **2026-02-22**: 初始版本，支持67只A股实时扫描
- **2026-02-22**: ✅ **新增卖点检测**，同时输出买卖信号
