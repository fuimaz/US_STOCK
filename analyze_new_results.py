#!/usr/bin/env python
"""分析新回测结果（复权后）"""
import pandas as pd
import numpy as np

# 读取新数据
df_new = pd.read_csv('results/volume_breakout_minute/summary_60min.csv')

print('=' * 80)
print('【复权后回测结果分析】')
print('=' * 80)
print()

# 整体统计
print('=' * 80)
print('【整体表现统计】')
print('=' * 80)
print(f'股票数量: {len(df_new)}')
print(f'盈利股票: {(df_new["total_return_pct"] > 0).sum()} / {len(df_new)} ({(df_new["total_return_pct"] > 0).sum() / len(df_new) * 100:.1f}%)')
print(f'平均总收益: {df_new["total_return_pct"].mean():.2f}%')
print(f'平均最大回撤: {df_new["max_drawdown_pct"].mean():.2f}%')
print(f'平均胜率: {df_new["win_rate_pct"].mean():.2f}%')
print(f'平均交易次数: {df_new["total_trades"].mean():.1f}')
print(f'平均夏普比率: {df_new["sharpe_ratio"].mean():.2f}')
print()

# 对比比亚迪（关键改进案例）
print('=' * 80)
print('【比亚迪(002594) - 复权前后对比】')
print('=' * 80)
byd = df_new[df_new['symbol'] == '002594.SZ'].iloc[0]
print(f'最终资金: {byd["final_capital"]:.0f} (之前: 46525)')
print(f'总收益: {byd["total_return_pct"]:.1f}% (之前: -53.5%)')
print(f'最大回撤: {byd["max_drawdown_pct"]:.1f}% (之前: 79.9%)')
print(f'胜率: {byd["win_rate_pct"]:.1f}% (之前: 38.5%)')
print()

# 其他大幅改善的股票
print('=' * 80)
print('【其他关键改善】')
print('=' * 80)
improved = [
    ('300760.SZ', '迈瑞医疗'),
    ('603533.SS', '掌阅科技'),
    ('300274.SZ', '阳光电源'),
    ('300394.SZ', '天孚通信'),
]
for symbol, name in improved:
    row = df_new[df_new['symbol'] == symbol]
    if len(row) > 0:
        r = row.iloc[0]
        print(f'{symbol} ({name}): 收益{r["total_return_pct"]:+.1f}%, 回撤{r["max_drawdown_pct"]:.1f}%')
print()

# 按回撤分组
print('=' * 80)
print('【按最大回撤分组】')
print('=' * 80)
high_dd = df_new[df_new['max_drawdown_pct'] > 40]
med_dd = df_new[(df_new['max_drawdown_pct'] >= 30) & (df_new['max_drawdown_pct'] <= 40)]
low_dd = df_new[df_new['max_drawdown_pct'] < 30]

print(f'高回撤(>40%): {len(high_dd)}只, 平均收益: {high_dd["total_return_pct"].mean():.2f}%, 平均胜率: {high_dd["win_rate_pct"].mean():.1f}%')
print(f'中回撤(30-40%): {len(med_dd)}只, 平均收益: {med_dd["total_return_pct"].mean():.2f}%, 平均胜率: {med_dd["win_rate_pct"].mean():.1f}%')
print(f'低回撤(<30%): {len(low_dd)}只, 平均收益: {low_dd["total_return_pct"].mean():.2f}%, 平均胜率: {low_dd["win_rate_pct"].mean():.1f}%')
print()

# 表现最好的股票
print('=' * 80)
print('【表现最好的10只股票】')
print('=' * 80)
top10 = df_new.nlargest(10, 'total_return_pct')
for _, row in top10.iterrows():
    print(f"{row['symbol']}: 收益{row['total_return_pct']:+.1f}%, 回撤{row['max_drawdown_pct']:.1f}%, 胜率{row['win_rate_pct']:.1f}%")
print()

# 表现最差的股票
print('=' * 80)
print('【表现最差的10只股票】')
print('=' * 80)
bottom10 = df_new.nsmallest(10, 'total_return_pct')
for _, row in bottom10.iterrows():
    print(f"{row['symbol']}: 收益{row['total_return_pct']:+.1f}%, 回撤{row['max_drawdown_pct']:.1f}%, 胜率{row['win_rate_pct']:.1f}%")
print()

# 盈亏比分析
print('=' * 80)
print('【盈亏比分析】')
print('=' * 80)
trades_dir = 'results/volume_breakout_minute'
all_profits = []
all_losses = []

