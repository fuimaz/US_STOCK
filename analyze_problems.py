#!/usr/bin/env python
"""分析成交量突破策略的问题"""
import pandas as pd
import numpy as np
import os

# 读取汇总数据
df = pd.read_csv('results/volume_breakout_minute/summary_60min.csv')
print('=' * 80)
print('【整体表现统计】')
print('=' * 80)
print(f'股票数量: {len(df)}')
print(f'盈利股票: {(df["total_return_pct"] > 0).sum()} / {len(df)} ({(df["total_return_pct"] > 0).sum() / len(df) * 100:.1f}%)')
print(f'平均总收益: {df["total_return_pct"].mean():.2f}%')
print(f'平均最大回撤: {df["max_drawdown_pct"].mean():.2f}%')
print(f'平均胜率: {df["win_rate_pct"].mean():.2f}%')
print(f'平均交易次数: {df["total_trades"].mean():.1f}')
print()

# 按回撤分组分析
print('=' * 80)
print('【按最大回撤分组分析】')
print('=' * 80)
high_dd = df[df['max_drawdown_pct'] > 40]
med_dd = df[(df['max_drawdown_pct'] >= 25) & (df['max_drawdown_pct'] <= 40)]
low_dd = df[df['max_drawdown_pct'] < 25]

print(f'高回撤(>40%): {len(high_dd)}只, 平均收益: {high_dd["total_return_pct"].mean():.2f}%, 平均胜率: {high_dd["win_rate_pct"].mean():.1f}%')
print(f'中回撤(25-40%): {len(med_dd)}只, 平均收益: {med_dd["total_return_pct"].mean():.2f}%, 平均胜率: {med_dd["win_rate_pct"].mean():.1f}%')
print(f'低回撤(<25%): {len(low_dd)}只, 平均收益: {low_dd["total_return_pct"].mean():.2f}%, 平均胜率: {low_dd["win_rate_pct"].mean():.1f}%')
print()

# 找出问题股票
print('=' * 80)
print('【问题股票 - 回撤>40%且亏损】')
print('=' * 80)
bad_stocks = df[(df['max_drawdown_pct'] > 40) & (df['total_return_pct'] < 0)].sort_values('total_return_pct')
for _, row in bad_stocks.head(10).iterrows():
    print(f"{row['symbol']}: 收益{row['total_return_pct']:.1f}%, 回撤{row['max_drawdown_pct']:.1f}%, 胜率{row['win_rate_pct']:.1f}%")
print()

# 分析交易明细 - 计算盈亏比
print('=' * 80)
print('【盈亏比分析】')
print('=' * 80)
trades_dir = 'results/volume_breakout_minute'
all_profits = []
all_losses = []

for _, row in df.iterrows():
    symbol = row['symbol']
    trades_file = os.path.join(trades_dir, f'{symbol}_trades.csv')
    if os.path.exists(trades_file):
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

# 极端亏损分析
print('=' * 80)
print('【极端亏损交易 (>20%)】')
print('=' * 80)
extreme_losses = []
for _, row in df.iterrows():
    symbol = row['symbol']
    trades_file = os.path.join(trades_dir, f'{symbol}_trades.csv')
    if os.path.exists(trades_file):
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
print()

# 分析连续亏损
print('=' * 80)
print('【连续亏损分析】')
print('=' * 80)
max_consecutive_losses_all = []
for _, row in df.iterrows():
    symbol = row['symbol']
    trades_file = os.path.join(trades_dir, f'{symbol}_trades.csv')
    if os.path.exists(trades_file):
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
    print(f'最大连续亏损次数分布:')
    from collections import Counter
    dist = Counter(max_consecutive_losses_all)
    for k in sorted(dist.keys()):
        print(f'  {k}次: {dist[k]}只股票')
print()

# 按行业分析
print('=' * 80)
print('【按行业分析】')
print('=' * 80)
industry_map = {
    '000001.SZ': '银行', '000333.SZ': '家电', '000525.SZ': '化工', '000625.SZ': '汽车',
    '000651.SZ': '家电', '000661.SZ': '医药', '000725.SZ': '电子', '000876.SZ': '农业',
    '001217.SZ': '新材料', '002028.SZ': '电力设备', '002049.SZ': '半导体', '002129.SZ': '电子',
    '002230.SZ': '软件', '002272.SZ': '化工', '002415.SZ': '安防', '002460.SZ': '锂电池',
    '002475.SZ': '电子', '002594.SZ': '汽车', '002714.SZ': '养殖', '002837.SZ': '温控设备',
    '300033.SZ': '软件', '300124.SZ': '自动化', '300274.SZ': '光伏', '300364.SZ': '传媒',
    '300394.SZ': '光模块', '300750.SZ': '锂电池', '300760.SZ': '医药', '300846.SZ': '汽车电子',
    '301018.SZ': '专用设备', '600009.SS': '机场', '600018.SS': '港口', '600019.SS': '钢铁',
    '600028.SS': '石油', '600029.SS': '航空', '600030.SS': '证券', '600031.SS': '机械',
    '600036.SS': '银行', '600050.SS': '通信', '600104.SS': '汽车', '600115.SS': '航空',
    '600276.SS': '医药', '600309.SS': '化工', '600346.SS': '化工', '600584.SS': '半导体',
    '600585.SS': '建材', '600586.SS': '建材', '600690.SS': '家电', '600694.SS': '零售',
    '600886.SS': '电力', '600887.SS': '乳制品', '600900.SS': '电力', '600941.SS': '通信',
    '600986.SS': '广告', '601012.SS': '光伏', '601088.SS': '煤炭', '601111.SS': '航空',
    '601126.SS': '自动化', '601166.SS': '银行', '601186.SS': '基建', '601238.SS': '汽车',
    '601318.SS': '保险', '601390.SS': '基建', '601398.SS': '银行', '601600.SS': '有色',
    '601601.SS': '保险', '601628.SS': '保险', '601688.SS': '证券', '601857.SS': '石油',
    '601888.SS': '旅游', '601898.SS': '煤炭', '601899.SS': '有色', '601939.SS': '银行',
    '601985.SS': '核电', '603188.SS': '医药', '603259.SS': '医药', '603288.SS': '调味品',
    '603533.SS': '传媒', '688158.SS': '软件', '688521.SS': '半导体'
}

industry_stats = {}
for _, row in df.iterrows():
    symbol = row['symbol']
    industry = industry_map.get(symbol, '其他')
    if industry not in industry_stats:
        industry_stats[industry] = {'count': 0, 'total_return': 0, 'avg_dd': 0, 'avg_winrate': 0}
    industry_stats[industry]['count'] += 1
    industry_stats[industry]['total_return'] += row['total_return_pct']
    industry_stats[industry]['avg_dd'] += row['max_drawdown_pct']
    industry_stats[industry]['avg_winrate'] += row['win_rate_pct']

for ind, stats in sorted(industry_stats.items(), key=lambda x: x[1]['total_return']/x[1]['count'], reverse=True):
    avg_return = stats['total_return'] / stats['count']
    avg_dd = stats['avg_dd'] / stats['count']
    avg_wr = stats['avg_winrate'] / stats['count']
    print(f"{ind:8s}: {stats['count']}只, 平均收益{avg_return:+.1f}%, 回撤{avg_dd:.1f}%, 胜率{avg_wr:.1f}%")
