# 期货分钟级数据回测开发方案

基于 `chan_theory_realtime.py` 的缠论实时策略，针对期货分钟级数据设计回测框架。

---

## 1. 整体架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  期货数据适配层  │───▶│  滑动窗口回测引擎  │───▶│  结果分析与可视化 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  ChanTheory      │
                    │  Realtime        │
                    └──────────────────┘
```

---

## 2. 模块设计

### 2.1 数据适配层 (DataAdapter)

#### 职责
- 加载各类期货分钟数据源 (CSV/数据库/API)
- 处理主力合约切换
- 过滤非交易时间
- 统一数据格式

#### 输入数据格式
```python
# 标准分钟数据 DataFrame
{
    'DateTime': datetime64[ns],  # 时间戳，精确到分钟
    'Open': float64,             # 开盘价
    'High': float64,             # 最高价  
    'Low': float64,              # 最低价
    'Close': float64,            # 收盘价
    'Volume': int64,             # 成交量
    'Instrument': str,           # 合约代码 (如: RB2505)
    'IsMain': bool               # 是否主力合约标记
}
```

#### 关键处理逻辑

| 问题 | 解决方案 |
|------|----------|
| 日盘/夜盘分割 | 按交易所交易时间过滤，夜盘数据归属下一交易日 |
| 主力合约切换 | 提前5天检测，切换时平旧仓开新仓 |
| 数据跳空 | 换月时记录价差，回测时统一为连续合约价格 |
| 缺失数据 | 用前值填充或标记为无效时间 |

---

### 2.2 滑动窗口回测引擎 (RollingBacktestEngine)

#### 核心思想
模拟真实交易环境，每个时间点只能访问历史数据，无未来函数。

#### 类结构
```python
class RollingBacktestEngine:
    def __init__(
        self,
        chan_analyzer: ChanTheoryRealtime,
        window_size: int = 300,      # 历史窗口大小 (5小时)
        initial_capital: float = 1_000_000,
        margin_rate: float = 0.12,   # 保证金比例
        commission_rate: float = 0.0001,
        slippage: int = 1            # 滑点 (跳)
    ):
        pass
```

#### 执行流程

```
初始化引擎
    │
    ▼
加载历史数据 ────────▶ 按合约/日期分组
    │
    ▼
FOR 每个交易日:
    │
    ├── 开盘前初始化
    │
    ├── FOR 每分钟 bar:
    │   │
    │   ├── Step 1: 更新滑动窗口
    │   │           window = data[i-window_size : i]
    │   │
    │   ├── Step 2: 缠论分析
    │   │           signals = chan.analyze(window)
    │   │
    │   ├── Step 3: 检查止损止盈
    │   │           if hit_stop_loss: close_position()
    │   │
    │   ├── Step 4: 生成交易指令
    │   │           orders = strategy.on_bar(signals)
    │   │
    │   ├── Step 5: 模拟成交
    │   │           fill_orders(orders, current_bar)
    │   │
    │   └── Step 6: 记录状态
    │               equity_curve.append(current_equity)
    │
    └── 收盘结算 (盯市盈亏)
    │
    ▼
生成回测报告
```

---

### 2.3 缠论分析模块集成

#### 与 ChanTheoryRealtime 对接

```python
class ChanFuturesStrategy:
    """期货缠论策略封装"""
    
    def __init__(self):
        self.chan = ChanTheoryRealtime(k_type='minute')
        self.last_fenxing = None  # 缓存上次分型
    
    def on_bar(self, window_df: pd.DataFrame) -> dict:
        """
        每分钟调用一次
        
        Returns:
            {
                'buy_signal': bool,
                'sell_signal': bool, 
                'signal_type': int,  # 1:一类, 2:二类
                'strength': float    # 信号强度
            }
        """
        # 全量分析 (后续可优化为增量)
        result = self.chan.analyze(window_df)
        
        # 提取当前分钟信号
        current = result.iloc[-1]
        
        return {
            'buy_signal': current['buy_point'] > 0,
            'sell_signal': current['sell_point'] > 0,
            'signal_type': max(current['buy_point'], current['sell_point']),
            'has_zhongshu': pd.notna(current['zhongshu_high'])
        }
