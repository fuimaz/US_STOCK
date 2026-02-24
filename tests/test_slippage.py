"""测试不同滑点参数"""
import sys
sys.path.insert(0, '.')
from backtest_futures_minute import *

def test_slippage(slippage_val):
    # 创建新的账户，手动设置滑点
    df = load_futures_data('I0')
    
    # 使用缠论策略
    strategy = ChanFuturesStrategy(k_type='minute')
    
    # 创建引擎 - 滑点设为0
    engine = FuturesBacktestEngine(
        strategy, 
        initial_capital=BACKTEST_CONFIG['initial_capital'],
        commission_rate=BACKTEST_CONFIG['commission_rate'],
        slippage=slippage_val,
        window_size=100
    )
    
    result = engine.run(df, 'I0')
    return result

print('=== 滑点参数对比测试 (铁矿石I0) ===')
print()

for slip in [0, 1, 2, 5]:
    result = test_slippage(slip)
    print('滑点={0}: 交易次数={1}, 胜率={2:.1f}%, 盈亏={3:.0f}, 收益率={4:.2f}%'.format(
        slip,
        result['total_trades'],
        result['win_rate']*100,
        result['total_pnl'],
        result['total_return']*100
    ))
