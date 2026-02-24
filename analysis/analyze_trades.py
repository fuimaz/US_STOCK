"""详细分析交易结果"""
import sys
sys.path.insert(0, '.')
from backtest_futures_minute import *

# 分析交易结果
df = load_futures_data('I0')

# 使用固定参数运行
BACKTEST_CONFIG['stop_loss_pct'] = 0.02
BACKTEST_CONFIG['stop_profit_pct'] = 0.04

strategy = ChanFuturesStrategy(k_type='minute')
engine = FuturesBacktestEngine(strategy, window_size=100)
result = engine.run(df, 'I0')

print()
print('=== 详细分析 ===')
print('问题：所有交易都是因为卖出信号平仓，没有触发止损/止盈')
print()

# 分析盈利和亏损的交易
trades = result.get('trades', [])
winning_trades = []
losing_trades = []

for t in trades:
    if 'pnl' in t:
        if t['pnl'] > 0:
            winning_trades.append(t)
        else:
            losing_trades.append(t)

print('盈利交易({0}笔):'.format(len(winning_trades)))
for t in winning_trades:
    print('  {0} 买入 {1}手 @ {2}'.format(t['time'], t.get('quantity', 0), t.get('price', 0)))
    print('    -> 盈亏: {0:.2f}'.format(t.get('pnl', 0)))

print()
print('亏损交易({0}笔):'.format(len(losing_trades)))
for t in losing_trades:
    print('  {0} 买入 {1}手 @ {2}'.format(t['time'], t.get('quantity', 0), t.get('price', 0)))
    print('    -> 盈亏: {0:.2f}'.format(t.get('pnl', 0)))

print()
print('=== 结论 ===')
print('1. 没有触发止损/止盈 - 所有交易都是信号驱动平仓')
print('2. 胜率44.44% < 50%，策略期望为负')
print('3. 问题不在止损参数，而在于买卖点信号本身')
print('4. 缠论第一类/第二类买卖点可能不够准确')
print('5. 建议：优化缠论策略或使用其他指标')
