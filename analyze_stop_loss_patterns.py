#!/usr/bin/env python
"""分析止损高发的场景和规律"""
import pandas as pd
import numpy as np
import os
from collections import Counter, defaultdict

trades_dir = 'results/volume_breakout_minute'
df_summary = pd.read_csv('results/volume_breakout_minute/summary_60min.csv')

print('=' * 80)
print('【止损高发场景分析】')
print('=' * 80)
print()

# 收集所有止损交易
stop_loss_trades = []

for _, row in df_summary.iterrows():
    symbol = row['symbol']
    trades_file = f'{trades_dir}/{symbol}_trades.csv'
    
    if not os.path.exists(trades_file):
        continue
    
    try:
        trades = pd.read_csv(trades_file)
        
        # 找到所有买入和对应的卖出
        for i, trade in trades.iterrows():
            if trade['type'] == 'buy':
                buy_price = trade['price']
                buy_date = trade['date']
                
                # 找到下一笔卖出
                sells_after = trades[(trades['type'].isin(['sell', 'close'])) & (trades.index > i)]
                if len(sells_after) == 0:
                    continue
                    
                sell_row = sells_after.iloc[0]
                sell_price = sell_row['price']
                sell_date = sell_row['date']
                reason = sell_row.get('reason', '')
                profit_pct = sell_row.get('profit_pct', 0)
                
                if 'stop_loss' in reason and profit_pct < 0:
                    stop_loss_trades.append({
                        'symbol': symbol,
                        'buy_date': buy_date,
                        'sell_date': sell_date,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'loss_pct': profit_pct,
                        'reason': reason
                    })
    except Exception as e:
        pass

print(f'总共收集到 {len(stop_loss_trades)} 笔止损交易')
print()

# 1. 按日期统计止损次数
print('=' * 80)
print('【1. 按日期统计 - 止损高发日】')
print('=' * 80)

dates = [t['sell_date'][:10] for t in stop_loss_trades]  # 提取日期部分
date_counts = Counter(dates)

print('止损最集中的日期（前20）：')
for date, count in date_counts.most_common(20):
    print(f'  {date}: {count}笔止损')
print()

# 2. 按月份统计
print('=' * 80)
print('【2. 按月份统计 - 哪个月止损最多】')
print('=' * 80)

months = [t['sell_date'][:7] for t in stop_loss_trades]
month_counts = Counter(months)

for month, count in sorted(month_counts.items()):
    print(f'  {month}: {count}笔止损')
print()

# 3. 按时间段统计（小时）
print('=' * 80)
print('【3. 按时间段统计 - 一天中何时止损最多】')
print('=' * 80)

hours = []
for t in stop_loss_trades:
    try:
        hour = t['sell_date'][11:13]
        hours.append(hour)
    except:
        pass

hour_counts = Counter(hours)
for hour in sorted(hour_counts.keys()):
    print(f'  {hour}:00: {hour_counts[hour]}笔')
print()

# 4. 按股票统计 - 哪些股票最容易止损
print('=' * 80)
print('【4. 按股票统计 - 哪些股票最容易触发止损】')
print('=' * 80)

symbol_stats = defaultdict(lambda: {'stop_count': 0, 'total_trades': 0, 'avg_loss': []})

for t in stop_loss_trades:
    symbol = t['symbol']
    symbol_stats[symbol]['stop_count'] += 1
    symbol_stats[symbol]['avg_loss'].append(t['loss_pct'])

# 获取每只股票的总交易次数
for _, row in df_summary.iterrows():
    symbol = row['symbol']
    symbol_stats[symbol]['total_trades'] = row['total_trades']

# 计算止损率
symbol_list = []
for symbol, stats in symbol_stats.items():
    total = stats['total_trades']
    stops = stats['stop_count']
    avg_loss = sum(stats['avg_loss']) / len(stats['avg_loss']) if stats['avg_loss'] else 0
    stop_rate = stops / total * 100 if total > 0 else 0
    symbol_list.append({
        'symbol': symbol,
        'stop_count': stops,
        'total_trades': total,
        'stop_rate': stop_rate,
        'avg_loss': avg_loss
    })

# 按止损率排序
symbol_list.sort(key=lambda x: x['stop_rate'], reverse=True)