```

#### 增量计算优化

为提高性能，可修改 `ChanTheoryRealtime` 支持增量更新：

```python
class ChanTheoryRealtimeIncremental(ChanTheoryRealtime):
    """支持增量计算的缠论分析器"""
    
    def update(self, new_bar: pd.Series) -> dict:
        """
        只处理最新一根K线，而非全量重算
        """
        # 检查是否形成新分型
        if self._check_new_fenxing(new_bar):
            self._update_bi_list()
            self._update_xianduan_list()
            self._update_zhongshu_list()
        
        return self._get_current_signals()
```

---

### 2.4 期货账户与风控模块

#### 账户结构

```python
@dataclass
class FuturesAccount:
    """期货账户状态"""
    
    # 资金
    available_cash: float       # 可用资金
    frozen_margin: float        # 冻结保证金
    realized_pnl: float         # 已实现盈亏
    unrealized_pnl: float       # 浮动盈亏
    
    # 持仓
    positions: Dict[str, Position]  # 合约代码 -> 持仓
    
    @property
    def total_equity(self) -> float:
        return self.available_cash + self.frozen_margin + self.unrealized_pnl

@dataclass  
class Position:
    """单个合约持仓"""
    instrument: str
    direction: int              # 1:多, -1:空
    quantity: int               # 手数
    avg_price: float            # 开仓均价
    margin_occupied: float      # 占用保证金
    open_time: datetime         # 开仓时间
```

#### 保证金计算

```python
def calculate_margin(
    contract_code: str,
    price: float,
    quantity: int,
    margin_rate: float = 0.12
) -> float:
    """
    计算期货保证金
    
    公式: 保证金 = 价格 × 合约乘数 × 手数 × 保证金比例
    """
    contract_specs = {
        'RB': {'multiplier': 10},   # 螺纹钢 10吨/手
        'CU': {'multiplier': 5},    # 铜 5吨/手
        'AL': {'multiplier': 5},    # 铝 5吨/手
        # ... 更多合约
    }
    
    multiplier = contract_specs[get_category(contract_code)]['multiplier']
    return price * multiplier * quantity * margin_rate
```

#### 风控规则

| 规则类型 | 说明 | 触发动作 |
|----------|------|----------|
| 单笔止损 | 亏损超过开仓价2% | 市价平仓 |
| 总权益止损 | 当日回撤超5% | 清仓并暂停 |
| 保证金不足 | 可用资金<0 | 拒绝开仓 |
| 持仓时间 | 超过设定周期 | 强制平仓 |
| 涨跌停板 | 价格触及涨跌停 | 停止开仓 |

---

### 2.5 交易执行模块

#### 订单类型

```python
class Order:
    """订单对象"""
    
    order_id: str
    instrument: str
    direction: int          # 1:买(开多/平空), -1:卖(开空/平多)
    action: str             # 'OPEN'开仓, 'CLOSE'平仓
    quantity: int
    order_type: str         # 'MARKET'市价, 'LIMIT'限价
    limit_price: float = None
    
    @property
    def is_open(self) -> bool:
        """是否开仓"""
        return self.action == 'OPEN'
```

#### 撮合逻辑

```python
class SimpleMatcher:
    """简单撮合引擎"""
    
    def match(self, order: Order, bar: pd.Series) -> Trade:
        """
        基于当前bar进行撮合
        
        市价单: 以当前价 + 滑点成交
        限价单: 检查是否可成交
        """
        if order.order_type == 'MARKET':
            fill_price = self._apply_slippage(
                bar['Close'], 
                order.direction,
                slippage_ticks=1
            )
        else:
            fill_price = self._check_limit_fill(order, bar)
        
        return Trade(
            order_id=order.order_id,
            fill_price=fill_price,
            quantity=order.quantity,
            fill_time=bar.name  # 假设bar的index是时间
        )
