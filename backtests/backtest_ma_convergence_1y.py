"""均线收敛策略回测 - 最近1年"""
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

sys.path.append('.')
from indicators.ma_convergence_strategy import calculate_indicators, generate_signals

# 获取所有股票数据文件
data_dir = 'data_cache'
stock_files = []
for filename in os.listdir(data_dir):
    if filename.endswith('.csv') and '20y_1d_forward.csv' in filename and '_1y_' not in filename:
        stock_files.append(os.path.join(data_dir, filename))

print(f'找到 {len(stock_files)} 个股票数据文件')

# 只回测最近一年
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

print(f'回测时间范围: {start_date.strftime("%Y-%m-%d")} 到 {end_date.strftime("%Y-%m-%d")}')

def backtest_on_stock(data, symbol, initial_capital=100000):
    df = data.copy()
    cols_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
    df = df[[c for c in cols_to_keep if c in df.columns]]
    if len(df) < 50:
        return None
    
    df_indicators = calculate_indicators(df)
    df_with_signals = generate_signals(df_indicators)
    if df_with_signals is None or df_with_signals.empty:
        return None
    
    position = 0
    cash = initial_capital
    entry_price = 0
    entry_date = None
    trades = []
    
    for i in range(len(df_with_signals)):
        row = df_with_signals.iloc[i]
        date = df_with_signals.index[i]
        close_price = row['Close']
        
        if row.get('signal') == 1 and position == 0 and cash > 0:
            shares_to_buy = int(cash * 0.5 / close_price)
            if shares_to_buy > 0:
                position = shares_to_buy
                entry_price = close_price
                entry_date = date
                cash = cash - shares_to_buy * close_price
        
        elif row.get('signal') == -1 and position > 0:
            sell_price = close_price
            profit_pct = (sell_price - entry_price) / entry_price * 100
            trades.append({
                'symbol': symbol,
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_date': date,
                'exit_price': sell_price,
                'return_pct': profit_pct,
            })
            cash = cash + position * sell_price
            position = 0
    
    if position > 0:
        final_price = df_with_signals['Close'].iloc[-1]
        profit_pct = (final_price - entry_price) / entry_price * 100
        trades.append({
            'symbol': symbol,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'exit_date': df_with_signals.index[-1],
            'exit_price': final_price,
            'return_pct': profit_pct,
        })
        cash = cash + position * final_price
        position = 0
    
    final_capital = cash
    total_return = (final_capital - initial_capital) / initial_capital * 100
    
    if len(trades) > 0:
        win_count = sum(1 for t in trades if t['return_pct'] > 0)
        win_rate = win_count / len(trades) * 100
    else:
        win_rate = 0
    
    return {
        'symbol': symbol,
        'final_capital': final_capital,
        'total_return_pct': total_return,
        'win_rate_pct': win_rate,
        'total_trades': len(trades),
        'trades': trades
    }

all_results = []
all_trades = []

for filepath in stock_files:
    filename = os.path.basename(filepath)
    symbol = filename.split('_')[0]
    try:
        data = pd.read_csv(filepath, index_col='datetime', parse_dates=True)
        # 筛选最近一年数据
        data = data[data.index >= start_date]
        data = data[data.index <= end_date]
        if len(data) < 50:
            continue
        result = backtest_on_stock(data, symbol)
        if result:
            all_results.append(result)
            all_trades.extend(result['trades'])
    except Exception as e:
        pass

# 统计
valid_results = [r for r in all_results if r['total_return_pct'] is not None]
df = pd.DataFrame(valid_results)
print(f'\n回测结果: {len(df)} 只股票')
profitable = df[df['total_return_pct'] > 0]
print(f'盈利股票: {len(profitable)} ({len(profitable)/len(df)*100:.1f}%)')
df_with_trades = df[df['total_trades'] > 0]
print(f'有交易股票: {len(df_with_trades)}')
print(f'平均收益: {df_with_trades["total_return_pct"].mean():.2f}%')
print(f'平均胜率: {df_with_trades["win_rate_pct"].mean():.2f}%')
print(f'总交易次数: {len(all_trades)}')

if all_trades:
    trades_df = pd.DataFrame(all_trades)
    print(f'盈利交易: {len(trades_df[trades_df["return_pct"] > 0])}')
    print(f'亏损交易: {len(trades_df[trades_df["return_pct"] <= 0])}')
    print(f'平均收益: {trades_df["return_pct"].mean():.2f}%')
    print(f'最大盈利: {trades_df["return_pct"].max():.2f}%')
    print(f'最大亏损: {trades_df["return_pct"].min():.2f}%')

# Top 10 盈利
print('\n--- Top 10 盈利股票 ---')
top = df.nlargest(10, 'total_return_pct')
for _, row in top.iterrows():
    print(f'{row["symbol"]}: {row["total_return_pct"]:.2f}%, 胜率:{row["win_rate_pct"]:.1f}%, 交易:{row["total_trades"]}')

# Top 10 亏损
print('\n--- Top 10 亏损股票 ---')
bottom = df.nsmallest(10, 'total_return_pct')
for _, row in bottom.iterrows():
    print(f'{row["symbol"]}: {row["total_return_pct"]:.2f}%, 胜率:{row["win_rate_pct"]:.1f}%, 交易:{row["total_trades"]}')
