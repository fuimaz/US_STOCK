# 缠论实时交易系统 - 项目文件索引

## 📁 文件结构总览

```
us_stock/
│
├── 📊 核心指标模块（复用）
│   ├── chan_theory.py              # 缠论主模块（标准版）
│   ├── chan_theory_realtime.py     # 缠论实时近似版（⭐主要使用）
│   └── chan_theory_delayed.py      # 缠论延迟确认版
│
├── 📈 回测模块
│   ├── backtest_all_cached_stocks_10y.py  # 批量10年回测（112只股票）⭐
│   ├── backtest_hot_stocks_1y.py          # 热门股票近1年回测
│   ├── backtest_hot_stocks_1y_type1_only.py  # 仅第一类买卖点回测
│   └── backtest_chan_realtime.py          # 实时方案回测
│
├── 🔍 实时扫描模块（新增）⭐
│   ├── scan_signals_realtime.py    # 【主脚本】实时买卖点扫描
│   ├── scan_signals_demo.py        # 演示脚本（带示例输出）
│   ├── analyze_scan_history.py     # 历史扫描结果分析
│   ├── run_scan.bat                # Windows一键运行批处理
│   └── REALTIME_SCAN_USAGE.md      # 实时扫描使用说明
│
├── 📉 数据获取模块
│   ├── data_fetcher.py             # 数据获取器
│   └── data_cache/                 # 数据缓存目录
│       └── *_20y_1d_forward.csv    # 股票历史数据缓存
│
├── 📊 结果输出目录
│   └── results/
│       ├── chan_10y_backtest/      # 10年回测结果
│       │   ├── detailed_results.csv
│       │   ├── summary_distributions.png
│       │   ├── top20_returns.png
│       │   └── scatter_comparison.png
│       ├── hot_stocks_1y/          # 热门股票回测结果
│       └── realtime_scan/          # 实时扫描结果
│           ├── buy_signals_*.csv
│           ├── sell_signals_*.csv
│           └── summary_*.json
│
├── 📚 文档
│   ├── README.md                   # 项目主文档
│   ├── PROJECT_INDEX.md            # 本文件（项目索引）
│   ├── WEEKLY_BOLL_STRATEGY.md     # 布林带策略文档
│   └── INTERACTIVE_FEATURES.md     # 交互功能文档
│
└── 🧪 测试/调试脚本
    ├── scan_demo.py                # 简单演示
    ├── test_chan_theory.py         # 缠论单元测试
    └── debug_*.py                  # 调试脚本

```

---

## 🎯 快速开始

### 1. 批量回测（10年数据）
```bash
python backtest_all_cached_stocks_10y.py
```
- 回测112只股票的近10年表现
- 输出：`results/chan_10y_backtest/`

### 2. 实时买卖点扫描
```bash
# 方式1: Python脚本
python scan_signals_realtime.py

# 方式2: Windows批处理（双击运行）
run_scan.bat
```
- 扫描67只A股龙头
- 检测近5个交易日的买卖点信号
- 输出：`results/realtime_scan/`

### 3. 分析扫描历史
```bash
python analyze_scan_history.py
```
- 统计哪些股票频繁出现信号
- 生成频率图表
- 输出：`results/realtime_scan/history_analysis_*.png`

---

## 📊 核心指标模块说明

### `chan_theory_realtime.py`
**功能**: 缠论指标实时近似版本

**核心方法**:
```python
chan = ChanTheoryRealtime(k_type='day')
result = chan.analyze(data)

# 获取买卖点
buy_points = chan.buy_points   # 买点列表
sell_points = chan.sell_points # 卖点列表
```

**特点**:
- 无延迟、无未来函数
- 当天收盘即可判断信号
- 被回测和实时扫描共同复用

---

## 🔍 实时扫描系统详解

### 主脚本: `scan_signals_realtime.py`

**工作流程**:
1. 加载股票池（默认67只A股龙头）
2. 对每只股票：
   - 获取历史数据（优先缓存）
   - 调用 `ChanTheoryRealtime.analyze()` 分析
   - 检测近5个交易日的买卖点
3. 汇总输出结果

**信号类型**:
| 类型 | 说明 | 操作建议 |
|------|------|---------|
| Type 1 Buy | 第一类买点（趋势反转） | 建仓/重仓 |
| Type 2 Buy | 第二类买点（回调确认） | 加仓/买入 |
| Type 1 Sell | 第一类卖点（趋势反转） | 清仓/减仓 |
| Type 2 Sell | 第二类卖点（反弹确认） | 减仓/观望 |

**输出文件**:
- `buy_signals_YYYYMMDD_HHMMSS.csv` - 买点详情
- `sell_signals_YYYYMMDD_HHMMSS.csv` - 卖点详情
- `summary_YYYYMMDD_HHMMSS.json` - 汇总数据

---

