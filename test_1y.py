import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

sys.path.append('.')
from indicators.ma_convergence_strategy import calculate_indicators, generate_signals

data_dir = 'data_cache'
files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.csv') and '20y_1d_forward' in f and '_1y_' not in f]
print(f'Files: {len(files)}')

end_date = datetime.now()
start_date = end_date - timedelta(days=365)
print(f'Range: {start_date.date()} to {end_date.date()}')

results = []
trades_list = []

for fp in files:
    sym = os.path.basename(fp).split('_')[0]
    try:
        df = pd.read_csv(fp, index_col='datetime', parse_dates=True)
        df = df[df.index >= start_date]
        df = df[df.index <= end_date]
        if len(df) < 50:
            continue
        
        cols = ['Open','High','Low','Close','Volume']
        df = df[[c for c in cols if c in df.columns]]
        
        df = calculate_indicators(df)
        df = generate_signals(df)
        
        pos, cash, entry_p = 0, 100000, 0
        trades = []
        
        for i in range(len(df)):
            r = df.iloc[i]
            c = r['Close']
            
            if r.get('signal') == 1 and pos == 0 and cash > 0:
                sh = int(cash * 0.5 / c)
                if sh > 0:
                    pos, entry_p = sh, c
                    cash -= sh * c
            
            elif r.get('signal') == -1 and pos > 0:
                p = (c - entry_p) / entry_p * 100
                trades.append({'symbol': sym, 'return_pct': p})
                cash += pos * c
                pos = 0
        
        if pos > 0:
            c = df['Close'].iloc[-1]
            p = (c - entry_p) / entry_p * 100
            trades.append({'symbol': sym, 'return_pct': p})
            cash += pos * c
        
        ret = (cash - 100000) / 100000 * 100
        wr = sum(1 for t in trades if t['return_pct'] > 0) / len(trades) * 100 if trades else 0
        
        results.append({'symbol': sym, 'return': ret, 'trades': len(trades), 'win_rate': wr})
        trades_list.extend(trades)
    except Exception as e:
        pass

df = pd.DataFrame(results)
print(f'Stocks: {len(df)}')
prof = df[df['return'] > 0]
print(f'Profitable: {len(prof)} ({len(prof)/len(df)*100:.1f}%)')
print(f'Avg Return: {df["return"].mean():.2f}%')
print(f'Avg Win Rate: {df["win_rate"].mean():.1f}%')
print(f'Total Trades: {len(trades_list)}')
td = pd.DataFrame(trades_list)
print(f'Win Trades: {len(td[td["return_pct"] > 0])}')
print(f'Loss Trades: {len(td[td["return_pct"] <= 0])}')
print(f'Avg Trade Return: {td["return_pct"].mean():.2f}%')
print(f'Max Win: {td["return_pct"].max():.2f}%')
print(f'Max Loss: {td["return_pct"].min():.2f}%')
print('\n--- Top 10 ---')
for _, r in df.nlargest(10, 'return').iterrows():
    print(f"{r['symbol']}: {r['return']:.2f}%")
