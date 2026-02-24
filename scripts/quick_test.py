import pandas as pd
from chan_theory import ChanTheory
import numpy as np

np.random.seed(42)
dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
prices = []
base_price = 100
for i in range(100):
    if i < 30:
        trend = 0.5
    elif i < 60:
        trend = 0.1 * np.sin(i * 0.3)
    else:
        trend = -0.4
    noise = np.random.normal(0, 0.5)
    close = base_price + trend * i + noise
    high = close + abs(np.random.normal(0, 0.5))
    low = close - abs(np.random.normal(0, 5))
    open_price = close + np.random.normal(0, 0.3)
    prices.append({'Open': open_price, 'High': high, 'Low': low, 'Close': close, 'Volume': 1000000})

data = pd.DataFrame(prices, index=dates)
chan = ChanTheory(k_type='day')
result = chan.analyze(data)

print("Fenxing list:")
for i, fx in enumerate(chan.fenxing_list[:15]):
    type_str = "Ding" if fx['type'] == 1 else "Di"
    print(f"  {i}: {fx['date'].strftime('%m-%d')} {type_str} high={fx['high']:.1f} low={fx['low']:.1f}")

print("\nBi list:")
for i, bi in enumerate(chan.bi_list):
    type_str = "Up" if bi['type'] == 1 else "Down"
    print(f"  {i}: {bi['start'].strftime('%m-%d')} -> {bi['end'].strftime('%m-%d')} {type_str}")

print("\nXianduan list:", len(chan.xianduan_list))
for xd in chan.xianduan_list:
    type_str = "Up" if xd['type'] == 1 else "Down"
    print(f"  {xd['start'].strftime('%m-%d')} -> {xd['end'].strftime('%m-%d')} {type_str} Bi count={len(xd['bi_list'])}")