## ⚙️ 定时任务设置

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务：
   - **名称**: ChanTheorySignalScan
   - **触发器**: 每天 14:00
   - **操作**: 启动程序
   - **程序**: `python`
   - **参数**: `C:\Users\jiman\Documents\trae_projects\us_stock\scan_signals_realtime.py`
   - **起始位置**: `C:\Users\jiman\Documents\trae_projects\us_stock`

### Linux/Mac Crontab
```bash
# 每天下午2点运行
0 14 * * * cd /path/to/us_stock && python scan_signals_realtime.py
```

---

## 📈 回测 vs 实时扫描

| 功能 | 回测脚本 | 实时扫描 |
|------|---------|---------|
| 数据范围 | 10年历史 | 近5个交易日 |
| 股票数量 | 112只 | 67只（可配置） |
| 输出 | 收益统计、图表 | 当前信号列表 |
| 用途 | 验证策略有效性 | 实盘交易参考 |
| 运行频率 | 一次性/定期 | 每日定时 |

**共同点**: 都复用 `chan_theory_realtime.py`，确保指标逻辑一致

---

## 🔧 自定义配置

### 修改股票池

编辑 `scan_signals_realtime.py`:
```python
STOCK_UNIVERSE = {
    '000001.SZ': '平安银行',
    '600519.SS': '贵州茅台',
    # 添加/删除股票...
}
```

### 调整信号检测周期

修改 `analyze_signals` 方法:
```python
# 检测近10个交易日的信号（默认5天）
for bp in chan.buy_points:
    if bp['index'] >= data.index[-10]:  # 改为10天
        ...
```

### 添加推送通知

在 `save_results` 方法中添加:
```python
def save_results(self, signals: Dict):
    # ... 原有代码 ...
    
    # 发送邮件/微信通知
    if signals['buy_signals'] or signals['sell_signals']:
        self.send_wechat_notification(
            f"发现 {len(signals['buy_signals'])} 个买点, "
            f"{len(signals['sell_signals'])} 个卖点"
        )
```

---

## 📊 结果解读

### 回测结果

**10年回测关键指标**:
- **平均策略收益**: +1,378%
- **平均买入持有**: +247%
- **平均超额收益**: +1,131%
- **胜率**: 51.5%
- **正超额比例**: 92.9%

**说明**: 缠论实时方案在10年回测中大幅跑赢买入持有

### 实时扫描结果

**示例输出**:
```
[ BUY SIGNALS ] - Total: 3
Symbol       Name       Date         Type         SigPrice   CurPrice   Change
--------------------------------------------------------------------------------
000333.SZ    美的集团   2026-02-20   Type 1 Buy      77.85      79.20   +1.73%
002594.SZ    比亚迪     2026-02-21   Type 2 Buy     285.50     288.00   +0.88%
601012.SS    隆基绿能   2026-02-21   Type 2 Buy      25.60      25.82   +0.85%

[ SELL SIGNALS ] - Total: 2
Symbol       Name       Date         Type         SigPrice   CurPrice   Change
--------------------------------------------------------------------------------
002594.SZ    比亚迪     2026-02-20   Type 1 Sell    310.00     294.64   -4.95%
601888.SS    中国中免   2026-02-19   Type 1 Sell    185.00     182.50   -1.35%
```

**解读**:
- **SigPrice**: 信号触发时的价格
- **CurPrice**: 当前价格
- **Change**: 当前价格相对信号价格的变化

---

## 📝 更新日志

- **2026-02-22**: 
  - ✅ 完成10年批量回测（112只股票）
  - ✅ 创建实时买卖点扫描系统
  - ✅ 添加历史扫描结果分析工具
  - ✅ 完善使用文档

---

## 🎓 使用建议

1. **回测验证**: 先运行 `backtest_all_cached_stocks_10y.py` 验证策略有效性
2. **模拟运行**: 使用 `scan_signals_demo.py` 熟悉输出格式
3. **定时扫描**: 设置每天14:00自动运行 `scan_signals_realtime.py`
4. **定期分析**: 每周运行 `analyze_scan_history.py` 分析信号频率
5. **实盘谨慎**: 信号仅供参考，建议结合基本面和其他指标综合判断

---

## 📞 常见问题

**Q: 为什么实时扫描没有输出信号？**  
A: 可能原因：
- 当前不是交易日
- 缓存数据过期（数据截止到2月12日）
- 最近5个交易日确实没有信号

**Q: 如何更新股票数据？**  
A: 数据会自动从缓存获取，如需最新数据，删除 `data_cache/` 中的缓存文件后重新运行

**Q: 可以同时监控美股吗？**  
A: 可以，在 `STOCK_UNIVERSE` 中添加美股代码（如 'AAPL', 'TSLA'），确保有对应缓存数据

---

**项目路径**: `C:\Users\jiman\Documents\trae_projects\us_stock`  
**创建时间**: 2026-02-22  
**版本**: v1.0