```

---

## 3. 数据流设计

### 3.1 逐Bar处理流程

```python
def process_bar(self, bar: pd.Series, history: pd.DataFrame):
    """处理单根K线的主流程"""
    
    # 1. 时间检查
    if not self._is_trading_time(bar.name):
        return
    
    # 2. 更新行情
    self.price_board.update(bar)
    
    # 3. 缠论信号计算
    chan_result = self.chan_strategy.on_bar(history)
    
    # 4. 检查现有持仓
    for pos in self.account.positions.values():
        # 4.1 止损检查
        if self._check_stop_loss(pos, bar):
            self._place_order(pos.generate_close_order())
        
        # 4.2 止盈检查  
        if self._check_take_profit(pos, bar):
            self._place_order(pos.generate_close_order())
    
    # 5. 生成新订单 (基于缠论信号)
    orders = self._generate_orders(chan_result, bar)
    
    # 6. 风控检查
    approved_orders = self.risk_manager.check(orders, self.account)
    
    # 7. 执行订单
    for order in approved_orders:
        trade = self.matcher.match(order, bar)
        self._update_account(trade)
    
    # 8. 记录状态
    self._record_state()
```

### 3.2 信号到订单的映射

| 当前持仓 | 缠论信号 | 操作 | 订单类型 |
|----------|----------|------|----------|
| 空仓 | 一买 | 开多 | 市价买入 |
| 空仓 | 一卖 | 开空 | 市价卖出 |
| 有多仓 | 一卖/二卖 | 平多 | 市价卖出 |
| 有空仓 | 一买/二买 | 平空 | 市价买入 |
| 有多仓 | 二买 | 加仓 (可选) | 市价买入 |
| 有空仓 | 二卖 | 加空 (可选) | 市价卖出 |

---

## 4. 回测结果分析

### 4.1 绩效指标

#### 基础指标
```python
class BacktestReport:
    """回测报告"""
    
    # 收益指标
    total_return: float         # 总收益率
    annualized_return: float    # 年化收益率
    sharpe_ratio: float         # 夏普比率
    
    # 风险指标
    max_drawdown: float         # 最大回撤
    max_drawdown_duration: int  # 最大回撤天数
    volatility: float           # 波动率
    
    # 交易指标
    win_rate: float             # 胜率
    profit_factor: float        # 盈亏比
    avg_trade_return: float     # 平均交易收益
    num_trades: int             # 总交易次数
    
    # 期货特有
    margin_utilization: float   # 平均保证金占用率
    contract_rollovers: int     # 换月次数
    overnight_risk: float       # 隔夜风险暴露
```

### 4.2 可视化输出

- **资金曲线图**: 显示权益变化
- **回撤分析图**: 标注回撤区间
- **交易分布图**: 买卖点在K线上的标注
- **月度收益热力图**: 按合约/月份统计
- **缠论结构可视化**: 分型、笔、线段、中枢

---

## 5. 关键实现细节

### 5.1 主力合约连续化处理

```python
def create_continuous_contract(
    contract_data: Dict[str, pd.DataFrame],
    rollover_days: int = 5
) -> pd.DataFrame:
    """
    创建连续合约数据
    
    Args:
        contract_data: 各合约数据字典
        rollover_days: 提前换月天数
    
    Returns:
        连续的分钟数据，包含换月调整
    """
    # 1. 按到期日排序合约
    sorted_contracts = sorted(contract_data.items(), key=lambda x: x[1]['expire_date'])
    
    # 2. 拼接数据，换月时进行价差调整
    continuous_data = []
    adjustment = 0
    
    for i, (code, df) in enumerate(sorted_contracts):
        if i > 0:
            # 计算换月价差
            prev_close = continuous_data[-1]['Close'].iloc[-1]
            curr_open = df['Open'].iloc[0]
            adjustment += (prev_close - curr_open)
        
        # 调整价格
        adjusted_df = df.copy()
        adjusted_df[['Open', 'High', 'Low', 'Close']] += adjustment
        adjusted_df['original_close'] = df['Close']  # 保留原始价格用于结算
        
        continuous_data.append(adjusted_df)
    
    return pd.concat(continuous_data)
