#!/usr/bin/env python
"""分析优化措施的实际效果"""
import pandas as pd
import os

trades_dir = 'results/volume_breakout_minute'
df_summary = pd.read_csv('results/volume_breakout_minute/summary_60min.csv')

print('=' * 80)
print('【优化措施效果分析】')
print('=' * 80)
print()

# 1. 分析大盘过滤器被触发的次数
print('=' * 80)
print('【1. 大盘过滤器效果分析】')
print('=' * 80)

market_block_count = 0
total_buy_signals = 0
blocked_by_market = 0

for _, row in df_summary.iterrows():
    symbol = row['symbol']
    signals_file = f'{trades_dir}/{symbol}_signals.csv'
    
    if not os.path.exists(signals_file):
        continue
    
    try:
        df = pd.read_csv(signals_file)
        if 'market_gap_down_block' in df.columns:
            block_days = df[df['market_gap_down_block'] == True]
            if len(block_days) > 0:
                market_block_count += 1
                
        if 'buy_signal' in df.columns:
            buy_signals = df[df['buy_signal'] == True]
            total_buy_signals += len(buy_signals)
            
            # 检查有多少买入信号被大盘过滤器阻挡
            if 'market_gap_down_block' in df.columns:
                blocked = df[(df['buy_signal'] == True) & (df['market_gap_down_block'] == True)]
                blocked_by_market += len(blocked)
    except:
        pass

print(f'有大盘跳空低开数据的股票数: {market_block_count}')
print(f'总买入信号次数: {total_buy_signals}')
print(f'被大盘过滤器阻挡的买入信号: {blocked_by_market}')
print(f'阻挡比例: {blocked_by_market/total_buy_signals*100:.2f}%' if total_buy_signals > 0 else '阻挡比例: N/A')
print()

# 2. 分析止盈触发情况
print('=' * 80)
print('【2. 分级止盈效果分析】')
print('=' * 80)

take_profit_count = 0
take_profit_trail = 0
take_profit_ma5 = 0
stop_loss_count = 0

profits_tp = []
profits_sl = []

for _, row in df_summary.iterrows():
    symbol = row['symbol']
    trades_file = f'{trades_dir}/{symbol}_trades.csv'
    
    if not os.path.exists(trades_file):
        continue
    
    try:
        trades = pd.read_csv(trades_file)
        sell_trades = trades[trades['type'].isin(['sell', 'close'])]
        
        for _, trade in sell_trades.iterrows():
            reason = trade.get('reason', '')
            profit = trade.get('profit_pct', 0)
            
            if reason == 'take_profit_trail':
                take_profit_trail += 1
                profits_tp.append(profit)
            elif reason == 'take_profit_ma5':
                take_profit_ma5 += 1
                profits_tp.append(profit)
            elif 'stop_loss' in reason:
                stop_loss_count += 1
                profits_sl.append(profit)
    except:
        pass

take_profit_count = take_profit_trail + take_profit_ma5

print(f'止盈次数（总）: {take_profit_count}')
print(f'  - 分级止盈（回撤7%）: {take_profit_trail}')
print(f'  - MA5止盈: {take_profit_ma5}')
print(f'止损次数: {stop_loss_count}')
print()

if profits_tp:
    print(f'止盈交易平均收益: {sum(profits_tp)/len(profits_tp):.2f}%')
    print(f'止盈交易最小收益: {min(profits_tp):.2f}%')
    print(f'止盈交易最大收益: {max(profits_tp):.2f}%')

if profits_sl:
    print(f'止损交易平均亏损: {sum(profits_sl)/len(profits_sl):.2f}%')

print()

# 3. 分析为什么优化可能无效
print('=' * 80)
print('【3. 为什么优化可能无效？】')
print('=' * 80)

print('\n### 大盘过滤器无效的可能原因：')
print('1. 触发频率太低')
print('   - 大盘跳空低开>2%是极端情况')
print('   - 回测期间（约1年）可能只发生了几次')
print('   - 被阻挡的买入信号太少，对整体结果影响有限')
print()
print('2. 副作用')
print('   - 虽然阻挡了高风险日的买入')
print('   - 但也可能错过了反弹机会')
print('   - 大盘急跌后的反弹往往很猛烈')

print('\n### 分级止盈无效的可能原因：')
print('1. 回撤阈值设置问题')
print('   - 当前设置：盈利10%后，回撤7%止盈')
print('   - 7%回撤可能太宽松，很多股票回撤7%后就继续涨了')
print('   - 或者太严格，频繁被震出')
print()
print('2. 与原有MA5止盈的冲突')
print('   - 代码逻辑：先检查回撤止盈，再检查MA5止盈')
print('   - MA5止盈可能更敏感，先触发了')
print()
print('3. 盈亏比没有改善')
print('   - 分级止盈让盈利更早结束')
print('   - 但亏损仍然是-5%止损')
print('   - 整体盈亏比可能没有提升')

# 4. 建议的其他优化方向
print()
print('=' * 80)
print('【4. 其他可能的优化方向】')
print('=' * 80)

print('\n### A. 大盘过滤器的改进')
print('1. 使用更宽松的阈值')
print('   - 大盘跳空低开>1%就暂停')
print('   - 或者使用趋势判断：大盘在MA20下方时暂停')
print()
print('2. 反向操作')
print('   - 大盘跳空低开>2%不是暂停买入，而是加仓')
print('   - 极端恐慌往往是买入机会')

print('\n### B. 止盈逻辑的改进')
print('1. 移动止盈（真正的分级）')
print('   - 盈利>10%：回撤5%止盈')
print('   - 盈利>15%：回撤3%止盈  
print('   - 盈利>20%：回撤2%止盈')
print('   - 让利润奔跑')
print()
print('2. 分批止盈')
print('   - 盈利10%时卖出50%仓位')
print('   - 盈利15%时卖出剩余50%')
print('   - 锁定部分利润，同时让利润奔跑')
print()
print('3. 时间止盈')
print('   - 持仓超过N天没有盈利就平仓')
print('   - 避免资金被长期占用')

print('\n### C. 入场过滤的改进（可能最有效）')
print('1. 趋势确认')
print('   - 只在日线MA20上方买入')
print('   - 或者只在MACD金叉后买入')
print()
print('2. 波动率过滤')
print('   - ATR（平均真实波幅）过高时暂停')
print('   - 避免在剧烈波动期交易')
print()
print('3. 成交量确认')
print('   - 不只是单根K线放量')
print('   - 要求持续放量或突破成交量新高')

print()
print('=' * 80)
print('【结论】')
print('=' * 80)
print('大盘过滤器和分级止盈效果不明显，可能是因为：')
print('1. 触发频率不够高')
print('2. 参数设置不够优化')
print('3. 需要配合其他过滤条件一起使用')
print()
print('建议优先尝试：')
print('1. 日线趋势过滤（MA20）')
print('2. 分批止盈机制')
print('3. 波动率过滤')
