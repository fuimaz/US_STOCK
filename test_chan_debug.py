import pandas as pd
from chan_theory_v5 import ChanTheory
import os

file = 'data_cache/600519.SS_20y_1d_forward.csv'
if os.path.exists(file):
    data = pd.read_csv(file, index_col='Date', parse_dates=True)
    data_10y = data[data.index >= data.index[-1] - pd.Timedelta(days=3650)]
    print(f"Full data length: {len(data)}")
    print(f"10y data length: {len(data_10y)}")
    print(f"10y data start: {data_10y.index[0]}")
    print(f"10y data end: {data_10y.index[-1]}")
    
    chan = ChanTheory(k_type='day')
    result = chan.analyze(data_10y)
    print('Success')
    print(f"Buy points: {len(chan.buy_points)}")
    print(f"Sell points: {len(chan.sell_points)}")
else:
    print("File not found")
