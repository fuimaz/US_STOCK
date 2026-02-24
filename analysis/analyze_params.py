"""分析不同止损止盈参数的效果"""
import sys
sys.path.insert(0, '.')
from backtest_futures_minute import *
import numpy as np

# 测试不同止损止盈参数
def test_params(stop_loss, stop_profit):
    BACKTEST_CONFIG['stop_loss_pct'] = stop_loss
    BACKTEST_CONFIG['stop_profit_pct'] = stop_profit
    
    df = load_futures_data('I0')
    strategy = ChanFuturesStrategy(k_type='minute')
    engine = FuturesBacktestEngine(strategy, window_size=100)
    result = engine.run(df, 'I0')
    return result

print('=== 不同止损止盈参数回测对比 (铁矿石I0) ===')
print()

results = []
for sl in [0.02, 0.03, 0.05, 0.08]:
    for sp in [0.04, 0.06, 0.10, 0.15]:
        result = test_params(sl, sp)
        results.append({
            '止损': sl*100,
            '止盈': sp*100,
            '交易次数': result['total_trades'],
            '胜率': result['win_rate']*100,
            '总盈亏': result['total_pnl'],
            '收益率': result['total_return']*100
        })

print('止损%  止盈%   交易  胜率%    盈亏      收益率%')
print('-' * 55)
for r in results:
    print(f"{r['止损']:5.0f}  {r['止盈']:5.0f}   {r['交易次数']:3d}   {r['胜率']:5.1f}   {r['总盈亏']:8.0f}   {r['收益率']:7.2f}")