```

### 5.2 交易时间处理

```python
# 各交易所交易时间配置
TRADING_HOURS = {
    'SHFE': {
        'day': [(time(9, 0), time(10, 15)), 
                (time(10, 30), time(11, 30)),
                (time(13, 30), time(15, 0))],
        'night': [(time(21, 0), time(23, 0))]  # 部分品种到1:00/2:30
    },
    'DCE': {
        # ... 大商所时间
    },
    'CZCE': {
        # ... 郑商所时间
    }
}

def is_trading_time(dt: datetime, exchange: str) -> bool:
    """检查是否为有效交易时间"""
    t = dt.time()
    
    # 检查日盘
    for start, end in TRADING_HOURS[exchange]['day']:
        if start <= t <= end:
            return True
    
    # 检查夜盘
    for start, end in TRADING_HOURS[exchange]['night']:
        if start <= t or t <= end:  # 跨午夜情况
            return True
    
    return False
```

### 5.3 多合约并行回测

```python
from concurrent.futures import ProcessPoolExecutor

def backtest_single_contract(contract_code: str, data: pd.DataFrame) -> dict:
    """单个合约回测"""
    engine = RollingBacktestEngine(
        chan_analyzer=ChanTheoryRealtime(k_type='minute'),
        window_size=300
    )
    return engine.run(data)

def run_multi_contract_backtest(contract_dict: Dict[str, pd.DataFrame]) -> dict:
    """并行回测多个合约"""
    results = {}
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(backtest_single_contract, code, data): code
            for code, data in contract_dict.items()
        }
        
        for future in futures:
            code = futures[future]
            results[code] = future.result()
    
    return results
```

---

## 6. 目录结构建议

```
futures_chan_backtest/
├── core/
│   ├── __init__.py
│   ├── engine.py           # 回测引擎主类
│   ├── account.py          # 账户与持仓管理
│   ├── matcher.py          # 撮合引擎
│   └── risk_manager.py     # 风控模块
│
├── strategy/
│   ├── __init__.py
│   ├── chan_futures.py     # 缠论期货策略封装
│   └── signal_mapping.py   # 信号到订单的映射
│
├── data/
│   ├── __init__.py
│   ├── adapter.py          # 数据适配器
│   ├── contract.py         # 合约管理
│   └── loader.py           # 数据加载器
│
├── analysis/
│   ├── __init__.py
│   ├── report.py           # 报告生成
│   └── metrics.py          # 绩效指标计算
│
├── utils/
│   ├── __init__.py
│   ├── trading_hours.py    # 交易时间工具
│   └── continuous.py       # 连续合约处理
│
├── config/
│   └── settings.yaml       # 配置参数
│
├── main.py                 # 回测入口
└── requirements.txt
```

---

## 7. 注意事项

### 7.1 数据质量
- 确保分钟数据无未来数据混入
- 处理停牌、集合竞价等特殊情况
- 验证数据的连续性和完整性

### 7.2 过拟合防范
- 使用样本外数据验证
- 参数敏感性分析
- 多品种、多周期交叉验证

### 7.3 滑点与冲击成本
- 分钟级回测需考虑滑点
- 大单成交对价格的影响
- 流动性不足时的成交延迟

### 7.4 缠论参数调整
- 分钟级数据K线数量级更大，需调整分型识别参数
- 考虑不同品种的价格波动特性
- 实时版本的误判率需在实盘中验证

---

## 8. 后续优化方向

1. **增量计算优化**: 避免每分钟全量重算缠论结构
2. **事件驱动架构**: 支持更复杂的策略逻辑
3. **实盘对接**: 添加交易接口适配层
4. **机器学习增强**: 用ML过滤缠论信号的噪声
5. **多时间框架**: 结合日线确认分钟信号
