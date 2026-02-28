#!/usr/bin/env python
"""分析止损执行情况"""
import pandas as pd
import os

trades_dir = 'results/volume_breakout_minute'
df_summary = pd.read_csv('results/volume_breakout_minute/summary_60min.csv')

print('=' * 80)
print('【止损执行分析 - 为什么亏损超过5%】')
print('=' * 80)
print()

# 收集所有超出5%止损的亏损交易
exceeded_losses = []

for _, row in df_summary.iterrows():
    symbol = row['symbol']
    trades_file = f'{trades_dir}/{symbol}_trades.csv'
    
    if not os.path.exists(trades_file):
        continue
    
    try:
        trades = pd.read_csv(trades_file)
        
        # 找到所有买入记录
        buys = trades[trades['type'] == 'buy']
        
        for i, buy_row in buys.iterrows():
            buy_price = buy_row['price']
            buy_date = buy_row['date']
            
            # 找到对应的卖出记录（下一笔卖出）
            sells_after = trades[(trades['type'].isin(['sell', 'close'])) & (trades.index > i)]
            if len(sells_after) == 0:
                continue
            
            sell_row = sells_after.iloc[0]
            sell_price = sell_row['price']
            sell_date = sell_row['date']
            profit_pct = sell_row.get('profit_pct', 0)
            reason = sell_row.get('reason', '')
            
            # 计算实际亏损百分比
            actual_loss_pct = (sell_price / buy_price - 1) * 100 if sell_price < buy_price else 0
            
            # 如果实际亏损超过6%（超出5%止损+手续费/滑点）
            if actual_loss_pct < -6:
                exceeded_losses.append({
                    'symbol': symbol,
                    'buy_date': buy_date,
                    'sell_date': sell_date,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'actual_loss_pct': actual_loss_pct,
                    'recorded_profit_pct': profit_pct,
                    'reason': reason
                })
    except Exception as e:
        pass

# 排序并显示
exceeded_losses.sort(key=lambda x: x['actual_loss_pct'])

print(f'发现 {len(exceeded_losses)} 笔超出5%止损的亏损交易：')
print()
print(f"{'股票':<12} {'买入日期':<20} {'卖出日期':<20} {'买入价':<10} {'卖出价':<10} {'实际亏损':<10} {'记录亏损':<10} {'原因':<15}")
print('-' * 120)

for loss in exceeded_losses[:30]:  # 显示前30笔
    print(f"{loss['symbol']:<12} {str(loss['buy_date']):<20} {str(loss['sell_date']):<20} "
          f"{loss['buy_price']:<10.2f} {loss['sell_price']:<10.2f} "
          f"{loss['actual_loss_pct']:<10.2f}% {loss['recorded_profit_pct']:<10.2f}% {loss['reason']:<15}")

print()
print('=' * 80)
print('【分析原因】')
print('=' * 80)

# 按原因统计
from collections import Counter
reasons = [l['reason'] for l in exceeded_losses]
reason_counts = Counter(reasons)

print('超出止损的交易原因分布：')
for reason, count in reason_counts.most_common():
    avg_loss = sum(l['actual_loss_pct'] for l in exceeded_losses if l['reason'] == reason) / count
    print(f'  {reason}: {count}笔, 平均亏损{avg_loss:.2f}%')

print()
print('=' * 80)
print('【可能的原因解释】')
print('=' * 80)
print('''
1. 滑点和手续费
   - 买入时价格上浮0.05%（滑点）
   - 卖出时价格下浮0.05%（滑点）
   - 买入手续费0.1%，卖出手续费0.1%
   - 总成本约0.3%，所以实际止损约5.3%

2. 止盈交易中的亏损
   - take_profit_ma5触发时，可能已经从高点回落
   - 如果买入后立即下跌，可能跌破5%止损
   - 但代码检查顺序：先止损，后止盈，所以这种情况不会发生

3. 代码逻辑问题
   - 检查是否有跳空导致止损价格计算错误
   - 检查是否在非交易时间触发信号

4. final_close导致的亏损
   - 回测结束时的强制平仓
   - 可能此时的价格已经远低于买入价
''')

# 具体分析final_close的情况
final_close_losses = [l for l in exceeded_losses if l['reason'] == 'final_close']
if final_close_losses:
    print()
    print('=' * 80)
    print(f'【final_close导致的超损交易: {len(final_close_losses)}笔】')
    print('=' * 80)
    for loss in final_close_losses[:10]:
        print(f"{loss['symbol']}: 买入{loss['buy_price']:.2f} -> 平仓{loss['sell_price']:.2f}, "
              f"亏损{loss['actual_loss_pct']:.2f}%")