print('止损率最高的股票（前15）：')
print(f"{'股票':<12} {'止损次数':<10} {'总交易':<10} {'止损率':<10} {'平均亏损':<10}")
print('-' * 60)
for s in symbol_list[:15]:
    print(f"{s['symbol']:<12} {s['stop_count']:<10} {s['total_trades']:<10} {s['stop_rate']:<10.1f}% {s['avg_loss']:<10.2f}%")
print()

# 5. 分析止损前的持股时间
print('=' * 80)
print('【5. 持股时间分析 - 止损前持有多久】')
print('=' * 80)

holding_periods = []
for t in stop_loss_trades:
    try:
        buy_dt = pd.to_datetime(t['buy_date'])
        sell_dt = pd.to_datetime(t['sell_date'])
        # 计算K线根数（假设60分钟周期，每天4小时，约4根K线）
        hours_diff = (sell_dt - buy_dt).total_seconds() / 3600
        bars = hours_diff / 1  # 60分钟周期，每根1小时
        holding_periods.append(bars)
    except:
        pass

if holding_periods:
    print(f'平均持股时间（根数）: {np.mean(holding_periods):.1f}')
    print(f'中位数持股时间: {np.median(holding_periods):.1f}')
    print(f'最短持股时间: {np.min(holding_periods):.1f}')
    print(f'最长持股时间: {np.max(holding_periods):.1f}')
    
    # 分布
    quick_stops = len([x for x in holding_periods if x <= 4])  # 当天或次日
    normal_stops = len([x for x in holding_periods if 4 < x <= 48])  # 1-12天
    long_stops = len([x for x in holding_periods if x > 48])  # 超过12天
    
    print()
    print('持股时间分布：')
    print(f'  快速止损(<=4根): {quick_stops}笔 ({quick_stops/len(holding_periods)*100:.1f}%)')
    print(f'  正常止损(5-48根): {normal_stops}笔 ({normal_stops/len(holding_periods)*100:.1f}%)')
    print(f'  长期持有后止损(>48根): {long_stops}笔 ({long_stops/len(holding_periods)*100:.1f}%)')
print()

# 6. 止损后的走势分析（需要加载价格数据，简化版）
print('=' * 80)
print('【6. 止损原因细分】')
print('=' * 80)

gap_stops = [t for t in stop_loss_trades if 'gap' in t['reason']]
normal_stops = [t for t in stop_loss_trades if 'gap' not in t['reason']]

print(f'跳空低开止损: {len(gap_stops)}笔 ({len(gap_stops)/len(stop_loss_trades)*100:.1f}%)')
print(f'普通触及止损: {len(normal_stops)}笔 ({len(normal_stops)/len(stop_loss_trades)*100:.1f}%)')

if gap_stops:
    avg_gap_loss = sum(t['loss_pct'] for t in gap_stops) / len(gap_stops)
    print(f'跳空止损平均亏损: {avg_gap_loss:.2f}%')

if normal_stops:
    avg_normal_loss = sum(t['loss_pct'] for t in normal_stops) / len(normal_stops)
    print(f'普通止损平均亏损: {avg_normal_loss:.2f}%')
print()

# 7. 关键发现总结
print('=' * 80)
print('【7. 关键发现总结】')
print('=' * 80)

print()
print('📊 止损高发场景：')

# 找出止损最集中的日期
top_dates = date_counts.most_common(5)
print('\n1. 集中爆发日：')
for date, count in top_dates:
    print(f'   {date}: {count}笔止损（可能是市场大跌日）')

# 找出止损率最高的股票
print('\n2. 高止损率股票特征：')
high_stop_stocks = [s for s in symbol_list if s['stop_rate'] > 70]
print(f'   止损率>70%的股票有{len(high_stop_stocks)}只：')
for s in high_stop_stocks[:5]:
    print(f'     {s["symbol"]}: 止损率{s["stop_rate"]:.1f}%')

print('\n3. 时间特征：')
most_common_hour = hour_counts.most_common(1)[0]
print(f'   止损最集中的时间段: {most_common_hour[0]}:00 ({most_common_hour[1]}笔)')

print('\n4. 持股时间特征：')
if holding_periods:
    quick_pct = quick_stops / len(holding_periods) * 100
    print(f'   {quick_pct:.1f}%的止损发生在买入后当天或次日')
    print('   说明很多买入信号是假突破，买入后立即回调')