for _, row in df_new.iterrows():
    symbol = row['symbol']
    trades_file = f'{trades_dir}/{symbol}_trades.csv'
    try:
        trades = pd.read_csv(trades_file)
        close_trades = trades[trades['type'].isin(['sell', 'close'])]
        for _, t in close_trades.iterrows():
            profit = t.get('profit_pct', 0)
            if profit > 0:
                all_profits.append(profit)
            else:
                all_losses.append(abs(profit))
    except:
        pass

if all_profits and all_losses:
    avg_profit = np.mean(all_profits)
    avg_loss = np.mean(all_losses)
    median_profit = np.median(all_profits)
    median_loss = np.median(all_losses)
    profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
    print(f'平均盈利: {avg_profit:.2f}%')
    print(f'平均亏损: {avg_loss:.2f}%')
    print(f'盈亏比: {profit_loss_ratio:.2f}')
    print(f'中位数盈利: {median_profit:.2f}%')
    print(f'中位数亏损: {median_loss:.2f}%')
    print(f'胜率要求(盈亏比{profit_loss_ratio:.2f}): {1/(1+profit_loss_ratio)*100:.1f}%')
print()

# 极端亏损交易
print('=' * 80)
print('【极端亏损交易 (>20%)】')
print('=' * 80)
extreme_losses = []
for _, row in df_new.iterrows():
    symbol = row['symbol']
    trades_file = f'{trades_dir}/{symbol}_trades.csv'
    try:
        trades = pd.read_csv(trades_file)
        close_trades = trades[trades['type'].isin(['sell', 'close'])]
        for _, t in close_trades.iterrows():
            profit = t.get('profit_pct', 0)
            if profit < -20:
                extreme_losses.append({
                    'symbol': symbol,
                    'date': t.get('date', ''),
                    'profit_pct': profit,
                    'reason': t.get('reason', '')
                })
    except:
        pass

if extreme_losses:
    for loss in sorted(extreme_losses, key=lambda x: x['profit_pct'])[:10]:
        print(f"{loss['symbol']} {loss['date']}: {loss['profit_pct']:.1f}% ({loss['reason']})")
else:
    print('未发现单笔亏损>20%的交易')
print()

# 连续亏损分析
print('=' * 80)
print('【连续亏损分析】')
print('=' * 80)
max_consecutive_losses_all = []
for _, row in df_new.iterrows():
    symbol = row['symbol']
    trades_file = f'{trades_dir}/{symbol}_trades.csv'
    try:
        trades = pd.read_csv(trades_file)
        close_trades = trades[trades['type'].isin(['sell', 'close'])]
        profits = close_trades['profit_pct'].tolist()
        
        max_consec = 0
        current_consec = 0
        for p in profits:
            if p < 0:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0
        max_consecutive_losses_all.append(max_consec)
    except:
        pass

if max_consecutive_losses_all:
    print(f'平均最大连续亏损次数: {np.mean(max_consecutive_losses_all):.1f}')
    from collections import Counter
    dist = Counter(max_consecutive_losses_all)
    print(f'最大连续亏损次数分布:')
    for k in sorted(dist.keys()):
        print(f'  {k}次: {dist[k]}只股票')
print()

# 夏普比率分布
print('=' * 80)
print('【夏普比率分布】')
print('=' * 80)
sharpe_high = df_new[df_new['sharpe_ratio'] > 1.0]
sharpe_mid = df_new[(df_new['sharpe_ratio'] >= 0.5) & (df_new['sharpe_ratio'] <= 1.0)]
sharpe_low = df_new[(df_new['sharpe_ratio'] >= 0) & (df_new['sharpe_ratio'] < 0.5)]
sharpe_neg = df_new[df_new['sharpe_ratio'] < 0]

print(f'夏普>1.0 (优秀): {len(sharpe_high)}只, 平均收益{sharpe_high["total_return_pct"].mean():.1f}%')
print(f'夏普0.5-1.0 (良好): {len(sharpe_mid)}只, 平均收益{sharpe_mid["total_return_pct"].mean():.1f}%')
print(f'夏普0-0.5 (一般): {len(sharpe_low)}只, 平均收益{sharpe_low["total_return_pct"].mean():.1f}%')
print(f'夏普<0 (差): {len(sharpe_neg)}只, 平均收益{sharpe_neg["total_return_pct"].mean():.1f}%')
